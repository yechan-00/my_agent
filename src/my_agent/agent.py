"""Ollama `/api/chat` — 멀티턴, 시스템 프롬프트, 도구 루프, 선택적 세션 저장."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from my_agent.persona import DEFAULT_SYSTEM
from my_agent.tools import TOOL_DEFINITIONS, TOOL_NAMES, dispatch_tool

AUTO_MODEL = "auto"
COURSE_MODEL = "qwen2.5-coder:7b"
MODEL_PICK_TIMEOUT = 10.0


def pick_installed_model(base_url: str, timeout: float = MODEL_PICK_TIMEOUT) -> str:
    """설치된 Ollama 모델 태그 중 우선순위가 높은 하나를 고릅니다."""
    url = f"{base_url.rstrip('/')}/api/tags"
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url)
        r.raise_for_status()
        payload = r.json()
    names = [str(m["name"]) for m in payload.get("models", []) if m.get("name")]
    if not names:
        return COURSE_MODEL

    installed = set(names)
    order = [
        COURSE_MODEL,
        "qwen2.5-coder:latest",
        "qwen2.5:latest",
        "llama3.2:latest",
        "llama3.2",
        "llama3.1:latest",
        "llama3.1:8b",
        "llama3.1",
        "mistral:latest",
    ]
    for tag in order:
        if tag in installed:
            return tag
    for tag in order:
        stem = tag.split(":")[0]
        for n in names:
            if n == stem or n.startswith(f"{stem}:"):
                return n
    return names[0]


def _deep_copy_messages(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(m) for m in history]


def _text_looks_like_tool_json(content: str) -> dict[str, Any] | None:
    """모델이 본문에 JSON만 넣어 도구를 흉내 내는 경우 파싱합니다."""
    raw = content.strip()
    if not raw.startswith("{"):
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    name = data.get("name")
    if name not in TOOL_NAMES:
        return None
    return data


def _run_dispatch(name: str, args: Any, workspace: Path) -> str:
    try:
        return dispatch_tool(name, args, workspace=workspace)
    except Exception as e:  # noqa: BLE001
        return f"[도구 실행 오류] {e}"


def _append_tool_message(
    messages: list[dict[str, Any]],
    name: str,
    content: str,
    *,
    tool_call_id: str | None = None,
) -> None:
    msg: dict[str, Any] = {"role": "tool", "content": content, "name": name}
    if tool_call_id:
        msg["tool_call_id"] = tool_call_id
    messages.append(msg)


@dataclass
class Agent:
    """로컬 Ollama LLM과 대화. 파일 도구는 workspace_root 아래만."""

    model: str = AUTO_MODEL
    base_url: str = "http://localhost:11434"
    timeout: float = 120.0
    system_prompt: str = DEFAULT_SYSTEM
    use_tools: bool = True
    remember: bool = True
    max_tool_rounds: int = 8
    workspace_root: Path | None = None
    memory_file: Path | None = None
    _messages: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        env_model = os.environ.get("OLLAMA_MODEL")
        if self.model == AUTO_MODEL and env_model:
            self.model = env_model
        elif self.model == AUTO_MODEL:
            try:
                self.model = pick_installed_model(self.base_url)
            except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError):
                self.model = COURSE_MODEL

        if self.workspace_root is None:
            w = os.environ.get("AGENT_WORKSPACE")
            self.workspace_root = (
                Path(w).expanduser().resolve() if w else Path.cwd().resolve()
            )
        else:
            self.workspace_root = self.workspace_root.expanduser().resolve()

        if self.memory_file is not None:
            self.memory_file = self.memory_file.expanduser().resolve()
        else:
            mf = os.environ.get("AGENT_MEMORY_FILE")
            if mf:
                self.memory_file = Path(mf).expanduser().resolve()

        self._messages = []
        if self.remember and self.memory_file and self.memory_file.is_file():
            self._load_session_from_disk()
        if not self._messages:
            self._messages = [{"role": "system", "content": self.system_prompt}]
        elif self._messages[0].get("role") != "system":
            self._messages.insert(0, {"role": "system", "content": self.system_prompt})
        else:
            self._messages[0] = {"role": "system", "content": self.system_prompt}

    def _load_session_from_disk(self) -> None:
        if not self.memory_file:
            return
        try:
            data = json.loads(self.memory_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, list) or not data:
            return
        self._messages = data

    def _persist_session_to_disk(self) -> None:
        if not self.remember or not self.memory_file:
            return
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.write_text(
            json.dumps(self._messages, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def reset(self) -> None:
        self._messages = [{"role": "system", "content": self.system_prompt}]
        self._persist_session_to_disk()

    def chat(self, user_message: str) -> str:
        """한 턴 처리. 연속 도구: 루프 안에서 API ↔ tool 메시지를 반복합니다."""
        if not self.remember:
            self._messages = [{"role": "system", "content": self.system_prompt}]
        self._messages.append({"role": "user", "content": user_message})

        chat_url = f"{self.base_url}/api/chat"
        ws = self.workspace_root or Path.cwd().resolve()

        with httpx.Client(timeout=self.timeout) as client:
            for _ in range(self.max_tool_rounds):
                payload: dict[str, Any] = {
                    "model": self.model,
                    "messages": _deep_copy_messages(self._messages),
                    "stream": False,
                }
                if self.use_tools:
                    payload["tools"] = TOOL_DEFINITIONS

                r = client.post(chat_url, json=payload)
                r.raise_for_status()
                data = r.json()
                msg = data.get("message")
                if not isinstance(msg, dict):
                    raise RuntimeError(f"Ollama 응답 형식 오류: {data!r}")

                self._messages.append(msg)
                tool_calls = msg.get("tool_calls")

                if not tool_calls:
                    content = msg.get("content")
                    if content is None:
                        self._persist_session_to_disk()
                        return ""
                    text = str(content).strip()
                    if self.use_tools and text:
                        pseudo = _text_looks_like_tool_json(text)
                        if pseudo is not None:
                            fn = str(pseudo.get("name"))
                            args = pseudo.get("arguments", {})
                            out = _run_dispatch(fn, args, ws)
                            _append_tool_message(self._messages, fn, out)
                            continue
                    self._persist_session_to_disk()
                    return text

                for tc in tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    fn_block = tc.get("function") or {}
                    name = fn_block.get("name")
                    if not name:
                        continue
                    args = fn_block.get("arguments")
                    out = _run_dispatch(str(name), args, ws)
                    _append_tool_message(
                        self._messages,
                        str(name),
                        out,
                        tool_call_id=str(tc["id"]) if tc.get("id") else None,
                    )

            raise RuntimeError(
                f"도구 루프가 max_tool_rounds({self.max_tool_rounds})에 도달했습니다."
            )
