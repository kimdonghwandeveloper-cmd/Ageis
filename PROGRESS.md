# Ageis Agent — 개발 진행 현황 및 인수인계 가이드

> **최종 업데이트:** 2026-02-17
> **완료 Phase:** Phase 1 (The Body)
> **다음 Phase:** Phase 2 (The Brain)

---

## 완료된 작업: Phase 1 — 뼈대 세우기

### 무엇을 만들었나

Rust 코어 데몬(gRPC 서버)과 Python 에이전트(gRPC 클라이언트) 간의 **통신 기반**과 **보안 샌드박스**를 구축했다.

### 파일별 역할

```
Ageis/
├── proto/
│   └── agent.proto                # gRPC 서비스 계약서 (Rust↔Python 통신 인터페이스)
│                                    서비스: AgentBroker
│                                    RPC 4개: RequestFileRead, RequestFileWrite,
│                                             ExecuteCommand, StreamChat
│                                    메시지 7개: FileRequest, FileResponse, FileWriteRequest,
│                                               StatusResponse, CommandRequest, CommandResponse,
│                                               ChatMessage
│
├── rust_core/                      # Rust 코어 데몬 (보안 게이트웨이)
│   ├── Cargo.toml                 # 의존성: tonic 0.12, prost 0.13, tokio, dunce, clap, tracing
│   ├── build.rs                   # 빌드 시 agent.proto → Rust 코드 자동 생성
│   └── src/
│       ├── main.rs                # 진입점: CLI 인자(--port, --workspace) 파싱 → gRPC 서버 시작
│       ├── server.rs              # AgentBroker 서비스 구현체
│       │                            - request_file_read: 샌드박스 경유 파일 읽기
│       │                            - request_file_write: 샌드박스 경유 파일 쓰기
│       │                            - execute_command: 화이트리스트 기반 명령 실행
│       │                            - stream_chat: 양방향 스트리밍 (현재 에코 모드)
│       └── sandbox.rs             # 보안 핵심: Path Traversal 방어
│                                    dunce::canonicalize()로 Windows UNC 경로 대응
│                                    Agent_Workspace 밖 접근 시 DENIED 반환
│                                    단위 테스트 2개 포함 (허용/거부 경로)
│
├── python_agent/                   # Python 에이전트 (마이크로서비스 레이어)
│   ├── pyproject.toml             # 의존성: grpcio, grpcio-tools
│   ├── .python-version            # Python 3.10 지정
│   ├── generate_proto.py          # agent.proto → agent_pb2.py, agent_pb2_grpc.py 생성 스크립트
│   ├── agent_pb2.py               # [자동생성] protobuf 메시지 클래스
│   ├── agent_pb2_grpc.py          # [자동생성] gRPC 스텁 (AgentBrokerStub)
│   ├── grpc_client.py             # Rust 데몬 gRPC 클라이언트 래퍼
│   │                                AgentGrpcClient 클래스: read_file(), write_file(),
│   │                                execute_command(), with문 지원
│   ├── main.py                    # gRPC 연결 테스트 (5개 테스트 케이스)
│   └── tools/
│       └── __init__.py            # 도구 패키지 초기화 (빈 상태)
│
└── Agent_Workspace/                # 샌드박스 허용 디렉토리 (에이전트가 접근 가능한 유일한 영역)
    └── .gitkeep
```

### 빌드 및 실행 방법

```bash
# 1. Rust 코어 데몬 빌드 (최초 1회)
cd rust_core
cargo build --release

# 2. Rust 서버 실행 (터미널 1)
cargo run --release -- --port 50051 --workspace ../Agent_Workspace

# 3. Python 의존성 설치 (최초 1회)
cd python_agent
uv sync

# 4. Proto → Python 코드 재생성 (agent.proto 수정 시에만)
uv run python generate_proto.py

# 5. Python 테스트 실행 (터미널 2, Rust 서버가 실행 중이어야 함)
uv run python main.py

# 6. Rust 단위 테스트
cd rust_core
cargo test
```

### 주의사항

- **Windows 빌드 시** `rust_core/target/` 폴더를 Windows Defender 실시간 검사 제외 목록에 추가해야 파일 잠금(os error 32) 에러가 발생하지 않는다.
- **proto 수정 시** Rust 쪽은 `cargo build`가 자동으로 재생성하지만, Python 쪽은 `generate_proto.py`를 수동 실행해야 한다.
- 모든 코드에 **줄별 한국어 주석**이 달려 있으므로 각 파일을 읽으면 동작 원리를 파악할 수 있다.

---

## 다음 작업: Phase 2 — 뇌 이식 (The Brain)

> 핵심 목표: LLM이 상황을 판단하고 행동할 수 있는 지능을 부여한다.

### 작업 순서

#### 1단계: Ollama 연동 준비

```bash
# Python 의존성 추가
cd python_agent
uv add ollama httpx beautifulsoup4
```

- Ollama가 로컬에 설치되어 있어야 한다 (`ollama serve` 실행 상태)
- 사용 모델: `llama3.2` (또는 원하는 모델로 변경 가능)

#### 2단계: Router (의도 분류기) 구현 — `python_agent/router.py`

CLAUDE.md의 Phase 2 > 목표 1 섹션에 코드 스켈레톤이 있다.

해야 할 일:
- `CLASSIFIER_PROMPT`를 사용해 사용자 입력을 5개 카테고리로 분류 (CHAT, FILE, WEB, TASK, PERSONA)
- `PIPELINE_MAP`에 따라 적절한 핸들러 함수로 라우팅
- Ollama 클라이언트를 사용해 분류 수행

#### 3단계: ReAct 루프 구현 — `python_agent/react_loop.py`

CLAUDE.md의 Phase 2 > 목표 2 섹션에 전체 코드가 있다.

해야 할 일:
- `ReActAgent` 클래스 구현 (Thought → Action → Observation 루프)
- `_parse_action()` 메서드로 LLM 출력에서 Action/Action Input 파싱
- 최대 10회 반복 후 자동 종료 (MAX_ITERATIONS)

#### 4단계: 기초 도구 2개 구현

**파일 리더** — `python_agent/tools/file_reader.py`
- 기존 `grpc_client.py`의 `AgentGrpcClient.read_file()`을 래핑
- ReAct 루프에서 `read_file` 도구로 등록

**웹 크롤러** — `python_agent/tools/web_scraper.py`
- httpx + BeautifulSoup4로 URL에서 텍스트 추출
- 최대 2000자로 잘라서 반환
- CLAUDE.md의 Phase 2 > 목표 3 섹션에 코드가 있다

#### 5단계: main.py에 통합

```python
# 최종적으로 main.py에서 이렇게 연결한다:
from tools.file_reader import read_file_tool
from tools.web_scraper import web_scrape_tool
from react_loop import ReActAgent
import ollama

TOOLS = {
    "read_file": read_file_tool,
    "web_scrape": web_scrape_tool,
}

agent = ReActAgent(tools=TOOLS, llm_client=ollama)
```

### 핵심 아키텍처 원칙 (반드시 지켜야 할 것)

1. **Python은 절대로 직접 파일시스템에 접근하지 않는다** — 모든 파일 I/O는 `grpc_client.py`를 통해 Rust 게이트웨이를 경유해야 한다.
2. **stream_chat RPC가 에코 모드로 되어 있다** — Phase 2에서 Ollama 연동 시 `server.rs`의 `stream_chat` 메서드를 수정하거나, Python 쪽에서 직접 Ollama API를 호출하는 방식 중 선택해야 한다. (CLAUDE.md 설계상 Python에서 직접 Ollama 호출이 맞다)
3. **명령어 화이트리스트**는 `server.rs`의 `execute_command` 메서드 안에 하드코딩되어 있다 — 새 명령어가 필요하면 이 목록을 확장해야 한다.

---

## 이후 Phase 참고

- **Phase 3 (The Soul):** ChromaDB RAG + 페르소나 시스템 → CLAUDE.md 참조
- **Phase 4 (Expansion):** 플러그인 로더 + CLI/Web UI → CLAUDE.md 참조

전체 설계 문서는 `CLAUDE.md`에 있다.
