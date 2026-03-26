"""Ollama tools 스키마 정의 및 `dispatch_tool` 라우팅."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from my_agent.file_ops import (
    READ_MAX_CHARS,
    read_file_content,
    replace_in_file_content,
    resolve_safe_path,
    write_file_content,
)
from my_agent.namuwiki import fetch_namuwiki_raw, search_namuwiki

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "현재 로컬 타임존 기준 시각을 ISO 8601 문자열로 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "두 정수 a와 b의 합을 계산합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "첫 번째 정수"},
                    "b": {"type": "integer", "description": "두 번째 정수"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "작업 폴더 내 텍스트 파일을 UTF-8로 읽습니다. 상대 경로만 사용합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "읽을 파일 상대 경로"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "파일 전체를 덮어씁니다. 없으면 생성합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "쓸 파일 상대 경로"},
                    "content": {"type": "string", "description": "파일 전체 내용"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": (
                "파일에서 old_string 첫 일치 1곳만 new_string으로 바꿉니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "수정할 파일 상대 경로"},
                    "old_string": {
                        "type": "string",
                        "description": "바꿀 원문 (정확히 일치)",
                    },
                    "new_string": {"type": "string", "description": "바꿀 내용"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "namu_search",
            "description": (
                "나무위키 키워드 검색. 문서 제목·URL 목록을 반환합니다. "
                "본문이 필요하면 이어서 namu_fetch를 호출하세요."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색 키워드"},
                    "max_results": {
                        "type": "integer",
                        "description": "최대 결과 수 (1~20, 기본 8)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "namu_fetch",
            "description": (
                "나무위키 단일 문서. 가능하면 raw 위키텍스트, 아니면 /w/ 페이지 메타 요약."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "description": "문서 제목 또는 /w/ 이하 경로",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "최대 글자 수 (기본 약 28000)",
                    },
                },
                "required": ["page"],
            },
        },
    },
]

TOOL_NAMES = frozenset(
    {
        "get_current_time",
        "add",
        "read_file",
        "write_file",
        "replace_in_file",
        "namu_search",
        "namu_fetch",
    }
)


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            return json.loads(s)
        except json.JSONDecodeError as e:
            raise ValueError(f"도구 인자 JSON 파싱 실패: {e}") from e
    raise TypeError(f"도구 인자는 str 또는 dict 여야 합니다: {type(raw)}")


def _clamp_int(value: Any, default: int, *, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(n, hi))


def dispatch_tool(name: str, arguments: Any, *, workspace: Path) -> str:
    """도구 이름에 맞는 구현을 호출하고, 항상 문자열 결과를 반환합니다."""
    try:
        args = _parse_arguments(arguments)
    except (TypeError, ValueError) as e:
        return f"[오류] {e}"

    if name == "get_current_time":
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    if name == "add":
        try:
            a = int(args["a"])
            b = int(args["b"])
        except KeyError as e:
            return f"[오류] add에는 a, b가 필요합니다: {e}"
        except (TypeError, ValueError) as e:
            return f"[오류] a, b는 정수여야 합니다: {e}"
        return str(a + b)

    if name == "read_file":
        try:
            return read_file_content(workspace, str(args["path"]))
        except KeyError:
            return "[오류] read_file에는 path가 필요합니다."
        except (OSError, PermissionError, FileNotFoundError, ValueError) as e:
            return f"[오류] {e}"

    if name == "write_file":
        try:
            return write_file_content(
                workspace, str(args["path"]), str(args["content"])
            )
        except KeyError as e:
            return f"[오류] write_file 인자 누락: {e}"
        except (OSError, PermissionError, ValueError) as e:
            return f"[오류] {e}"

    if name == "replace_in_file":
        try:
            return replace_in_file_content(
                workspace,
                str(args["path"]),
                str(args["old_string"]),
                str(args["new_string"]),
            )
        except KeyError as e:
            return f"[오류] replace_in_file 인자 누락: {e}"
        except (OSError, PermissionError, FileNotFoundError, ValueError) as e:
            return f"[오류] {e}"

    if name == "namu_search":
        try:
            q = str(args["query"])
        except KeyError:
            return "[오류] namu_search에는 query가 필요합니다."
        mr = _clamp_int(args.get("max_results"), 8, lo=1, hi=20)
        try:
            return search_namuwiki(q, mr)
        except httpx.HTTPError as e:
            return f"[오류] 나무위키 검색 HTTP 실패: {e}"

    if name == "namu_fetch":
        try:
            page = str(args["page"])
        except KeyError:
            return "[오류] namu_fetch에는 page가 필요합니다."
        mc = _clamp_int(args.get("max_chars"), 28_000, lo=1_000, hi=500_000)
        try:
            return fetch_namuwiki_raw(page, mc)
        except httpx.HTTPError as e:
            return f"[오류] 나무위키 본문 HTTP 실패: {e}"

    return f"[도구 오류] 알 수 없는 도구: {name}"


__all__ = [
    "READ_MAX_CHARS",
    "TOOL_DEFINITIONS",
    "TOOL_NAMES",
    "dispatch_tool",
    "resolve_safe_path",
]
