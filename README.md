# my_agent

uv 패키지 매니저로 관리하는 Python 프로젝트입니다. 로컬 [Ollama](https://ollama.com/)의 Qwen 모델과 HTTP API로 대화하는 최소 에이전트입니다.

## 사전 준비

- Python 3.11 이상 (또는 uv가 사용할 인터프리터)
- [uv](https://docs.astral.sh/uv/) 설치
- [Ollama](https://ollama.com/) 설치·실행
- Qwen 등 사용할 모델 다운로드

```bash
# 모델이 없으면 한 번 받기 (예시)
ollama pull qwen2.5-coder:7b
```

Ollama가 켜져 있는지 확인합니다. 기본 주소는 `http://localhost:11434` 입니다.

---

## 설치

저장소를 받은 뒤 프로젝트 폴더에서 의존성을 맞춥니다.

```bash
git clone https://github.com/yechan-00/my_agent.git
cd my_agent
uv sync
```

이미 클론했다면 `my_agent` 디렉터리만 들어가 `uv sync` 하면 됩니다.

---

## 실행 방법

아래 명령은 **반드시 `my_agent` 프로젝트 루트**에서 실행합니다.

### 1) 대화 모드 (연속 입력)

터미널에서 메시지를 반복 입력합니다. 끝낼 때는 `quit`, `exit`, `q` 중 하나를 입력합니다.

```bash
uv run my-agent
```

### 2) 한 번만 질문하기

```bash
uv run my-agent -m "간단히 자기소개 해줘"
```

### 3) 모델·호스트 바꾸기

다른 Qwen/모델이나 Ollama 주소를 쓸 때 사용합니다.

```bash
# 옵션으로 지정
uv run my-agent -m "Hello" --model qwen2.5-coder:7b --base-url http://localhost:11434
```

또는 환경 변수로 지정할 수 있습니다.

```bash
export OLLAMA_MODEL=qwen2.5-coder:7b
export OLLAMA_HOST=http://localhost:11434
uv run my-agent -m "ping"
```

| 환경 변수 | 설명 | 기본값 |
|-----------|------|--------|
| `OLLAMA_MODEL` | Ollama에 등록된 모델 이름 | `qwen2.5-coder:7b` |
| `OLLAMA_HOST` | Ollama 서버 URL (끝에 `/` 없이) | `http://localhost:11434` |

### 4) Python 모듈로 실행

```bash
uv run python -m my_agent -m "한 줄 질문"
```

(`-m my_agent`는 패키지 실행, 뒤의 `-m "..."`는 CLI의 메시지 옵션입니다.)

### 5) 오류가 날 때

- **연결 거부 / timeout**: Ollama 앱(또는 `ollama serve`)이 실행 중인지 확인합니다.
- **모델을 찾을 수 없음**: `ollama list`로 모델 이름을 확인하고 `OLLAMA_MODEL` 또는 `--model`을 맞춥니다.

---

## 패키지 구조

- `src/my_agent/agent.py` — Ollama `/api/chat` 클라이언트
- `src/my_agent/main.py` — CLI 진입점

## 빌드 확인

```bash
uv build
```

산출물은 `dist/`에 생성됩니다. 이 폴더는 `.gitignore`에 포함되어 저장소에는 올라가지 않습니다.
