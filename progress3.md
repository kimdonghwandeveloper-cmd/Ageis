# Phase 3 완료 보고서 — 자아 형성 (The Soul)

> 작성일: 2026-02-18

---

## 완료된 작업

### 1. 장기 기억 모듈 (`python_agent/memory.py`) — 신규

`AgentMemory` 클래스 구현 완료.

- **저장소:** ChromaDB `PersistentClient` → `Agent_Workspace/.chroma/` 디렉토리에 SQLite 기반 영구 저장
- **임베딩:** Ollama `nomic-embed-text` 모델 사용 (`_embed()` 메서드)
- **save(text, metadata):** uuid 생성 후 임베딩+문서+메타데이터 저장. 메타데이터에 `type`(chat/task)과 `timestamp` 포함
- **recall(query, n_results=5):** 코사인 유사도 검색으로 관련 기억 반환. 컬렉션이 비어있으면 빈 리스트 반환 (에러 방지)
- 경로는 `Path(__file__)`로 프로젝트 루트 기준 자동 계산

### 2. 페르소나 모듈 (`python_agent/persona.py`) — 신규

- **load_persona(path):** `Agent_Workspace/persona.yaml`을 YAML로 로드
- **build_system_prompt(user_query, memory):** 페르소나 설정(이름, 성격, 제약조건) + `memory.recall()` 결과를 결합해 최종 시스템 프롬프트 문자열 생성
- 경로는 `Path(__file__)`로 프로젝트 루트 기준 자동 계산

### 3. 페르소나 설정 파일 (`Agent_Workspace/persona.yaml`) — 신규

기본값:
- name: `Aria`
- tone: `professional`
- language: `ko`
- verbosity: `concise`
- 절대 금지 행동 3개, 콘텐츠 정책 1개 정의

### 4. ReAct 루프 수정 (`python_agent/react_loop.py`)

- `__init__`에 `memory=None` 파라미터 추가
- `run()` 시작 시: `memory`가 있으면 `build_system_prompt()`로 페르소나+기억 프롬프트 생성 → 기존 ReAct 도구 프롬프트 앞에 결합
- `run()` 종료 시: Final Answer 도달하면 `memory.save()` 호출 (task+answer 쌍 저장)

### 5. 메인 진입점 수정 (`python_agent/main.py`)

- `AgentMemory` 인스턴스를 한 번 생성하여 `ReActAgent`에 주입
- `handle_chat()`에서 `build_system_prompt()`로 페르소나+기억 적용 후 응답, 응답 후 `memory.save()` 호출
- PERSONA 인텐트 처리: "persona.yaml 직접 수정 후 재시작" 안내 메시지로 변경
- 시작 배너: `Phase 3: The Soul`로 변경

### 6. 의존성 업데이트 (`python_agent/pyproject.toml`)

- `chromadb>=0.6`, `pyyaml>=6.0` 추가
- **Python 최소 버전 3.10 → 3.11로 상향** (chromadb → onnxruntime이 3.11+ 필요)
- `.python-version` 파일도 `3.11`로 업데이트됨
- `py-modules`에 `memory`, `persona`, `router`, `react_loop` 추가
- `uv sync` 완료, 85개 패키지 설치 확인

---

## 현재 프로젝트 파일 구조

```
ageis/
├── CLAUDE.md                         # 마스터 플랜
├── progress3.md                      # 이 파일
├── proto/
│   └── agent.proto                   # gRPC 서비스 스키마
├── rust_core/
│   ├── Cargo.toml
│   ├── build.rs
│   └── src/
│       ├── main.rs                   # Rust 데몬 진입점
│       ├── server.rs                 # gRPC 서버 구현
│       └── sandbox.rs                # 샌드박스 경로 검증
├── python_agent/
│   ├── pyproject.toml                # uv 프로젝트 (Python >=3.11)
│   ├── .python-version               # 3.11
│   ├── main.py                       # 진입점 (Phase 3 완료)
│   ├── router.py                     # 의도 분류기 (Phase 2)
│   ├── react_loop.py                 # ReAct 루프 (메모리 통합)
│   ├── memory.py                     # 장기 기억 (ChromaDB + RAG)
│   ├── persona.py                    # 페르소나 로더 + 프롬프트 빌더
│   ├── grpc_client.py                # Rust 코어 gRPC 클라이언트
│   ├── generate_proto.py             # proto 코드 생성 스크립트
│   ├── agent_pb2.py                  # (자동 생성) protobuf 메시지
│   ├── agent_pb2_grpc.py             # (자동 생성) gRPC 스텁
│   └── tools/
│       ├── __init__.py
│       ├── file_reader.py            # 파일 읽기/쓰기 도구
│       └── web_scraper.py            # 웹 크롤러 도구
└── Agent_Workspace/
    ├── persona.yaml                  # 에이전트 성격 설정
    └── .chroma/                      # ChromaDB 벡터 DB (자동 생성)
        └── chroma.sqlite3
```

---

## 데이터 흐름 (Phase 3 완성)

```
사용자 입력
  → Router: 의도 분류 (CHAT / FILE / WEB / TASK / PERSONA)
  │
  ├─ CHAT 경로:
  │   → Memory.recall(): 관련 기억 검색
  │   → Persona: 시스템 프롬프트 조립 (성격 + 기억)
  │   → Ollama 직접 호출 → 응답
  │   → Memory.save(): 대화 저장
  │
  ├─ FILE/WEB/TASK 경로:
  │   → Memory.recall(): 관련 기억 검색
  │   → Persona + ReAct: 시스템 프롬프트 조립 (성격 + 기억 + 도구 설명)
  │   → ReAct Loop: LLM 추론 + 도구 사용 (gRPC 경유)
  │   → Memory.save(): 태스크+결과 저장
  │
  └─ PERSONA 경로:
      → "persona.yaml 수정 후 재시작" 안내
```

---

## 검증 결과

| 항목 | 상태 |
|------|------|
| `uv sync` 의존성 설치 | 통과 (85 패키지) |
| `memory.py` import + AgentMemory 초기화 | 통과 |
| `persona.py` import + persona.yaml 로드 | 통과 (name=Aria, tone=professional) |
| ChromaDB `.chroma/chroma.sqlite3` 생성 | 통과 |
| 모듈 간 의존성 해결 (memory↔persona↔react_loop↔main) | 통과 |

### 미검증 (Ollama + Rust 서버 필요)

- `memory.save()` / `recall()` 실제 임베딩 동작 → `nomic-embed-text` 모델이 Ollama에 pull 되어 있어야 함
- ReAct 루프에서 페르소나+기억 프롬프트가 LLM 응답에 반영되는지
- 대화 반복 후 recall 결과가 유의미하게 돌아오는지

---

## 주의사항 / 알려진 이슈

1. **Python 버전 변경:** 3.10 → 3.11 필수. 이전 venv는 삭제하고 `uv sync`로 재생성해야 함
2. **Ollama 모델 필요:** 실행 전 `ollama pull nomic-embed-text`와 `ollama pull llama3.2` 실행 필요
3. **persona.yaml 경로:** `Path(__file__)` 기반으로 프로젝트 루트를 자동 계산하므로 `python_agent/` 디렉토리에서 실행해야 정상 동작
4. **ChromaDB 초기 상태:** 컬렉션이 비어있을 때 `recall()`이 빈 리스트 반환하도록 처리 완료 (첫 실행 에러 방지)

---

# Phase 4 인수인계 — 확장 및 사용자 경험 (Expansion & UX)

## 개요

Phase 4는 에이전트를 일반 사용자/개발자가 쉽게 사용하고 확장할 수 있도록 포장하는 단계.
크게 **3가지 목표**가 있다.

---

## 목표 1: 커스텀 플러그인 생태계

### 할 일

1. **`python_agent/plugin_loader.py` 신규 생성**
   - `Agent_Workspace/plugins/` 폴더의 `.py` 파일을 자동 스캔
   - 각 파일에서 `TOOL_NAME`, `TOOL_DESCRIPTION`, `run(args)` 규격을 확인하고 도구로 등록
   - `load_plugins() -> dict` 함수 구현

2. **`main.py` 수정**
   - 시작 시 `load_plugins()` 호출하여 반환된 도구들을 기존 `TOOLS` 딕셔너리에 병합
   - `ReActAgent` 인스턴스 생성 전에 플러그인 로드 완료

3. **`Agent_Workspace/plugins/` 디렉토리 생성**
   - 예제 플러그인 파일 1개 작성 (`my_tool.py` 등)

### 플러그인 규격 (CLAUDE.md 참조)

```python
# Agent_Workspace/plugins/my_tool.py
TOOL_NAME = "my_custom_tool"
TOOL_DESCRIPTION = "사용자가 정의한 도구"

def run(args: dict) -> str:
    return f"플러그인 실행 결과: {args}"
```

### 주의사항
- `_`로 시작하는 파일은 무시
- 플러그인 로드 실패 시 에러 출력하되 다른 플러그인/시스템에 영향 없이 계속 진행
- 플러그인 도구는 ReAct 루프의 도구 설명에도 자동 반영되어야 함

---

## 목표 2: CLI 대시보드

### 할 일

1. **의존성 추가:** `uv add rich prompt-toolkit`
2. **`python_agent/cli.py` 신규 생성**
   - `rich` 라이브러리로 패널, 컬러, 스피너 등 시각적 대시보드
   - `prompt-toolkit`으로 향상된 입력 (히스토리, 자동완성 등)
   - 기존 `main.py`의 `input()` 루프를 `rich` 기반으로 교체

### CLAUDE.md 참조 코드

```python
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

def cli_main(agent):
    console.print(Panel.fit(
        "[bold cyan]Ageis Agent[/bold cyan]\n"
        "Type your command. Use [bold]/quit[/bold] to exit.",
        border_style="cyan"
    ))
    while True:
        user_input = Prompt.ask("[bold green]You[/bold green]")
        if user_input.strip().lower() in ("/quit", "/exit"):
            break
        with console.status("[bold]Thinking...[/bold]"):
            result = agent.run(user_input)
        console.print(Panel(result, title="[bold magenta]Agent[/bold magenta]",
                            border_style="magenta"))
```

### 통합 포인트
- `main.py`에서 CLI 모드 선택 가능하게 (기존 plain 모드 vs rich 모드)
- `--cli` 또는 `--rich` 플래그로 전환하거나, rich 설치 여부에 따라 자동 선택

---

## 목표 3: 로컬 웹 UI

### 할 일

1. **의존성 추가:** `uv add fastapi "uvicorn[standard]" websockets`
2. **`python_agent/web_ui.py` 신규 생성**
   - FastAPI + WebSocket 기반 실시간 채팅 UI
   - `localhost:8000`에서 서빙
   - WebSocket `/ws` 엔드포인트로 에이전트와 양방향 통신

### 핵심 구현 포인트
- WebSocket 핸들러에 실제 `agent` 인스턴스를 주입해야 함 (CLAUDE.md 코드에서 `agent=None`으로 되어 있는 부분)
- `memory`와 `persona`도 웹 UI 경로에서 동일하게 동작해야 함
- `main.py`에서 `--web` 플래그로 웹 UI 모드 실행 가능하게

### CLAUDE.md 참조 HTML
- 인라인 HTML/CSS/JS 단일 파일로 제공 (별도 프론트엔드 빌드 불필요)
- 다크 테마, 모노스페이스 폰트, 800px max-width

---

## Phase 4 의존성 요약

```bash
cd python_agent

# CLI 대시보드
uv add rich prompt-toolkit

# 웹 UI
uv add fastapi "uvicorn[standard]" websockets
```

`pyproject.toml`의 `py-modules`에 `plugin_loader`, `cli`, `web_ui` 추가 필요.

---

## Phase 4 권장 작업 순서

```
1. plugin_loader.py 구현 + 예제 플러그인 + main.py 연동
   └─ 테스트: 예제 플러그인이 ReAct 도구로 인식되는지 확인

2. cli.py 구현 + main.py에서 모드 선택 분기
   └─ 테스트: rich 패널, 스피너, 컬러 출력 확인

3. web_ui.py 구현 + main.py에서 --web 모드 분기
   └─ 테스트: 브라우저에서 localhost:8000 접속, WebSocket 채팅 동작 확인

4. 통합 테스트: 플러그인 + CLI + 웹 UI 모두 정상 동작
5. pyproject.toml 최종 정리
```

---

## Phase 4 완료 후 전체 시스템 상태

```
Phase 1 (The Body)  ✅  gRPC 통신 + Rust 샌드박스
Phase 2 (The Brain) ✅  Router + ReAct 루프 + 기초 도구
Phase 3 (The Soul)  ✅  ChromaDB RAG + 페르소나
Phase 4 (Expansion) ⬜  플러그인 + CLI + 웹 UI
```
