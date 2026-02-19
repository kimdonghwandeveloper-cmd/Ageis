# Phase 7 완료 보고서 — The Legs (자율성 & 스케줄링)

> **작성일:** 2026-02-19
> **완료 Phase:** Phase 7-A (Scheduler), Phase 7-B (Event Monitor)
> **미구현:** Phase 6-C (Wake Word) — 여전히 복잡도 높음, 향후 착수 권장

---

## 1. 개요 및 성과

텍스트/음성/이미지를 받아 반응하던 Ageis Agent에 **자율적으로 판단하고 먼저 행동하는 다리**를 달았습니다.

- **7-A Scheduler:** 사용자가 등록한 cron 표현식에 따라 특정 시각에 태스크를 자동 실행합니다.
  예) "평일 오전 9시에 뉴스 요약해서 파일에 저장해줘"
- **7-B Event Monitor:** 지정한 폴더를 watchdog으로 감시하다 파일 이벤트(생성/수정/삭제) 발생 시 태스크를 자동 트리거합니다.
  예) "downloads/ 에 PDF가 생기면 자동으로 요약해서 summaries/ 에 저장해줘"

---

## 2. 신규 파일 목록

| 파일 | Phase | 설명 |
|------|:-----:|------|
| `python_agent/scheduler.py` | 7-A | APScheduler AsyncIOScheduler 래퍼. YAML 영속성, CRUD API |
| `python_agent/event_monitor.py` | 7-B | watchdog Observer + asyncio 브릿지. YAML 영속성, CRUD API |
| `Agent_Workspace/schedules.yaml` | 7-A | 스케줄 규칙 저장소 (초기값: 빈 리스트) |
| `Agent_Workspace/watch_rules.yaml` | 7-B | 감시 규칙 저장소 (초기값: 빈 리스트) |

---

## 3. 수정 파일 목록

### `python_agent/router.py`
- `SCHEDULE` 인텐트 추가 (8번째 카테고리)
- 예시: "매일 오전 9시에", "스케줄 목록 보여줘", "자동 실행 설정해줘"

### `python_agent/web_ui.py`
전면 재작성 (Phase 6 대비 주요 변경점):

**FastAPI lifespan 추가:**
```python
@asynccontextmanager
async def lifespan(app):
    _scheduler.start()              # APScheduler 시작
    _monitor.start(event_loop)      # watchdog Observer 시작
    yield
    _scheduler.stop()
    _monitor.stop()
```

**신규 REST 엔드포인트:**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/schedule` | cron + task → 스케줄 등록 |
| `GET` | `/api/schedules` | 스케줄 목록 조회 |
| `DELETE` | `/api/schedule/{id}` | 스케줄 삭제 |
| `POST` | `/api/watch` | path + pattern + event + task → 감시 등록 |
| `GET` | `/api/watches` | 감시 규칙 목록 조회 |
| `DELETE` | `/api/watch/{id}` | 감시 규칙 삭제 |

**UI 개선 — 탭 구조 도입:**
- 💬 **채팅 탭:** Phase 6 기존 UI (변경 없음)
- ⚙️ **자동화 탭:** Scheduler & Event Monitor 관리 UI
  - cron 표현식 입력 + 태스크 입력 → 스케줄 등록
  - 감시 경로 / 패턴 / 이벤트 / 태스크 입력 → 감시 규칙 등록
  - 등록된 규칙 목록 카드 표시 + 개별 삭제 버튼
  - cron 예시 힌트 바 제공

**WebSocket 인텐트 처리:**
- `SCHEDULE` 수신 시 → "⚙️ 자동화 탭에서 스케줄을 등록하거나 관리할 수 있습니다." 반환

**헬스 체크 업데이트:**
- 버전: `0.3.0`, phase: `"7"`
- `schedules`, `watches` 카운트 추가

### `python_agent/pyproject.toml`
```
apscheduler>=3.11.2       # cron 기반 자율 스케줄러
watchdog>=6.0.0            # 파일시스템 이벤트 감시
python-multipart>=0.0.22  # FastAPI UploadFile 지원 (Phase 6 누락분 보완)
```
`py-modules`에 `scheduler`, `event_monitor` 추가

---

## 4. 아키텍처 흐름 (Phase 7 추가분)

```
[FastAPI 서버 시작]
    → lifespan startup
        → AgentScheduler.start()       ← APScheduler 스케줄 복원
        → EventMonitor.start(loop)     ← watchdog Observer 시작

[스케줄러 자동 실행]
    APScheduler cron 트리거
        → run_in_executor(handle_task, task_text)
            → ReAct 루프 실행
                → 도구 사용 (파일, 웹 등)

[파일 감시 자동 실행]
    watchdog 스레드 파일 이벤트 감지
        → asyncio.run_coroutine_threadsafe(루프)
            → run_in_executor(handle_task, task_text)
                → ReAct 루프 실행

[브라우저 자동화 탭]
    POST /api/schedule   → AgentScheduler.add_schedule()   → schedules.yaml 저장
    GET  /api/schedules  → AgentScheduler.list_schedules()
    DELETE /api/schedule/{id} → AgentScheduler.delete_schedule()

    POST /api/watch      → EventMonitor.add_watch()         → watch_rules.yaml 저장
    GET  /api/watches    → EventMonitor.list_watches()
    DELETE /api/watch/{id}  → EventMonitor.delete_watch()
```

---

## 5. 추가된 의존성 (실설치 버전)

```
apscheduler==3.11.2
tzdata==2025.3
tzlocal==5.3.1
watchdog==6.0.0
python-multipart==0.0.22
```

---

## 6. 사전 요구사항

없음 — 기존 Ollama + faster-whisper 환경과 동일.
스케줄러/감시 규칙은 서버 재시작 시 YAML에서 자동 복원됩니다.

---

## 7. 미구현 항목 (Phase 6-C)

**Wake Word** (`openwakeword`): 여전히 복잡도 높음.
- 백그라운드 마이크 상시 모니터링 + Tauri 트레이 연동 필요
- Phase 7 완료 기준으로는 보조 기능이므로 추후 착수 권장

---

## 8. 인수인계 가이드

### 개발 모드 실행
```bash
cd python_agent
uv run python web_ui.py
# → http://localhost:8000 접속 → ⚙️ 자동화 탭
```

### 스케줄 등록 예시 (REST)
```bash
curl -X POST http://localhost:8000/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"cron": "0 9 * * 1-5", "task": "오늘 날씨 정보를 Agent_Workspace/weather.txt에 저장해줘"}'
```

### 파일 감시 등록 예시 (REST)
```bash
curl -X POST http://localhost:8000/api/watch \
  -H "Content-Type: application/json" \
  -d '{"path": "Agent_Workspace/inbox", "pattern": "*.txt", "event": "created", "task": "{file} 내용을 요약해서 Agent_Workspace/summaries/에 저장해줘"}'
```

### YAML 직접 편집 (서버 재시작 후 반영)
- `Agent_Workspace/schedules.yaml`
- `Agent_Workspace/watch_rules.yaml`

---

수고하셨습니다! 이제 Ageis는 **스스로 판단하고, 정해진 시간에 행동하고, 파일 변화에 반응하는** 자율 에이전트가 되었습니다.
