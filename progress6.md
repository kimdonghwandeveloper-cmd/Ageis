# Phase 6 완료 보고서 — 감각 부여 (The Senses: Multimodal Expansion)

> **작성일:** 2026-02-19
> **완료 Phase:** Phase 6-A (Vision), Phase 6-B (Voice STT/TTS)
> **미완료:** Phase 6-C (Wake Word) — 복잡도 높음, Phase 7 이후 착수 권장

---

## 1. 개요 및 성과

텍스트 전용이었던 Ageis Agent에 **보고 듣는 감각**을 부여했습니다.

- **6-A Vision:** 이미지를 업로드하거나 클립보드에서 붙여넣으면, ollama `llava` 멀티모달 모델이 이미지를 분석하고 설명합니다.
- **6-B Voice:** 브라우저 마이크로 음성을 녹음하면 `faster-whisper`가 텍스트로 변환하고, LLM이 응답한 뒤 `pyttsx3`로 음성 재생합니다.

---

## 2. 신규 파일 목록

| 파일 | Phase | 설명 |
|------|:-----:|------|
| `python_agent/tools/vision_tool.py` | 6-A | ollama llava 호출 래퍼. 파일 경로 / base64 양쪽 지원 |
| `python_agent/tools/stt_tool.py` | 6-B | sounddevice 마이크 녹음 + faster-whisper STT. 지연 초기화 (미설치 시 앱 구동 보장) |
| `python_agent/tools/tts_tool.py` | 6-B | pyttsx3 TTS. 동기/비동기 재생 지원. Windows SAPI 직접 사용 |

---

## 3. 수정 파일 목록

### `python_agent/router.py`
- `VISION` 인텐트 추가: 이미지 분석, 사진 설명 요청 감지
- `VOICE` 인텐트 추가: 음성 입력, 마이크 녹음 관련 요청 감지
- 유효 카테고리: `CHAT / FILE / WEB / TASK / PERSONA / VISION / VOICE` (7종)

### `python_agent/core_logic.py`
- `handle_vision(image_path, base64_image, prompt)` 함수 추가
  - llava 모델로 이미지 분석 후 결과를 장기 기억(RAG)에 저장
- `handle_voice(duration_sec, language, tts_response)` 함수 추가
  - STT → handle_chat → TTS 3단계 파이프라인
- 도구 등록 추가: `vision_analyze`, `stt_record`, `stt_file`, `tts_speak` (4종)

### `python_agent/web_ui.py`
전면 재작성 (Phase 4 대비 주요 변경점):

**신규 REST 엔드포인트:**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/vision` | base64 이미지 → llava 분석 |
| `POST` | `/api/vision/file` | 파일 업로드 이미지 → llava 분석 |
| `POST` | `/api/voice` | 서버 마이크 녹음 → STT → LLM 응답 |
| `POST` | `/api/voice/upload` | 브라우저 녹음 파일 업로드 → STT → LLM 응답 |

**UI 개선:**
- 🖼 이미지 첨부 버튼: 파일 선택 다이얼로그
- 📋 클립보드 붙여넣기 (Ctrl+V): 스크린샷 등 클립보드 이미지 바로 첨부
- 이미지 첨부 시 썸네일 프리뷰 바 표시 (취소 버튼 포함)
- 🎤 마이크 버튼: 브라우저 MediaRecorder API로 녹음 → `/api/voice/upload` 전송
- 녹음 중 버튼 빨간색 + 맥박 애니메이션으로 상태 표시
- WebSocket: VISION/VOICE 인텐트 수신 시 UI 사용 안내 메시지 반환
- 헬스 체크 버전: `0.2.0`, phase: `"6"`

### `python_agent/pyproject.toml`
```
faster-whisper>=1.1.1   # 로컬 Whisper STT (CPU/CUDA)
sounddevice>=0.5.1      # 마이크 오디오 캡처
pyttsx3>=2.98           # 로컬 TTS
```

---

## 4. 실제 설치된 패키지 버전

```
faster-whisper==1.2.1
sounddevice==0.5.5
pyttsx3==2.99
ctranslate2==4.7.1   (faster-whisper 백엔드)
av==16.1.0           (오디오 디코딩)
pywin32==311         (Windows TTS 지원)
```

---

## 5. 아키텍처 흐름 (Phase 6 추가분)

```
[브라우저]
  🖼 이미지 첨부 / Ctrl+V 붙여넣기
      → POST /api/vision  (base64)
          → handle_vision()
              → tools/vision_tool.py
                  → ollama llava
                      → 분석 텍스트 반환

  🎤 마이크 버튼 (MediaRecorder)
      → POST /api/voice/upload  (webm 파일)
          → tools/stt_tool.transcribe_file_tool()
              → faster-whisper (로컬)
                  → 텍스트
                      → handle_chat()
                          → LLM 응답
                              → (서버 측) pyttsx3 TTS 재생
                              → 브라우저에 텍스트 응답 반환
```

---

## 6. 사전 요구사항

### Vision 활성화
```bash
ollama pull llava   # 약 4~7GB, 최초 1회만 실행
```
> Ollama가 설치/실행 중이어야 함. 어느 디렉토리에서나 실행 가능.

### STT 활성화
- `faster-whisper` 첫 실행 시 `base` 모델 자동 다운로드 (약 140MB)
- 별도 설치 불필요

### TTS 활성화
- Windows: SAPI 내장, 별도 설치 불필요
- Linux: `sudo apt install espeak` 필요

---

## 7. 미구현 항목 (Phase 6-C)

**Wake Word** (`openwakeword`): 복잡도 높음, Phase 7 완료 후 착수 권장.
- 백그라운드 스레드 상시 마이크 모니터링
- Wake word 감지 → STT 파이프라인 자동 트리거
- Tauri 시스템 트레이 연동 필요

---

## 8. 인수인계 가이드

### Python 코드 수정 후 데스크톱 앱에 반영
Phase 5 방식 동일:
```bash
uv run pyinstaller --onefile --name ageis-agent python_agent/main.py
mv dist/ageis-agent.exe desktop/src-tauri/bin/ageis-agent-x86_64-pc-windows-msvc.exe
```

### 개발 모드 실행 (웹 UI만)
```bash
cd python_agent
uv run python web_ui.py
# → http://localhost:8000 접속
```

### 새 도구를 ReAct 루프에 추가하는 방법
`core_logic.py`의 `TOOLS` 딕셔너리에 등록:
```python
TOOLS["my_tool"] = my_tool_function
```

---

수고하셨습니다! 이제 Ageis는 텍스트를 넘어 **이미지를 보고, 음성을 듣고, 말할 수 있는** 멀티모달 에이전트가 되었습니다.
