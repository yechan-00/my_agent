"""CLI 진입점: 한 번 질문하거나 대화 루프."""

from __future__ import annotations

import argparse
import sys

from my_agent.agent import Agent


def main() -> None:
    p = argparse.ArgumentParser(description="my_agent — Ollama 연동 챗")
    p.add_argument(
        "-m",
        "--message",
        help="한 번만 보낼 사용자 메시지 (없으면 대화 루프)",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Ollama 모델명 (기본: 환경변수 OLLAMA_MODEL 또는 qwen2.5-coder:7b)",
    )
    p.add_argument(
        "--base-url",
        default=None,
        help="Ollama 호스트 (기본: OLLAMA_HOST 또는 http://localhost:11434)",
    )
    args = p.parse_args()

    agent = Agent()
    if args.model:
        agent.model = args.model
    if args.base_url:
        agent.base_url = args.base_url.rstrip("/")

    if args.message:
        print(agent.chat(args.message))
        return

    print("대화 종료: quit 또는 exit 입력")
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
        try:
            reply = agent.chat(line)
        except Exception as e:  # noqa: BLE001 — CLI에서 원인 표시
            print(f"[error] {e}", file=sys.stderr)
            continue
        print(reply)


if __name__ == "__main__":
    main()
