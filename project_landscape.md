# Ageis Project Landscape & Future Roadmap

> **작성일:** 2026-02-18
> **상태:** Phase 4 완료 (CLI/Web UI 구축됨)
> **대상:** Ageis 개발팀 및 미래 확장을 위한 설계 문서

---

## 1. 현재 프로젝트 구조 (As-Is)

현재 Ageis는 **Rust(Backend Security)** 와 **Python(AI Logic)** 이 결합된 하이브리드 구조입니다.

```mermaid
graph TD
    subgraph "Interface Layer"
        CLI[Terminal CLI<br/>(Rich)]
        Web[Web UI<br/>(FastAPI/WebSocket)]
    end

    subgraph "Brain Layer (Python)"
        Core[Core Logic]
        ReAct[ReAct Loop<br/>(Thought/Action)]
        Router[Intent Router]
        Memory[Memory (ChromaDB)]
        Plugins[Plugin System]
    end

    subgraph "Body Layer (Rust)"
        Daemon[Ageis Core Daemon<br/>(gRPC Server)]
        Sandbox[Security Sandbox]
    end

    subgraph "Data & External"
        FS[Agent_Workspace]
        Ollama[Ollama LLM]
    end

    CLI --> Core
    Web --> Core
    Core --> Router
    Core --> ReAct
    ReAct --> Memory
    ReAct --> Plugins
    ReAct --> Daemon
    Daemon --> Sandbox
    Sandbox --> FS
    Core -.-> Ollama
```

### 핵심 포인트
1.  **코어 로직 분리:** UI(`cli.py`, `web_ui.py`)와 비즈니스 로직(`core_logic.py`, `react_loop.py`)이 분리되어 있어, 새로운 인터페이스(예: Tauri, Mobile)를 붙이기 쉽습니다.
2.  **보안 샌드박스:** 모든 물리적 파일 시스템 접근은 Rust 데몬을 통제받습니다.
3.  **플러그인 확장:** 파이썬 코드로 기능을 실시간으로 추가할 수 있습니다.

---

## 2. 미래 확장 방향: Tauri 데스크톱 앱 (To-Be)

동료가 진행 중인 **Rust Tauri** 프로젝트는 Ageis의 **새로운 얼굴(Native UI)** 이 될 수 있습니다.

### 통합 아키텍처 제안

```mermaid
graph LR
    subgraph "Tauri App (New Face)"
        WebView[Update UI<br/>(Frontend: React/Svelte)]
        TauriRust[Tauri Rust Process<br/>(Backend/System Tray)]
    end

    subgraph "Ageis Python Agent (The Brain)"
        PyAgent[Python Websocket Server]
    end

    subgraph "Ageis Rust Core (The Body)"
        CoreDaemon[Existing Rust Core]
    end

    WebView <-->|Command/Event| TauriRust
    TauriRust <-->|WebSocket/HTTP| PyAgent
    PyAgent <-->|gRPC| CoreDaemon
```

### 구현 전략
1.  **Headless Integration:**
    -   Tauri 앱 실행 시 백그라운드에서 `python_agent`를 서브 프로세스로 실행합니다 (`Sidecar` 패턴).
    -   Tauri 앱은 현재의 `web_ui.py`와 유사하게 **WebSocket 클라이언트** 역할을 수행하여 Python 에이전트와 통신합니다.
2.  **Native Capabilities:**
    -   Tauri는 단순 챗봇 UI를 넘어, 시스템 트레이, 알림, 글로벌 단축키 등을 제공하여 OS와 더 긴밀히 통합될 수 있습니다.

---

## 3. 발전 방향 제안 (Future Roadmap)

Ageis가 단순한 "로컬 챗봇"을 넘어 **"운영체제 레벨의 AI 파트너"** 가 되기 위한 3가지 길을 제안합니다.

### 길 1: 멀티 모달 센서 (The Senses) — Phase 5
텍스트를 넘어 보고 듣는 능력을 부여합니다.
-   **Vision:** 스크린샷 캡처 또는 이미지를 입력받아 `Llava` 모델(Ollama)로 분석. (예: "내 화면에 있는 에러 로그 좀 봐줘")
-   **Voice:** 사용자의 음성을 `Whisper`로 STT 변환, 에이전트의 답변을 TTS로 출력.
-   **구현:** Python `plugins`에 `vision_tool.py`, `voice_io.py` 추가.

### 길 2: 자율성 강화 (The Legs) — Phase 6
사용자가 시키지 않아도 스스로 움직이는 에이전트입니다.
-   **Scheduler:** "매일 아침 9시에 뉴스 요약해줘" 같은 반복 작업 수행 (`APScheduler` 활용).
-   **Event Monitor:** 특정 파일 변경이나 시스템 이벤트(USB 연결 등)를 감지하여 반응.
-   **Long-running Task:** 에이전트가 백그라운드에서 데이터를 수집하고 분석 리포트를 작성.

### 길 3: 멀티 에이전트 협업 (The Team) — Phase 7
하나의 슈퍼 에이전트 대신, 전문화된 여러 에이전트가 협력합니다.
-   **Coder Agent:** 코드 작성 및 분석 전문.
-   **Writer Agent:** 문서 작성 및 요약 전문.
-   **Manager Agent:** 사용자 입력을 받아 적절한 전문가에게 위임.
-   **구현:** 현재의 `Router`를 고도화하고, 별도의 `Persona`를 가진 프로세스들을 오케스트레이션.

---

## 4. 즉시 실행 가능한 다음 단계 (Action Items)

1.  **Tauri 연동 PoC (Proof of Concept):**
    -   동료분께 현재의 `python main.py --web` (WebSocket 서버)에 Tauri 앱이 클라이언트로 접속해보라고 제안하세요.
    -   Tauri의 Rust 백엔드에서 `tokio-tungstenite` 등을 사용해 통신하면 됩니다.

2.  **멀티 모달 플러그인 실험:**
    -   `pyautogui`로 화면 캡처 기능을 플러그인으로 만들어보세요. 에이전트가 "내 화면을 볼 수 있게" 됩니다.

이 지도가 Ageis의 미래를 설계하는 데 도움이 되길 바랍니다! 🗺️🚀
