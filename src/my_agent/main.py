"""CLI: 단발 메시지 또는 대화 루프."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

from my_agent.agent import AUTO_MODEL, Agent


def _format_user_error(exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        detail = ""
        try:
            body = exc.response.json()
            detail = str(body.get("error", ""))
        except (ValueError, json.JSONDecodeError):
            detail = (exc.response.text or "")[:300]
        code = exc.response.status_code
        if code == 404 and (
            "not found" in detail.lower() or "model" in detail.lower()
        ):
            return (
                f"모델을 쓸 수 없습니다: {detail or '404'}\n"
                "  → `ollama list` 후 `ollama pull <모델>` 또는 `--model` 지정.\n"
                "  → 과제: `ollama pull qwen2.5-coder:7b`"
            )
        if code == 503 or "connection" in detail.lower():
            return (
                f"Ollama 연결 실패 (HTTP {code}).\n"
                "  → Ollama 앱 실행 또는 `ollama serve` 후 재시도."
            )
        return f"HTTP {code}: {detail or exc.response.text[:200]!r}"

    if isinstance(exc, httpx.RequestError):
        return (
            f"네트워크 오류: {exc}\n"
            "  → Ollama가 http://localhost:11434 에 떠 있는지 확인하세요."
        )

    return str(exc)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="my_agent — Ollama 로컬 LLM 에이전트",
        epilog="빠른 실행: ./run 또는 uv run my-agent -e",
    )
    p.add_argument("-m", "--message", help="한 번만 보낼 메시지 (없으면 대화 모드)")
    p.add_argument(
        "-e", "--easy",
        action="store_true",
        help="작업 폴더=현재 디렉터리, 대화를 .my_agent_memory.json에 저장",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Ollama 태그 (미지정 시 자동 선택, 권장: qwen2.5-coder:7b)",
    )
    p.add_argument(
        "--base-url",
        default=None,
        help="Ollama 베이스 URL (기본: OLLAMA_HOST 또는 http://localhost:11434)",
    )
    p.add_argument(
        "--workspace",
        default=None,
        help="파일 도구 허용 루트 (기본: cwd / AGENT_WORKSPACE)",
    )
    p.add_argument("--persist", action="store_true", help="대화를 디스크에 저장")
    p.add_argument("--memory-file", default=None, help="세션 JSON 경로")
    p.add_argument("--no-tools", action="store_true", help="도구 끄기 (채팅만)")
    p.add_argument(
        "--no-memory",
        action="store_true",
        help="턴 단위로만 처리 (히스토리·파일 저장 안 함)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    ws = Path(args.workspace).expanduser().resolve() if args.workspace else None
    if args.easy and ws is None:
        ws = Path.cwd().resolve()

    mem: Path | None = None
    if args.memory_file:
        mem = Path(args.memory_file).expanduser().resolve()
    elif (args.persist or args.easy) and not args.no_memory:
        mem = (ws or Path.cwd().resolve()) / ".my_agent_memory.json"

    base_url = (
        args.base_url
        or os.environ.get("OLLAMA_HOST")
        or "http://localhost:11434"
    ).rstrip("/")

    agent = Agent(
        model=args.model if args.model else AUTO_MODEL,
        base_url=base_url,
        use_tools=not args.no_tools,
        remember=not args.no_memory,
        workspace_root=ws,
        memory_file=None if args.no_memory else mem,
    )
    if args.model:
        agent.model = args.model

    if args.message:
        try:
            print(agent.chat(args.message))
        except (httpx.HTTPError, httpx.RequestError) as e:
            print(_format_user_error(e), file=sys.stderr)
            sys.exit(1)
        except RuntimeError as e:
            print(f"[에이전트] {e}", file=sys.stderr)
            sys.exit(1)
        return

    mem_line = f"\n기록: {agent.memory_file}" if agent.memory_file else ""
    print(
        f"모델: {agent.model}  |  작업 폴더: {agent.workspace_root}{mem_line}\n"
        "종료: quit / exit / q  |  기록 초기화: /reset"
    )

    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if not line:
            continue
        if line.lower() in {"quit", "exit", "q"}:
            break
        if line == "/reset":
            agent.reset()
            print("(대화 기록을 초기화했습니다.)")
            continue

        try:
            print(agent.chat(line))
        except (httpx.HTTPError, httpx.RequestError) as e:
            print(_format_user_error(e), file=sys.stderr)
        except RuntimeError as e:
            print(f"[에이전트] {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
