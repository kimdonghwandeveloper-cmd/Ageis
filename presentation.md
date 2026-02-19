# Ageis Agent — 발표 자료

> **"보고, 듣고, 기억하고, 스스로 움직이는 완전 로컬 AI 에이전트"**
>
> 외부 클라우드 API 없이 내 PC 위에서만 동작하는
> 멀티모달 · 자율 실행 · 멀티에이전트 AI 시스템

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [전체 파일 구조](#2-전체-파일-구조)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [계층별 상세 설명](#4-계층별-상세-설명)
5. [데이터 흐름 지도](#5-데이터-흐름-지도)
6. [Phase별 개발 타임라인](#6-phase별-개발-타임라인)
7. [기술 스택 요약](#7-기술-스택-요약)
8. [핵심 설계 원칙](#8-핵심-설계-원칙)

---

## 1. 프로젝트 개요

### 한 줄 소개

> **Ageis**는 Ollama 로컬 LLM을 두뇌로 삼아,
> 텍스트·이미지·음성을 이해하고, 파일·웹·코드를 다루며,
> 스스로 일정을 잡고 파일 변화에 반응하는 **완전 오프라인 AI 에이전트**입니다.

### 무엇이 다른가

| 일반 챗봇 | Ageis |
|:----------|:------|
| 텍스트만 이해 | 텍스트 + 이미지 + 음성 |
| 대화만 가능 | 파일 읽기/쓰기, 웹 크롤링, 명령 실행 |
| 사람이 먼저 말해야 함 | 스케줄·파일 이벤트로 **먼저** 행동 |
| 단일 모델 | Manager → Researcher → Writer 멀티에이전트 |
| 클라우드 의존 | **100% 로컬**, 인터넷 불필요 |
| 기억 없음 | ChromaDB RAG로 **장기 기억** |
| 샌드박스 없음 | Rust 코어가 파일 접근을 **게이트 방어** |

---

## 2. 전체 파일 구조

```
Ageis/                                  ← 프로젝트 루트
│
├── CLAUDE.md                           ← 마스터 플랜 및 설계 명세
├── presentation.md                     ← 이 파일
├── progress{1~8}.md                    ← Phase별 완료 보고서
├── phase6_7_plan.md                    ← 구현 계획서
│
│   ┌─ 프로토콜 버퍼 스키마 ─────────────────────────────────┐
├── proto/
│   └── agent.proto                     ← gRPC 서비스 인터페이스 정의
│   └──────────────────────────────────────────────────────┘
│
│   ┌─ Rust 코어 데몬 (보안 게이트웨이) ──────────────────────┐
├── rust_core/
│   ├── Cargo.toml                      ← Rust 의존성
│   ├── build.rs                        ← .proto → Rust 코드 자동 생성
│   └── src/
│       ├── main.rs                     ← 진입점: CLI 인자 파싱, 서버 시작
│       ├── server.rs                   ← AgentBroker gRPC 서비스 구현
│       └── sandbox.rs                  ← 경로 검증 (Path Traversal 방어)
│   └──────────────────────────────────────────────────────┘
│
│   ┌─ Python 마이크로서비스 (두뇌) ───────────────────────────┐
├── python_agent/
│   ├── pyproject.toml                  ← 패키지 의존성 (uv 관리)
│   │
│   ├── ── 진입점 & 라우팅 ──
│   ├── main.py                         ← 애플리케이션 시작점
│   ├── router.py                       ← 의도 분류기 (9개 카테고리)
│   ├── core_logic.py                   ← 모든 핸들러의 통합 허브
│   │
│   ├── ── 인지 루프 ──
│   ├── react_loop.py                   ← ReAct(Thought→Action→Observation) 루프
│   │
│   ├── ── 기억 & 페르소나 ──
│   ├── memory.py                       ← ChromaDB RAG 파이프라인
│   ├── persona.py                      ← persona.yaml → 시스템 프롬프트 조립
│   │
│   ├── ── 자율 실행 (Phase 7) ──
│   ├── scheduler.py                    ← APScheduler: cron 기반 자동 실행
│   ├── event_monitor.py                ← watchdog: 파일 이벤트 자동 트리거
│   │
│   ├── ── 멀티에이전트 (Phase 8) ──
│   ├── actor.py                        ← AgentActor / AgentMessage 기반 클래스
│   ├── registry.py                     ← AgentRegistry: 메시지 버스
│   │
│   ├── ── Rust 통신 ──
│   ├── grpc_client.py                  ← Rust gRPC 서버 클라이언트
│   ├── generate_proto.py               ← .proto → Python 스텁 생성 스크립트
│   ├── agent_pb2.py                    ← [자동생성] protobuf 메시지 클래스
│   ├── agent_pb2_grpc.py               ← [자동생성] gRPC 서비스 스텁
│   │
│   ├── ── 플러그인 시스템 ──
│   ├── plugin_loader.py                ← plugins/ 폴더 동적 도구 로더
│   │
│   ├── ── UI 계층 ──
│   ├── cli.py                          ← CLI 대시보드 (Rich 터미널 UI)
│   ├── web_ui.py                       ← FastAPI + WebSocket 웹 UI
│   │
│   ├── tools/                          ← 도구 모음
│   │   ├── __init__.py
│   │   ├── file_reader.py              ← gRPC 경유 파일 읽기/쓰기
│   │   ├── web_scraper.py              ← HTTP + BeautifulSoup 웹 크롤링
│   │   ├── vision_tool.py              ← Ollama llava 이미지 분석
│   │   ├── stt_tool.py                 ← faster-whisper STT (로컬)
│   │   └── tts_tool.py                 ← pyttsx3 TTS (로컬)
│   │
│   └── agents/                         ← 전문화 에이전트 (Phase 8)
│       ├── __init__.py
│       ├── manager.py                  ← 관리자: 요청 분석 → 위임 결정
│       ├── researcher.py               ← 조사 전문가: 웹/파일 도구 활용
│       └── writer.py                   ← 작가: 정보 종합 → 문서 작성
│   └──────────────────────────────────────────────────────┘
│
│   ┌─ Tauri 데스크톱 앱 (Phase 5) ───────────────────────────┐
├── desktop/
│   ├── index.html                      ← 웹뷰 진입 HTML
│   └── src-tauri/
│       ├── tauri.conf.json             ← 앱 이름, 버전, 보안 정책
│       ├── src/
│       │   ├── main.rs                 ← OS 창 생성 및 사이드카 실행
│       │   └── lib.rs                  ← Tauri IPC 커맨드 핸들러
│       ├── bin/
│       │   └── ageis-agent-*.exe       ← Python 에이전트 사이드카 바이너리
│       ├── capabilities/               ← Tauri 권한 정의
│       └── icons/                      ← 앱 아이콘
│   └──────────────────────────────────────────────────────┘
│
│   ┌─ 에이전트 샌드박스 작업 공간 ────────────────────────────┐
└── Agent_Workspace/
    ├── persona.yaml                    ← 에이전트 이름/성격/제약조건 설정
    ├── schedules.yaml                  ← [런타임] cron 스케줄 규칙 저장소
    ├── watch_rules.yaml                ← [런타임] 파일 감시 규칙 저장소
    ├── .chroma/                        ← [런타임] ChromaDB 벡터 인덱스
    └── plugins/
        └── my_tool.py                  ← 커스텀 도구 플러그인 예시
    └──────────────────────────────────────────────────────┘
```

---

## 3. 시스템 아키텍처

### 3-A. 전체 구조 지도

```
╔══════════════════════════════════════════════════════════════════════╗
║                        사용자 인터페이스 계층                          ║
║                                                                      ║
║   ┌──────────────────┐   ┌──────────────────┐   ┌───────────────┐  ║
║   │  Tauri Desktop   │   │  Web UI (브라우저) │   │  CLI Terminal │  ║
║   │  (네이티브 앱)    │   │  localhost:8000   │   │  (Rich UI)    │  ║
║   └────────┬─────────┘   └────────┬──────────┘   └──────┬────────┘  ║
╚════════════╪════════════════════════╪══════════════════════╪══════════╝
             │ WebView / IPC          │ HTTP / WebSocket      │ stdin
╔════════════╪════════════════════════╪══════════════════════╪══════════╗
║            ▼                        ▼                       ▼         ║
║   ┌─────────────────────────────────────────────────────────────┐    ║
║   │              FastAPI 서버 (web_ui.py)                        │    ║
║   │                                                             │    ║
║   │  REST: /api/chat /api/vision /api/voice /api/society        │    ║
║   │        /api/schedule /api/schedules /api/watch /api/watches │    ║
║   │  WS:   /ws  (실시간 양방향 채팅)                             │    ║
║   └───────────────────────┬─────────────────────────────────────┘    ║
║                            │                                          ║
║   ┌────────────────────────▼──────────────────────────────────────┐  ║
║   │                   core_logic.py (통합 허브)                    │  ║
║   │                                                               │  ║
║   │  handle_chat()  handle_task()  handle_vision()  handle_voice()│  ║
║   │  handle_society()                                             │  ║
║   └──────┬──────────────────────────────────────────┬────────────┘  ║
║          │                                           │               ║
║   ┌──────▼────────────┐               ┌─────────────▼────────────┐  ║
║   │  router.py         │               │  Multi-Agent Society      │  ║
║   │  (의도 분류기)      │               │                           │  ║
║   │                   │               │  registry.py (메시지 버스)  │  ║
║   │  CHAT / FILE /    │               │       ┌──────────┐        │  ║
║   │  WEB / TASK /     │               │  ┌────▶ Manager  │        │  ║
║   │  VISION / VOICE / │               │  │    └──┬───────┘        │  ║
║   │  SCHEDULE /       │               │  │       │ delegate        │  ║
║   │  SOCIETY          │               │  │  ┌────▼──────────────┐ │  ║
║   └──────┬────────────┘               │  │  │ Researcher │Writer │ │  ║
║          │                            │  │  └────────────────────┘ │  ║
║   ┌──────▼────────────┐               │  └────────────────────────┘  ║
║   │  react_loop.py     │               │                              ║
║   │  (ReAct 인지 루프) │               │                              ║
║   │                   │               │                              ║
║   │  Thought →        │               │                              ║
║   │  Action →         │               │                              ║
║   │  Observation      │               │                              ║
║   └──────┬────────────┘               │                              ║
║          │                            │                              ║
║   ┌──────▼────────────────────────────▼──────────────────────────┐  ║
║   │                          도구 레이어 (tools/)                   │  ║
║   │                                                               │  ║
║   │   file_reader  web_scraper  vision_tool  stt_tool  tts_tool  │  ║
║   │   [plugin_loader → plugins/*.py 동적 로드]                    │  ║
║   └──────────────┬───────────────────────────────────────────────┘  ║
║                  │                                                    ║
║   ┌──────────────▼───────────────────────────────────────────────┐  ║
║   │                  자율 실행 계층                                 │  ║
║   │                                                               │  ║
║   │  scheduler.py              event_monitor.py                   │  ║
║   │  (APScheduler cron)        (watchdog 파일 감시)               │  ║
║   │   ↓ 시간 도달 시              ↓ 파일 이벤트 발생 시            │  ║
║   │  handle_task() 자동 호출     handle_task() 자동 호출           │  ║
║   └──────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
║   ┌──────────────────────────────────────────────────────────────┐  ║
║   │                  기억 & 페르소나 계층                           │  ║
║   │                                                               │  ║
║   │  memory.py (ChromaDB RAG)     persona.py (persona.yaml 로드) │  ║
║   │  ├── 대화 자동 저장            ├── 이름 / 성격 / 말투           │  ║
║   │  └── 관련 기억 검색 → 프롬프트 주입                            │  ║
║   └──────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
╚═══════════════════════════╪══════════════════════════════════════════╝
                             │  gRPC (grpc_client.py)
                             │  localhost:50051
╔═══════════════════════════▼══════════════════════════════════════════╗
║                   Rust 코어 데몬 (rust_core/)                         ║
║                                                                      ║
║   server.rs — AgentBroker gRPC 서비스                                ║
║   ┌──────────────────────────────────────────────────────────────┐  ║
║   │  RequestFileRead()    RequestFileWrite()    ExecuteCommand()  │  ║
║   │        │                     │                    │          │  ║
║   │        ▼                     ▼                    ▼          │  ║
║   │            sandbox.rs (경로 검증 게이트)                       │  ║
║   │                                                               │  ║
║   │   is_path_allowed() → Agent_Workspace 내부 여부 확인           │  ║
║   │   Agent_Workspace 외부 요청 → 즉시 DENIED 반환                 │  ║
║   └──────────────────────────────────────────────────────────────┘  ║
╚═══════════════════════════╪══════════════════════════════════════════╝
              ┌─────────────┴──────────────┐
              ▼                            ▼
   ┌──────────────────┐        ┌───────────────────────┐
   │  파일시스템       │        │  Ollama 로컬 LLM 서버  │
   │  Agent_Workspace │        │                       │
   │  (샌드박스 영역)  │        │  • llama3.2 (텍스트)  │
   └──────────────────┘        │  • llava    (비전)    │
                               │  • nomic-embed-text   │
                               │    (임베딩)           │
                               └───────────────────────┘
```

---

### 3-B. 멀티에이전트 소사이어티 내부 구조

```
사용자: "최신 AI 트렌드 심층 분석 보고서 써줘"
    │
    ▼  SOCIETY 인텐트 분류
╔═══════════════════════════════════════════╗
║         AgentRegistry (메시지 버스)         ║
║                                           ║
║  ┌─────────────────────────────────────┐  ║
║  │           ManagerAgent              │  ║
║  │                                     │  ║
║  │  "조사는 Researcher에게,            │  ║
║  │   보고서는 Writer에게 위임"          │  ║
║  └────────┬────────────────────────────┘  ║
║           │ AgentMessage(REQUEST)         ║
║           ▼                              ║
║  ┌─────────────────────────────────────┐  ║
║  │         ResearcherAgent             │  ║
║  │                                     │  ║
║  │  1. web_scrape 도구 실행            │  ║
║  │  2. LLM으로 결과 정리              │  ║
║  │  3. return 조사 결과               │  ║
║  └────────┬────────────────────────────┘  ║
║           │ (결과 반환)                   ║
║           ▼                              ║
║  ┌─────────────────────────────────────┐  ║
║  │            WriterAgent              │  ║
║  │                                     │  ║
║  │  1. 조사 결과를 입력으로 받음        │  ║
║  │  2. LLM으로 보고서 작성             │  ║
║  │  3. return 최종 문서               │  ║
║  └────────┬────────────────────────────┘  ║
║           │ (최종 결과)                   ║
╚═══════════╪═══════════════════════════════╝
            ▼
        사용자에게 반환
```

---

### 3-C. 자율 실행 흐름

```
┌─────────────────────────────────────────────────────┐
│               자율 실행 계층                           │
│                                                     │
│  ┌──────────────────────────┐                       │
│  │     scheduler.py         │                       │
│  │                          │  cron 트리거           │
│  │  schedules.yaml 로드     ├──────────────────┐    │
│  │  APScheduler 등록        │                  │    │
│  └──────────────────────────┘                  │    │
│                                                │    │
│  ┌──────────────────────────┐                  │    │
│  │    event_monitor.py      │                  │    │
│  │                          │  파일 이벤트       │    │
│  │  watch_rules.yaml 로드   ├──────────────────┤    │
│  │  watchdog Observer 시작  │                  │    │
│  │  (별도 스레드)            │                  │    │
│  └──────────────────────────┘                  │    │
│                                                │    │
│              asyncio.run_coroutine_threadsafe() │    │
│                              ┌─────────────────▼──┐ │
│                              │  handle_task(text)  │ │
│                              │  → ReAct 루프 실행  │ │
│                              └────────────────────┘ │
└─────────────────────────────────────────────────────┘

예시:
  "0 9 * * 1-5" + "오늘 뉴스 요약해서 news.txt에 저장"
   → 평일 오전 9시 자동 실행

  Agent_Workspace/inbox/*.pdf 파일 생성 감지
   → "{file} 내용 요약해서 summaries/에 저장" 자동 실행
```

---

### 3-D. 보안 샌드박스 계층

```
Python 에이전트                Rust 코어 데몬

파일 읽기 요청
 "read ../../../etc/passwd"
       │
       │  gRPC RequestFileRead
       └──────────────────────▶│
                               │  sandbox.is_path_allowed()
                               │
                               │  canonicalize("../../../etc/passwd")
                               │  → "/etc/passwd"
                               │
                               │  starts_with(Agent_Workspace)?
                               │  → NO
                               │
                               │  return DENIED
                       ◀───────┘
       ×  접근 거부

정상 요청:
 "read Agent_Workspace/data.txt"
       │
       └──────────────────────▶│
                               │  starts_with(Agent_Workspace)?
                               │  → YES
                               │
                               │  safe_read() 실행
                               │  return 파일 내용
                       ◀───────┘
       ✓  파일 내용 반환
```

---

## 4. 계층별 상세 설명

### 4-A. UI 계층

| 컴포넌트 | 파일 | 역할 |
|:---------|:-----|:-----|
| **Tauri 데스크톱 앱** | `desktop/src-tauri/` | 네이티브 OS 창 생성, Python 에이전트를 사이드카 프로세스로 실행, WebView로 Web UI 렌더링 |
| **Web UI** | `web_ui.py` | FastAPI 서버, 브라우저에서 채팅/이미지/음성 입력, 자동화 탭(스케줄·감시 관리) |
| **CLI 대시보드** | `cli.py` | 터미널에서 Rich 라이브러리로 렌더링하는 인터랙티브 채팅 UI |

---

### 4-B. 라우팅 & 인지 계층

#### `router.py` — 의도 분류기 (9개 카테고리)

```
사용자 입력
    │
    ▼ Ollama llama3.2 (temperature=0, 결정적 분류)
    │
    ├── CHAT     → 일반 대화, LLM 직접 응답
    ├── FILE     → 파일 읽기/쓰기 작업
    ├── WEB      → 웹 검색, URL 크롤링
    ├── TASK     → ReAct 루프 (복합 다단계 작업)
    ├── PERSONA  → 에이전트 설정 변경
    ├── VISION   → 이미지 분석 (llava)
    ├── VOICE    → 음성 입력 (STT)
    ├── SCHEDULE → 스케줄 등록/조회/삭제
    └── SOCIETY  → 멀티에이전트 협업 처리
```

#### `react_loop.py` — ReAct 인지 루프

```
TASK 입력
    │
    └─▶  Thought: "파일을 읽어야 한다"
         Action: read_file
         Action Input: {"path": "..."}
         Observation: "파일 내용..."
         Thought: "웹도 검색해야겠다"
         Action: web_scrape
         Action Input: {"url": "..."}
         Observation: "검색 결과..."
         ...
         Final Answer: "종합 결과"
```

---

### 4-C. 기억 & 페르소나 계층

#### `memory.py` — RAG 파이프라인

```
저장:  텍스트 → nomic-embed-text 임베딩 → ChromaDB 저장
검색:  새 쿼리 → 임베딩 → 코사인 유사도 검색 → 상위 5개 기억
주입:  시스템 프롬프트 [관련 기억] 섹션에 삽입
```

#### `persona.py` — 동적 시스템 프롬프트

```yaml
# Agent_Workspace/persona.yaml
name: "Aria"
personality:
  description: "논리적이고 간결한 전문가형 어시스턴트"
  tone: "professional"
  language: "ko"
restrictions:
  absolute_forbidden:
    - "Agent_Workspace 외부 파일 접근 시도"
```

---

### 4-E. 도구 계층 (tools/)

| 도구 | 파일 | 동작 방식 |
|:-----|:-----|:---------|
| **file_reader** | `tools/file_reader.py` | gRPC → Rust 샌드박스 경유 파일 읽기/쓰기 |
| **web_scraper** | `tools/web_scraper.py` | httpx GET → BeautifulSoup 텍스트 추출 (최대 2000자) |
| **vision_tool** | `tools/vision_tool.py` | 이미지 경로/base64 → Ollama llava → 텍스트 설명 |
| **stt_tool** | `tools/stt_tool.py` | sounddevice 마이크 녹음 → faster-whisper STT |
| **tts_tool** | `tools/tts_tool.py` | 텍스트 → pyttsx3 → Windows SAPI 음성 재생 |
| **플러그인** | `plugins/*.py` | `TOOL_NAME` + `run(args)` 규격의 파일을 자동 로드 |

---

### 4-F. 자율 실행 계층 (Phase 7)

#### `scheduler.py`

- APScheduler `AsyncIOScheduler` → FastAPI lifespan에 연결
- cron 규칙 (`0 9 * * 1-5`) → 정해진 시각에 `handle_task()` 자동 호출
- 규칙은 `Agent_Workspace/schedules.yaml`에 영구 저장 (서버 재시작 후 복원)

#### `event_monitor.py`

- watchdog `Observer`가 지정 경로를 별도 스레드로 감시
- 파일 이벤트(생성/수정/삭제) 감지 → `asyncio.run_coroutine_threadsafe()`로 이벤트 루프에 태스크 전달
- 규칙은 `Agent_Workspace/watch_rules.yaml`에 영구 저장

---

### 4-G. 멀티에이전트 계층 (Phase 8)

| 에이전트 | 파일 | 역할 |
|:---------|:-----|:-----|
| **ManagerAgent** | `agents/manager.py` | 요청 분석 → DELEGATE/ANSWER 결정 → Researcher 또는 Writer에게 위임 |
| **ResearcherAgent** | `agents/researcher.py` | web_scrape/read_file 도구 실제 호출 → 팩트 기반 조사 결과 반환 |
| **WriterAgent** | `agents/writer.py` | 수집된 정보를 논리적 구조의 문서로 작성 |
| **AgentRegistry** | `registry.py` | 에이전트 등록소 + 동기식 메시지 버스 (dispatch) |
| **AgentMessage** | `actor.py` | 에이전트 간 메시지 규격 (sender/recipient/content/type) |

---

### 4-H. Rust 코어 데몬 (rust_core/)

| 모듈 | 파일 | 역할 |
|:-----|:-----|:-----|
| **진입점** | `main.rs` | CLI 인자 파싱, tokio 런타임 시작, gRPC 서버 바인딩 |
| **gRPC 서버** | `server.rs` | `AgentBroker` 서비스 구현: 파일 읽기/쓰기, 명령 실행, 채팅 스트림 |
| **샌드박스** | `sandbox.rs` | `dunce::canonicalize()`로 경로 정규화 → `starts_with(Agent_Workspace)` 검증 |

**보안 게이트웨이 원칙:** Python은 절대 직접 파일시스템에 접근하지 않는다. 모든 I/O는 Rust를 경유한다.

---

## 5. 데이터 흐름 지도

### 5-A. 일반 채팅 흐름

```
[브라우저] → WebSocket /ws
    → web_ui.py: classify_intent()
        → router.py: llama3.2로 분류 → "CHAT"
    → handle_chat(user_input)
        → persona.py: build_system_prompt()
            → memory.py: recall() → 관련 기억 5개
            → persona.yaml: 페르소나 설정
        → ollama.chat(llama3.2)
        → memory.save(대화 내용)
    → WebSocket 응답
[브라우저] ← 에이전트 답변
```

### 5-B. 이미지 분석 흐름

```
[브라우저] → 🖼 버튼 클릭 또는 Ctrl+V
    → FileReader API → base64 변환
    → POST /api/vision { base64_image, prompt }
    → handle_vision()
        → vision_tool.analyze_image_tool()
            → ollama.chat(llava, images=[base64])
        → memory.save(분석 결과 요약)
    → JSON 응답
[브라우저] ← 이미지 분석 텍스트
```

### 5-C. 음성 입력 흐름

```
[브라우저] → 🎤 버튼 클릭
    → MediaRecorder API (audio/webm)
    → POST /api/voice/upload (FormData)
    → tempfile 저장
    → stt_tool.transcribe_file_tool()
        → faster-whisper (로컬 Whisper 모델)
        → 텍스트 변환
    → handle_chat(transcribed_text)
    → (옵션) tts_tool.speak_async() → 서버 측 TTS 재생
    → JSON { response, transcribed }
[브라우저] ← 텍스트 답변 + 음성 재생
```

### 5-D. 자율 실행 흐름

```
[시간 도달] APScheduler 트리거
    → asyncio 이벤트 루프
        → run_in_executor(handle_task, "뉴스 요약해줘")
            → react_loop.ReActAgent.run()
                → Thought: 웹 검색 필요
                → web_scraper.web_scrape_tool()
                → Thought: 파일 저장 필요
                → file_reader.write_file_tool() → gRPC → Rust → 파일 쓰기
                → Final Answer: 완료

[파일 생성] watchdog 감지 (별도 스레드)
    → asyncio.run_coroutine_threadsafe()
        → 위와 동일한 ReAct 파이프라인
```

### 5-E. 파일 접근 보안 흐름

```
Python tools/file_reader.py
    → grpc_client.py: channel = grpc.insecure_channel("localhost:50051")
    → stub.RequestFileRead(FileRequest(path=path))
        [gRPC 전송]
    → rust_core/server.rs: request_file_read()
        → sandbox.is_path_allowed(path)
            → dunce::canonicalize(path)
            → path.starts_with(Agent_Workspace)?
                YES → safe_read() → FileResponse { content, allowed: true }
                NO  → FileResponse { allowed: false, error: "DENIED" }
    → Python: response.content 또는 에러 처리
```

---

## 6. Phase별 개발 타임라인

```
Phase 1  ████████████████  gRPC 통신 기반 + Rust 샌드박스
              ↓
Phase 2  ████████████████  Router + ReAct 루프 + 기초 도구 2종
              ↓
Phase 3  ████████████████  ChromaDB RAG + persona.yaml 페르소나
              ↓
Phase 4  ████████████████  플러그인 동적 로더 + CLI 대시보드
              ↓
Phase 5  ████████████████  Tauri 데스크톱 앱 + Web UI (FastAPI)
              ↓
Phase 6A ████████████████  Vision: llava 이미지 분석
              ↓
Phase 6B ████████████████  Voice: faster-whisper STT + pyttsx3 TTS
              ↓
Phase 7A ████████████████  Scheduler: APScheduler cron 자율 실행
              ↓
Phase 7B ████████████████  Event Monitor: watchdog 파일 감시
              ↓
Phase 8  ████████████████  Multi-Agent Society: Manager/Researcher/Writer
```

| Phase | 핵심 기능 | 주요 신규 파일 |
|:------|:---------|:-------------|
| **1** | Rust gRPC 서버, Python 클라이언트, 파일 샌드박스 | `rust_core/`, `proto/`, `grpc_client.py` |
| **2** | 의도 분류기, ReAct 루프, 파일/웹 도구 | `router.py`, `react_loop.py`, `tools/` |
| **3** | 장기 기억 (RAG), 동적 시스템 프롬프트 | `memory.py`, `persona.py`, `persona.yaml` |
| **4** | 플러그인 생태계, CLI 대시보드 | `plugin_loader.py`, `cli.py` |
| **5** | 데스크톱 앱, 웹 UI | `desktop/`, `web_ui.py` |
| **6-A** | 이미지 이해 (Vision) | `tools/vision_tool.py` |
| **6-B** | 음성 입출력 (STT/TTS) | `tools/stt_tool.py`, `tools/tts_tool.py` |
| **7-A** | 시간 기반 자율 실행 | `scheduler.py`, `schedules.yaml` |
| **7-B** | 이벤트 기반 자율 실행 | `event_monitor.py`, `watch_rules.yaml` |
| **8** | 멀티에이전트 협업 | `actor.py`, `registry.py`, `agents/` |

---

## 7. 기술 스택 요약

### Python (마이크로서비스 레이어)

| 영역 | 라이브러리 | 버전 | 용도 |
|:-----|:----------|:-----|:-----|
| **LLM** | ollama | ≥0.6 | 로컬 LLM API 클라이언트 |
| **웹 서버** | fastapi + uvicorn | ≥0.129 | REST API + WebSocket 서버 |
| **gRPC** | grpcio + grpcio-tools | ≥1.65 | Rust 코어 데몬 통신 |
| **벡터 DB** | chromadb | ≥0.6 | 장기 기억 벡터 인덱스 |
| **STT** | faster-whisper | ≥1.1 | 로컬 Whisper 음성 인식 |
| **TTS** | pyttsx3 | ≥2.98 | 로컬 텍스트-음성 변환 |
| **오디오** | sounddevice | ≥0.5 | 마이크 스트림 캡처 |
| **스케줄러** | apscheduler | ≥3.10 | cron 기반 자율 실행 |
| **파일 감시** | watchdog | ≥4.0 | 파일시스템 이벤트 감지 |
| **HTTP** | httpx | ≥0.28 | 웹 크롤링 HTTP 클라이언트 |
| **파싱** | beautifulsoup4 | ≥4.12 | HTML 텍스트 추출 |
| **설정** | pyyaml | ≥6.0 | YAML 파일 읽기/쓰기 |
| **UI** | rich + prompt-toolkit | — | 터미널 CLI 대시보드 |
| **패키지** | uv | — | 빠른 Python 패키지 매니저 |

### Rust (코어 데몬)

| 라이브러리 | 버전 | 용도 |
|:----------|:-----|:-----|
| tonic | 0.12 | gRPC 서버 프레임워크 |
| prost | 0.13 | Protocol Buffer 직렬화 |
| tokio | 1 (full) | 비동기 런타임 |
| dunce | 1 | Windows UNC 경로 정규화 |
| tracing | 0.1 | 구조화 로깅 |

### 로컬 AI 모델 (Ollama)

| 모델 | 용도 |
|:-----|:-----|
| `llama3.2` | 채팅, 의도 분류, ReAct, 멀티에이전트 |
| `llava` | 이미지 분석 (멀티모달) |
| `nomic-embed-text` | 텍스트 임베딩 (RAG) |

---

## 8. 핵심 설계 원칙

### 원칙 1. 완전 로컬 (Privacy First)

> 모든 AI 처리는 내 PC 위의 Ollama에서 수행됩니다.
> 사용자의 대화, 파일, 기억이 외부 서버로 전송되지 않습니다.

### 원칙 2. 권한 분리 (Least Privilege)

> Python은 파일시스템에 직접 접근하지 않습니다.
> 모든 I/O는 반드시 **Rust 코어 데몬의 gRPC 게이트**를 경유합니다.
> `Agent_Workspace` 외부 접근 시도는 즉시 DENIED됩니다.

### 원칙 3. 영속성 (Persistence)

> 스케줄 규칙, 감시 규칙, 기억은 모두 파일 또는 DB에 영구 저장됩니다.
> 서버가 재시작되어도 모든 설정이 자동 복원됩니다.

### 원칙 4. 확장성 (Extensibility)

> `Agent_Workspace/plugins/` 폴더에 `.py` 파일을 추가하기만 하면
> 재시작 없이 새 도구가 ReAct 루프에 자동 등록됩니다.

### 원칙 5. 자율성 (Autonomy)

> 사용자가 먼저 말하지 않아도 됩니다.
> 정해진 시각이 되거나 파일이 생기면 에이전트가 **먼저** 행동합니다.

### 원칙 6. 협업 (Society)

> 단일 LLM이 모든 것을 처리하는 대신,
> 역할이 분화된 에이전트들이 메시지를 주고받으며 협력합니다.

---

## 발표 핵심 메시지

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   Ageis는 단순한 챗봇이 아닙니다.                         │
│                                                         │
│   • 이미지를 보고   (llava Vision)                       │
│   • 음성을 듣고    (faster-whisper STT)                  │
│   • 기억을 가지며  (ChromaDB RAG)                        │
│   • 스스로 일하고  (APScheduler + watchdog)              │
│   • 팀으로 협력하는 (Multi-Agent Society)                │
│                                                         │
│   완전히 내 PC 위에서 동작하는 개인용 AI 에이전트입니다.    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```
