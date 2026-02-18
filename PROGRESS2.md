# Ageis Agent — 개발 진행 현황 및 인수인계 가이드 (통합본)

> **최종 업데이트:** 2026-02-18
> **완료 Phase:** Phase 1 (The Body), Phase 2 (The Brain)
> **다음 Phase:** Phase 3 (The Soul)

---

## 🚀 완료된 작업 요약

### Phase 1: 튼튼한 뼈대 (The Body)
> **Rust 코어 데몬(gRPC 서버)과 Python 에이전트(gRPC 클라이언트) 간의 안전한 통신 기반 구축**

- **IPC 통신**: `agent.proto` 계약을 통해 Rust와 Python 간의 강타입(Type-Safe) 통신 구현 (파일 읽기/쓰기, 명령 실행, 채팅 스트리밍).
- **보안 샌드박스**: `sandbox.rs` 모듈을 통해 `Agent_Workspace` 외부로의 파일 접근을 원천 차단 (Path Traversal 방어 및 Windows UNC 경로 정규화).
- **gRPC 서버**: Rust `tonic` 프레임워크를 사용하여 고성능 비동기 서버 구축 (포트 50051).
- **Python 클라이언트**: `grpcio`를 사용하여 Rust 서버와 연결하고, 파일 I/O 및 명령 실행 요청을 전송하는 래퍼 클래스(`AgentGrpcClient`) 구현.

### Phase 2: 깨어난 지능 (The Brain)
> **LLM(Ollama)과 연동하여 스스로 생각하고 행동하는 에이전트 구현**

- **Router (의도 분류기)**: 사용자 입력을 분석하여 대화(CHAT), 파일 작업(FILE), 웹 검색(WEB), 복합 작업(TASK), 설정 변경(PERSONA)으로 자동 분류.
- **ReAct Loop (추론 루프)**: `Thought`(생각) -> `Action`(행동) -> `Observation`(관찰) 과정을 10회까지 반복하며 복잡한 태스크를 해결.
- **도구(Tools)**:
    -   `file_reader`: Rust 게이트웨이를 경유하여 안전하게 파일을 읽고 씀.
    -   `web_scraper`: `httpx`와 `BeautifulSoup4`를 이용해 웹 페이지 텍스트 추출 (최대 2000자).

---

## 📂 프로젝트 구조 (구현 완료본)

```
Ageis/
├── proto/
│   └── agent.proto                # gRPC 서비스 계약서 (Rust↔Python 통신 인터페이스)
│
├── rust_core/                      # [Phase 1] Rust 코어 데몬 (보안 게이트웨이)
│   ├── Cargo.toml                 # 의존성 (tonic, prost, tokio, dunce 등)
│   ├── Cargo.lock                 # [포함됨] 바이너리 크레이트이므로 커밋 권장 (.gitignore 예외 처리됨)
│   └── src/
│       ├── main.rs                # 진입점: CLI 인자(--port, --workspace) 파싱 → gRPC 서버 시작
│       ├── server.rs              # AgentBroker 서비스 구현체
│       └── sandbox.rs             # 보안 핵심: Path Traversal 방어 (Windows 경로 정규화 포함)
│
├── python_agent/                   # [Phase 2] Python 지능형 에이전트
│   ├── pyproject.toml             # 의존성 관리 (grpcio, ollama, httpx, beautifulsoup4 포함됨)
│   ├── grpc_client.py             # Rust 데몬 gRPC 클라이언트 래퍼
│   ├── main.py                    # 통합 진입점 (Router + ReAct Agent 연결)
│   ├── router.py                  # 의도 분류기 (LLM 기반)
│   ├── react_loop.py              # 추론 루프 (Thinking Process)
│   └── tools/
│       ├── __init__.py            # [포함됨] 패키지 초기화 파일
│       ├── file_reader.py         # 파일 도구 (gRPC 래퍼)
│       └── web_scraper.py         # 웹 크롤러
│
└── Agent_Workspace/                # 샌드박스 허용 디렉토리 (에이전트가 접근 가능한 유일한 영역)
```

---

## 🛠️ 빌드 및 실행 가이드

1. **Rust Core 실행** (필수)
   ```bash
   cd rust_core
   # 최초 빌드
   cargo build --release
   # 실행 (50051 포트 사용)
   cargo run --release -- --port 50051 --workspace ../Agent_Workspace
   ```

2. **Ollama 실행** (필수)
   ```bash
   ollama serve
   # 모델이 없다면: ollama pull llama3.2
   ```

3. **Python Agent 실행**
   ```bash
   cd python_agent
   # 의존성 동기화 (최초 1회)
   uv sync
   # 실행
   uv run python main.py
   ```

---

## 👉 다음 단계: Phase 3 인수인계 가이드 (The Soul)

> **목표:** 에이전트에게 **장기 기억(Memory)** 과 **고유 인격(Persona)** 부여.

### 1단계: 의존성 추가
현재 `pyproject.toml`에는 Phase 2 의존성(`ollama`, `httpx`, `beautifulsoup4`)까지는 이미 추가되어 있습니다.
Phase 3 구현을 위해 다음 패키지를 **새로 추가**해야 합니다:
```bash
cd python_agent
uv add chromadb pyyaml
```

### 2단계: Memory 시스템 구현 (`python_agent/memory.py`)
- **개요**: 대화 내용을 임베딩하여 로컬 DB(ChromaDB)에 저장하고, 필요할 때 검색(RAG)합니다.
- **참고**: `CLAUDE.md` Phase 3 섹션.
- **주요 기능**: `save(text, metadata)`, `recall(query, n=5)`.

### 3단계: Persona 시스템 구현 (`python_agent/persona.py`)
- **개요**: `Agent_Workspace/persona.yaml` 설정 파일을 읽어 시스템 프롬프트를 동적으로 구성합니다.
- **로직**: `기본 성격` + `현재 상황` + `검색된 기억` = `최종 프롬프트`.
- **통합**: `main.py` 또는 `react_loop.py`에서 이 모듈을 호출하여 LLM의 페르소나를 설정합니다.

---

이 문서를 바탕으로 Phase 3 개발을 진행하시면 됩니다. 🚀
