"""Ollama HTTP API와 통신하는 단순 에이전트."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass
class Agent:
    """로컬 Ollama `/api/chat` 엔드포인트에 질의를 보냅니다."""

    model: str = "qwen2.5-coder:7b"
    base_url: str = "http://localhost:11434"
    timeout: float = 120.0

    def __post_init__(self) -> None:
        env_model = os.environ.get("OLLAMA_MODEL")
        if env_model:
            self.model = env_model
        env_base = os.environ.get("OLLAMA_HOST")
        if env_base:
            self.base_url = env_base.rstrip("/")

    def chat(self, user_message: str, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_message})

        url = f"{self.base_url}/api/chat"
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        msg = data.get("message", {})
        content = msg.get("content")
        if content is None:
            raise RuntimeError(f"Unexpected Ollama response: {data!r}")
        return content
