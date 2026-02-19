# Phase 6 & 7 구현 계획

> **작성일:** 2026-02-18
> **담당:** Claude (AI 페어 프로그래머)
> **전제:** Phase 1~4 완료, Phase 5 (Tauri 통합) 동료 진행 중

---

## 현재 베이스 파악

Phase 1~4 구현 완료 상태:
- `web_ui.py` — FastAPI + WebSocket (텍스트 전용)
- `router.py` — CHAT / FILE / WEB / TASK / PERSONA 5개 인텐트
- `tools/` — file_reader, web_scraper
- gRPC, RAG 메모리, 페르소나 시스템 완비

---

## Phase 6: The Senses (멀티모달 확장)

### 6-A. Vision (이미지 분석)

**전략:**
- 현재 WebSocket은 텍스트 전용 → 이미지용 `POST /api/vision` REST 엔드포인트 별도 추가
- `ollama` 클라이언트로 `llava` 모델 호출 (기존 클라이언트 재사용)
- `router.py`에 `VISION` 인텐트 추가

**작업 목록:**
- [ ] `tools/vision_tool.py` 생성 (이미지 경로/base64 → llava 호출 → 텍스트 반환)
- [ ] `web_ui.py`에 `POST /api/vision` 엔드포인트 추가
- [ ] `router.py` CLASSIFIER_PROMPT에 VISION 카테고리 추가
- [ ] Web UI HTML에 이미지 업로드 버튼 / 클립보드 붙여넣기 지원 추가
- [ ] `core_logic.py`에 `handle_vision()` 함수 추가

**추가 의존성:**
```bash
# 없음 — ollama 클라이언트가 llava를 지원
# Ollama에서 모델만 pull 필요
ollama pull llava
```

---

### 6-B. Voice — STT/TTS

**전략:**
- STT: `faster-whisper` (로컬, CUDA/CPU 모두 지원, pyaudio보다 안정적)
- 오디오 캡처: `sounddevice` (Windows에서 pyaudio보다 안정적)
- TTS: `pyttsx3` (Windows SAPI 직접 사용, 가장 간단)
- WebSocket에 오디오 스트림 바이너리 채널 추가

**작업 목록:**
- [ ] `tools/stt_tool.py` 생성 (sounddevice로 녹음 → faster-whisper로 변환)
- [ ] `tools/tts_tool.py` 생성 (pyttsx3으로 텍스트 → 음성 재생)
- [ ] `web_ui.py`에 마이크 버튼 및 오디오 WebSocket 채널 추가
- [ ] Web UI HTML에 마이크 버튼 UI 추가 (MediaRecorder API)
- [ ] `router.py`에 VOICE 인텐트 추가

**추가 의존성:**
```bash
uv add faster-whisper sounddevice pyttsx3
# faster-whisper 모델: base로 시작 (속도 vs 정확도 균형)
```

---

### 6-C. Wake Word (별도 서브태스크, 마지막 구현)

**전략:**
- `openwakeword` (오픈소스, 로컬) 사용
- 백그라운드 스레드에서 상시 마이크 모니터링
- Wake word 감지 시 → STT 파이프라인 트리거

**작업 목록:**
- [ ] `tools/wake_word.py` 생성
- [ ] 백그라운드 스레드 관리 (`threading.Thread`)
- [ ] Tauri 트레이 연동 (Phase 5 완료 후 진행)

**추가 의존성:**
```bash
uv add openwakeword
```

> ⚠️ 복잡도 높음 — Phase 6-A, 6-B 완료 후 착수

---

## Phase 7: The Legs (자율성 및 스케줄링)

### 7-A. Scheduler (시간 기반 자율 실행)

**전략:**
- `APScheduler`의 `AsyncIOScheduler`를 FastAPI lifespan 이벤트에 연결
- 스케줄 규칙은 `Agent_Workspace/schedules.yaml`에 저장 (페르소나 패턴과 일관성)
- 스케줄 실행 시 기존 `handle_task()` 파이프라인 재사용

**작업 목록:**
- [ ] `scheduler.py` 생성 (AsyncIOScheduler 관리, YAML 규칙 로드/저장)
- [ ] `web_ui.py` lifespan에 스케줄러 시작/종료 연결
- [ ] `POST /api/schedule` — 스케줄 등록 엔드포인트
- [ ] `GET /api/schedules` — 스케줄 목록 조회
- [ ] `DELETE /api/schedule/{id}` — 스케줄 삭제
- [ ] `router.py`에 SCHEDULE 인텐트 추가
- [ ] 자연어 → 크론 표현식 변환 로직 (LLM 활용)

**스케줄 규칙 포맷 (`Agent_Workspace/schedules.yaml`):**
```yaml
schedules:
  - id: "uuid-1"
    cron: "0 9 * * 1-5"       # 평일 오전 9시
    task: "주식 시장 요약해줘"
    enabled: true
    created_at: "2026-02-18"
```

**추가 의존성:**
```bash
uv add apscheduler pyyaml
# pyyaml은 Phase 3에서 이미 추가됨
```

---

### 7-B. Event Monitor (이벤트 기반 자율 실행)

**전략:**
- `watchdog`으로 파일시스템 이벤트 감시
- `watchdog`은 자체 스레드 → `asyncio.run_coroutine_threadsafe()`로 이벤트 루프 브릿지
- 감시 규칙은 `Agent_Workspace/watch_rules.yaml`에 저장

**작업 목록:**
- [ ] `event_monitor.py` 생성 (watchdog Handler + asyncio 브릿지)
- [ ] `web_ui.py` lifespan에 감시 시작/종료 연결
- [ ] `POST /api/watch` — 감시 규칙 등록 엔드포인트
- [ ] `GET /api/watches` — 감시 규칙 목록 조회
- [ ] `DELETE /api/watch/{id}` — 감시 규칙 삭제
- [ ] 이벤트 발생 시 → `handle_task()` 자동 트리거

**감시 규칙 포맷 (`Agent_Workspace/watch_rules.yaml`):**
```yaml
watches:
  - id: "uuid-1"
    path: "Agent_Workspace/downloads"
    pattern: "*.pdf"
    event: "created"           # created / modified / deleted
    task: "이 파일 요약해서 Agent_Workspace/summaries/ 에 저장해줘"
    enabled: true
```

**추가 의존성:**
```bash
uv add watchdog
```

---

## 구현 순서

```
Phase 6-A: Vision          ← 가장 쉬움, ollama 재사용
    ↓
Phase 6-B: Voice STT/TTS   ← sounddevice + faster-whisper + pyttsx3
    ↓
Phase 7-A: Scheduler       ← APScheduler + FastAPI lifespan
    ↓
Phase 7-B: Event Monitor   ← watchdog + asyncio 브릿지
    ↓
Phase 6-C: Wake Word       ← 복잡도 높음, 마지막
```

---

## 주요 우려사항 및 대응

| 항목 | 위험도 | 내용 | 대응 |
|------|:------:|------|------|
| WebSocket 바이너리 처리 | 중 | 현재 텍스트 전용 | 이미지용 REST 엔드포인트 분리 |
| Windows 오디오 | 높 | pyaudio 빌드 이슈 | sounddevice 사용 필수 |
| Scheduler + asyncio | 중 | 이벤트 루프 충돌 가능 | AsyncIOScheduler + lifespan 패턴 |
| watchdog 스레드 → asyncio | 중 | 스레드 경계 문제 | run_coroutine_threadsafe 브릿지 |
| faster-whisper 모델 크기 | 낮 | 대형 모델은 느림 | base 모델로 시작 |

---

## 파일 구조 (Phase 6~7 완료 후 예상)

```
python_agent/
├── tools/
│   ├── file_reader.py     (기존)
│   ├── web_scraper.py     (기존)
│   ├── vision_tool.py     ← Phase 6-A
│   ├── stt_tool.py        ← Phase 6-B
│   ├── tts_tool.py        ← Phase 6-B
│   └── wake_word.py       ← Phase 6-C
├── scheduler.py           ← Phase 7-A
├── event_monitor.py       ← Phase 7-B
├── router.py              (VISION, VOICE, SCHEDULE 인텐트 추가)
├── web_ui.py              (엔드포인트 및 lifespan 확장)
└── core_logic.py          (handle_vision 추가)

Agent_Workspace/
├── schedules.yaml         ← Phase 7-A
└── watch_rules.yaml       ← Phase 7-B
```
