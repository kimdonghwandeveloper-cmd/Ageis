# Ageis Future Roadmap 학습 가이드 (Learning Guide)

> **작성일:** 2026-02-18
> **목적:** Ageis의 Phase 5 (Tauri), Phase 6 (Total AI), Phase 7/8 (Automation & Multi-Agent) 개발을 위해 필요한 핵심 지식과 학습 키워드를 정리합니다.

---

## 🏗️ Phase 5: The Face (Tauri 데스크톱 앱 통합)

이 단계에서는 **Rust(Backend)** 와 **Web Frontend(React/Svelte)**, 그리고 **Python(Sidecar)** 세 가지가 유기적으로 통신해야 합니다.

### 1. Tauri & Rust 핵심 (필수)
*   **Sidecar Pattern:** Tauri 앱이 실행될 때 외부 바이너리(여기선 Python 에이전트)를 함께 실행하고 관리하는 방법.
    *   *검색 키워드:* `tauri sidecar python`, `tauri command lifecycle`
*   **IPC (Inter-Process Communication):** Rust 프로세스와 WebView(프론트엔드) 간의 메시지 교환.
    *   *검색 키워드:* `tauri events`, `tauri invoke command`
*   **Tokio (Async Rust):** 비동기 런타임에 대한 이해. Tauri는 Tokio 위에서 돌아가므로, 비동기 작업 처리에 필수입니다.

### 2. Frontend (선택 - 동료가 담당하겠지만 알면 좋음)
*   **WebSocket Client:** Python 에이전트(`ws://localhost:8000`)와 통신하기 위한 JS 라이브러리.
    *   *검색 키워드:* `reconnecting-websocket`, `react useWebSocket`

---

## 👁️ Phase 6: The Senses (멀티모달 확장)

텍스트 모델(LLM)을 넘어, **Vision(시각)** 과 **Audio(청각)** 데이터를 처리하는 파이프라인 지식이 필요합니다.

### 1. Vision AI (Llava/Vision Models)
*   **Multimodal LLM:** 이미지를 텍스트 프롬프트와 함께 입력받는 모델의 구조 이해.
*   **Image Preprocessing:** 이미지를 모델에 넣기 전에 리사이징하거나 인코딩(Base64)하는 방법.
    *   *라이브러리:* `Pillow` (Python 이미지 처리 표준)
    *   *검색 키워드:* `ollama llava usage`, `python screenshot capture`

### 2. Audio AI (STT/TTS)
*   **STT (Speech-to-Text):** 음성 데이터를 텍스트로 변환. `Whisper` 모델이 표준입니다.
*   **TTS (Text-to-Speech):** 텍스트를 음성으로 변환. 로컬에서는 `Piper`, `Coqui TTS` 등이 유명합니다.
*   **Audio Stream Handling:** 마이크 입력을 실시간으로 청크(Chunk) 단위로 쪼개서 서버로 전송하는 기술.
    *   *라이브러리:* `PyAudio`, `sounddevice`

---

## 🦵 Phase 7: The Legs (자율성 및 자동화)

에이전트가 "스스로" 움직이려면 **이벤트 루프**와 **스케줄링**, **OS 시스템 콜**에 대한 깊은 이해가 필요합니다.

### 1. Advanced Python Scheduling
*   **Job Queue & Scheduling:** 단순 `sleep`이 아니라, 크론탭(Cron)처럼 정확한 시간에 작업을 실행하고, 실패 시 재시도하는 로직.
    *   *라이브러리:* `APScheduler` (강력 추천), `Celery` (너무 무거움, 참고만)
 
### 2. OS System Integration
*   **File System Monitoring:** 폴더에 파일이 생기거나 변경되는 이벤트를 감지.
    *   *라이브러리:* `watchdog`
*   **System Events:** USB 연결, 네트워크 변경, 절전 모드 진입/해제 등 OS 이벤트 훅(Hook).
    *   *윈도우:* `pywin32` (WinAPI 접근)

---

## 🧠 Phase 8: The Society (멀티 에이전트 시스템)

하나의 거대 모델이 아니라, **작고 전문적인 여러 에이전트**가 협력하는 구조(Orchestration)를 설계해야 합니다.

### 1. Agent Architecture Patterns
*   **Actor Model:** 각 에이전트를 독립적인 '배우'로 보고, 서로 메시지를 주고받는 동시성 모델.
*   **Orchestration vs Choreography:** 중앙 관리자(Manager)가 지시할지, 에이전트끼리 자율적으로 협업할지 설계.
    *   *프레임워크 참고:* `LangGraph` (상태 기반), `CrewAI` (역할 기반), `AutoGen` (대화 기반) — 직접 쓰지 않더라도 구조를 공부하면 좋습니다.

### 2. Prompt Engineering for Collaboration
*   **Role-Playing Prompts:** "너는 깐깐한 코드 리뷰어(Coder)야", "너는 친절한 매니저(Manager)야" 처럼 역할을 명확히 부여하고, 출력 형식을 통일시키는 프롬프트 기술.

---

## 📚 추천 학습 순서

1.  **Phase 5 대비:** [Rust] `Tauri` 공식 문서 정독 (특히 Sidecar 섹션)
2.  **Phase 6 대비:** [Python] `Pillow`로 스크린샷 찍어서 `Ollama Llava`에 던져보는 스크립트 작성해보기 (가장 재미있고 시각적임!)
3.  **Phase 7 대비:** [Python] `APScheduler`로 "1분마다 현재 시간 출력"하는 간단한 데몬 만들어보기.

준비되셨나요? 차근차근 하나씩 정복해봅시다! 🚀
