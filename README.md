# Ageis Agent 🛡️

> **"보고, 듣고, 기억하고, 스스로 움직이는 완전 로컬 AI 에이전트"**

Ageis는 Ollama 로컬 LLM을 두뇌로 삼아, 텍스트·이미지·음성을 이해하고, 파일·웹·코드를 다루며, 스스로 일정을 잡고 파일 변화에 반응하는 **완전 오프라인 AI 에이전트**입니다.

---

## 🌟 주요 특징

| 특징 | 설명 |
|:---:|:---|
| **🔒 완전 로컬** | 외부 클라우드 API 없이 내 PC 위에서 100% 동작 (Privacy First) |
| **🧠 멀티모달** | 텍스트(Llama 3.2), 이미지(Llava), 음성(Whisper/TTS) 처리 가능 |
| **🤝 멀티에이전트** | Manager, Researcher, Writer 등 전문 에이전트 간의 협업 (Phase 8) |
| **⏰ 자율 실행** | cron 스케줄링 및 파일 시스템 이벤트 감지로 스스로 작업 수행 |
| **💾 장기 기억** | ChromaDB RAG를 통해 대화 내용을 영구적으로 기억하고 활용 |
| **🛡️ 보안 샌드박스** | Rust 코어 데몬이 파일 시스템 접근을 엄격하게 통제 |
| **💻 크로스 플랫폼** | Python 백엔드 + Tauri 데스크톱 앱 (Windows/Mac/Linux) |

---

## 🏗️ 시스템 아키텍처

### 전체 구조

```mermaid
graph TD
    User[사용자] --> UI[UI 계층]
    
    subgraph "UI Layer"
        Desktop[Tauri Desktop App]
        Web[Web UI (FastAPI)]
        CLI[CLI Dashboard]
    end
    
    UI --> Core[Python Agent Core]
    
    subgraph "Python Agent (Brain)"
        Core --> Router[의도 분류기]
        Router --> Society[Multi-Agent Society]
        Router --> Task[ReAct Loop]
        Router --> Vision[Vision Handler]
        Router --> Voice[Voice Handler]
        
        Society --> Manager[Manager Agent]
        Manager --> Researcher[Researcher Agent]
        Manager --> Writer[Writer Agent]
        
        Task --> Tools[도구 모음]
        Vision --> Tools
        
        Memory[ChromaDB Memory] <--> Core
        Persona[Persona System] --> Core
        
        Scheduler[APScheduler] --> Core
        Monitor[Event Monitor] --> Core
    end
    
    Core --> gRPC[gRPC Client]
    
    subgraph "Rust Core (Body & Security)"
        gRPC --> Server[gRPC Server]
        Server --> Sandbox[Sandbox Gate]
        Sandbox --> FS[File System]
    end
    
    subgraph "Local AI Models"
        Core --> Ollama[Ollama Server]
        Ollama --> Llama[Llama 3.2]
        Ollama --> Llava[Llava]
        Ollama --> Embed[Nomic-Embed]
    end
```

### 멀티에이전트 협업 구조 (The Society)

```
[User] -> "최신 AI 트렌드 리포트 써줘"
   │
   ▼
[Manager Agent] (기획/조정)
   │ "조사는 Researcher에게, 집필은 Writer에게"
   ├─────────────────────────────┐
   ▼                             ▼
[Researcher Agent]          [Writer Agent]
(정보 수집)                   (보고서 작성)
   │ 위키/뉴스 검색                │
   │ 파일 읽기                    │ 조사 결과 바탕 작성
   └───────────┬─────────────────┘
               ▼
        [Final Report] -> [User]
```

---

## 📂 프로젝트 구조

```
Ageis/
├── rust_core/              # Rust 보안 데몬 (gRPC 서버)
│   ├── src/server.rs       # AgentBroker 서비스 구현
│   └── src/sandbox.rs      # 경로 접근 통제 로직
│
├── python_agent/           # Python 에이전트 (두뇌)
│   ├── main.py             # 메인 진입점
│   ├── core_logic.py       # 핵심 로직 허브
│   ├── router.py           # 사용자 의도 분류기
│   ├── actor.py            # Actor Model 기반 클래스
│   ├── registry.py         # 에이전트 레지스트리
│   ├── agents/             # 전문 에이전트 (Manager, Researcher, Writer)
│   ├── tools/              # 기능 도구 (File, Web, Vision, STT/TTS)
│   └── ...
│
├── desktop/                # Tauri 데스크톱 앱
│   ├── src-tauri/          # Rust 백엔드 (사이드카 관리)
│   └── src/                # 만료된 프론트엔드 (현재는 Web UI 사용)
│
├── proto/                  # gRPC 프로토콜 정의 (agent.proto)
└── Agent_Workspace/        # 샌드박스 작업 공간 (파일 생성/수정 허용)
    ├── plugins/            # 사용자 정의 플러그인
    ├── persona.yaml        # 에이전트 성격 설정
    └── ...
```

---

## 🚀 시작하기

### 필수 사항
- **Rust Toolchain**: `rustup` 설치 필요
- **Python**: 3.10+ (`uv` 패키지 매니저 권장)
- **Ollama**: 로컬 실행 및 모델(`llama3.2`, `llava`, `nomic-embed-text`) pull 필요
- **Node.js**: Tauri 앱 빌드용

### 설치 및 실행

1. **Rust Core 빌드**
   ```bash
   cd rust_core
   cargo build --release
   ```

2. **Python 환경 설정**
   ```bash
   cd python_agent
   uv sync
   ```

3. **실행 (CLI 모드)**
   ```bash
   uv run main.py
   # 또는
   uv run main.py --cli
   ```

4. **실행 (Desktop App)**
   ```bash
   cd desktop/src-tauri
   npm install
   npm run tauri dev
   ```

---

## 🛠️ 기술 스택

- **Core**: Rust (Tonic, Tokio), Python (FastAPI, gRPC)
- **AI**: Ollama, Llama 3.2, Llava, Faster-Whisper
- **Data**: ChromaDB (Vector Store), SQLite (Metadata)
- **Desktop**: Tauri (Rust + Web Tech)
- **Tools**: BeautifulSoup4, APScheduler, Watchdog, SoundDevice

---

## 📝 라이선스

MIT License
