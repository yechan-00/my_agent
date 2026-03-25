# my_agent

uv 패키지 매니저로 관리하는 Python 프로젝트입니다. 로컬 [Ollama](https://ollama.com/)의 Qwen 모델과 HTTP API로 대화하는 최소 에이전트입니다.

## 사전 준비

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Ollama 실행 중, Qwen 모델 설치 (예: `ollama pull qwen2.5-coder:7b`)

## 설치

```bash
cd my_agent
uv sync
```

## 실행

```bash
# 대화 루프
uv run my-agent

# 한 줄 질문
uv run my-agent -m "간단히 자기소개 해줘"
```

환경 변수(선택):

| 변수 | 설명 |
|------|------|
| `OLLAMA_MODEL` | 기본값 `qwen2.5-coder:7b` 대체 |
| `OLLAMA_HOST` | 기본값 `http://localhost:11434` 대체 |

## 패키지 구조

- `src/my_agent/agent.py` — Ollama `/api/chat` 클라이언트
- `src/my_agent/main.py` — CLI 진입점

## 빌드 확인

```bash
uv build
```

산출물은 `dist/`에 생성됩니다(저장소에는 포함하지 않음).
