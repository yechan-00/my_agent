# my_agent

uv로 관리하는 **Ollama 기반 도구 호출 에이전트**입니다. 과제 평가 항목(모델·파일·나무위키·연속 도구·문서화)을 맞출 수 있도록 설계했습니다.

## 과제 평가 기준 충족 (100점 설계)

| 배점 | 평가 항목 | 이 프로젝트에서의 대응 |
|------|-----------|------------------------|
| 20 | Ollama 설치 및 **`qwen2.5-coder:7b` 실행** | `ollama pull qwen2.5-coder:7b` 후 사용. 모델 자동 선택 시 **해당 태그가 있으면 최우선**(`agent.COURSE_MODEL`). 실행 스크린샷·`ollama list` 권장. |
| 20 | **파일 생성·읽기·수정** 도구 | `write_file`(생성/덮어쓰기), `read_file`, `replace_in_file` — 구현은 `file_ops.py`, 스키마는 `tools.py`. |
| 20 | **나무위키** 검색·내용 추출 | `namu_search`(검색 페이지 파싱), `namu_fetch`(`https://namu.wiki/raw/…` 위키텍스트). 구현: `namuwiki.py`. |
| 30 | **한 질문당 도구 연속 2회 이상** + **동작 원리 설명** | `Agent.chat()`의 `for` 루프가 API 응답에 `tool_calls`가 있는 동안 도구 실행 → `tool` 메시지 추가 → **다시** `/api/chat` 호출을 반복(`max_tool_rounds`). 원리: 아래 절 + `agent.py` docstring. |
| 10 | 코드 품질·주석·**실행 결과 캡처** | 모듈별 주석, 본 README, 터미널/도구 호출 로그 스크린샷을 보고서에 첨부. |

### 연속 도구 호출 동작 원리 (요약)

1. 사용자 한 턴이 `messages`에 쌓인다.  
2. Ollama에 `messages` + `tools` 정의를 보낸다.  
3. 모델이 `tool_calls`를 반환하면, 로컬에서 `dispatch_tool`로 각 도구를 실행하고 결과를 `role: tool` 메시지로 붙인다.  
4. **다시 2로** 돌아가므로, 한 질문 안에서 `namu_search` → `namu_fetch`처럼 **연쇄 호출**이 가능하다.  
5. 모델이 텍스트만 주면 그 내용을 사용자에게 반환한다.

### 시연용 질문 예

- 나무위키 2회 이상: *「나무위키에서 파이썬 검색한 뒤, 적절한 문서 하나 골라 본문 앞부분만 요약해 줘」* → `namu_search` 후 `namu_fetch` 유도.  
- 파일 2회 이상: *「`memo.txt` 읽고, 마지막 줄에 오늘 날짜 한 줄 추가해서 저장해 줘」* → `read_file` 후 `write_file`(또는 읽은 뒤 병합해 `write_file`).

## 에이전트가 하는 일

| 구성 요소 | 설명 |
|-----------|------|
| **LLM** | 자동 선택 시 **`qwen2.5-coder:7b` 우선**. `OLLAMA_MODEL` / `--model`으로 고정 가능. |
| **페르소나** | `persona.py` — 파일·나무위키·**연속 도구 호출** 지시. |
| **대화 기록** | 메모리 + 선택적 `--persist` / `AGENT_MEMORY_FILE`. `/reset`으로 초기화. |
| **파일 도구** | `read_file`, `write_file`, `replace_in_file` (`--workspace` / `AGENT_WORKSPACE` 하위만). |
| **나무위키** | `namu_search`, `namu_fetch` |
| **기타** | `get_current_time`, `add` |
| **CLI** | `main.py`, `./run` — `--workspace`, `--persist`, `--no-tools` 등 |

코드에서 쓰려면:

```python
from my_agent import Agent

agent = Agent()
print(agent.chat("안녕"))
```

## 사전 준비

- Python 3.11 이상 (또는 uv가 사용할 인터프리터)
- [uv](https://docs.astral.sh/uv/) 설치
- [Ollama](https://ollama.com/) 설치·실행
- **과제 권장:** `qwen2.5-coder:7b` (없으면 자동 선택이 다른 설치 모델을 고름)

```bash
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

## 가장 편한 실행

- **설치된 Ollama 모델을 자동으로 고릅니다** (`llama3.2` → `qwen2.5` 순 우선). `OLLAMA_MODEL`이 있으면 그걸 씁니다.

**터미널에 그대로** — `my_agent` 폴더까지 **절대 경로**만 맞추면, `cd` 없이 실행됩니다.

```bash
bash "/절대/경로/my_agent/run"
```

**프로젝트 폴더 안이라면:**

```bash
./run
```

`./chat` 은 `./run` 과 동일합니다.

**`uv`만 사용 (현재 작업 폴더 무관):**

```bash
uv run --project "/절대/경로/my_agent" my-agent -e
```

한 줄 질문:

```bash
bash "/절대/경로/my_agent/run" -m "안녕"
```

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

### 3) 옵션

| 옵션 | 설명 |
|------|------|
| `--workspace DIR` | 파일 읽기/쓰기/수정 도구가 허용하는 루트 폴더 |
| `--persist` | 대화 기록을 `<workspace>/.my_agent_memory.json` 등에 저장 |
| `--memory-file PATH` | 저장할 JSON 경로 (`--persist`만 줄 때 기본값과 함께 사용) |
| `--no-tools` | 도구 정의를 보내지 않음 |
| `--no-memory` | 매 질문만 독립 처리 (메모리·디스크 기록 안 씀) |

```bash
# 파일 도구 허용 범위를 현재 폴더로 제한 + 재실행 시 대화 이어가기
uv run my-agent --workspace . --persist

uv run my-agent --no-tools -m "그냥 잡담만 할게"
uv run my-agent --no-memory -m "이전 말은 잊고, 1+1은?"
```

환경 변수: `AGENT_WORKSPACE`, `AGENT_MEMORY_FILE`(JSON 경로), 기존과 같이 `OLLAMA_MODEL`, `OLLAMA_HOST`.

### 4) 모델·호스트 바꾸기

다른 Qwen/모델이나 Ollama 주소를 쓸 때 사용합니다.

```bash
# 옵션으로 지정
uv run my-agent -m "Hello" --model llama3.2:latest --base-url http://localhost:11434
```

또는 환경 변수로 지정할 수 있습니다.

```bash
export OLLAMA_MODEL=llama3.2:latest
export OLLAMA_HOST=http://localhost:11434
uv run my-agent -m "ping"
```

| 환경 변수 | 설명 | 기본값 |
|-----------|------|--------|
| `OLLAMA_MODEL` | Ollama에 등록된 모델 이름 | `llama3.2:latest` |
| `OLLAMA_HOST` | Ollama 서버 URL (끝에 `/` 없이) | `http://localhost:11434` |

대화 모드에서는 **`/reset`** 을 입력하면 기록만 지우고 시스템 페르소나는 유지합니다.

### 5) Python 모듈로 실행

```bash
uv run python -m my_agent -m "한 줄 질문"
```

(`-m my_agent`는 패키지 실행, 뒤의 `-m "..."`는 CLI의 메시지 옵션입니다.)

### 6) 오류가 날 때

- **연결 거부 / timeout**: Ollama 앱(또는 `ollama serve`)이 실행 중인지 확인합니다.
- **모델을 찾을 수 없음**: `ollama list`로 모델 이름을 확인하고 `OLLAMA_MODEL` 또는 `--model`을 맞춥니다.

---

## 패키지 구조

- `src/my_agent/persona.py` — 시스템 프롬프트(파일·나무위키·연속 도구)
- `src/my_agent/file_ops.py` — 파일 읽기/쓰기/치환 함수
- `src/my_agent/namuwiki.py` — 나무위키 검색·raw 본문 추출
- `src/my_agent/tools.py` — Ollama `tools` 스키마 + `dispatch_tool`
- `src/my_agent/agent.py` — 연속 도구 루프, `/api/chat`, `COURSE_MODEL` 우선 선택
- `src/my_agent/main.py` — CLI

## 빌드 확인

```bash
uv build
```

산출물은 `dist/`에 생성됩니다. 이 폴더는 `.gitignore`에 포함되어 저장소에는 올라가지 않습니다.
