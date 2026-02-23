"""
stt_tool.py — Phase 6-B: 음성 인식 도구 (STT: Speech-To-Text)

사용 기술:
  - sounddevice: 마이크 오디오 캡처 (Windows 친화적, pyaudio 대체)
  - faster-whisper: OpenAI Whisper 경량화 로컬 구현 (CUDA/CPU 모두 지원)

설치:
  uv add faster-whisper sounddevice

의존성:
  - ffmpeg가 PATH에 있어야 함 (faster-whisper 내부 사용)
  - Windows: https://www.gyan.dev/ffmpeg/builds/ 에서 설치
"""
import io
import queue
import threading
import tempfile
import os

import numpy as np

# 선택적 임포트 — 패키지가 없어도 나머지 시스템은 동작
try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False
    print("[STT] sounddevice 없음 — 마이크 기능 비활성화. `uv add sounddevice` 실행하세요.")

try:
    from faster_whisper import WhisperModel
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False
    print("[STT] faster-whisper 없음 — STT 기능 비활성화. `uv add faster-whisper` 실행하세요.")


# Whisper 모델 크기: tiny / base / small / medium / large
# tiny (~39MB): 메모리 제한 환경에서 안정적
# base (~145MB): 속도와 정확도의 균형 (RAM 여유 있을 때)
WHISPER_MODEL_SIZE = "tiny"
SAMPLE_RATE = 16000   # Whisper 권장 샘플레이트
CHANNELS = 1          # 모노

_whisper_model = None  # 지연 초기화 (첫 호출 시 로드)


def _get_whisper_model() -> "WhisperModel":
    global _whisper_model
    if _whisper_model is None:
        print(f"[STT] Whisper 모델 로딩 중: {WHISPER_MODEL_SIZE} ...")
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        print("[STT] Whisper 모델 로드 완료.")
    return _whisper_model


def record_audio(duration_sec: float = 5.0) -> np.ndarray:
    """
    마이크에서 duration_sec 초 동안 오디오를 녹음하여 numpy 배열로 반환.
    """
    if not _SD_AVAILABLE:
        raise RuntimeError("sounddevice가 설치되지 않았습니다.")

    print(f"[STT] 녹음 시작 ({duration_sec}초)...")
    audio = sd.rec(
        int(duration_sec * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()  # 녹음 완료까지 대기
    print("[STT] 녹음 완료.")
    return audio.flatten()


def transcribe_audio(audio: np.ndarray, language: str = "ko") -> str:
    """
    numpy 오디오 배열을 텍스트로 변환 (faster-whisper 사용).
    """
    if not _WHISPER_AVAILABLE:
        raise RuntimeError("faster-whisper가 설치되지 않았습니다.")

    model = _get_whisper_model()

    # faster-whisper는 파일 경로 또는 numpy 배열을 직접 받음
    segments, info = model.transcribe(audio, language=language, beam_size=5)
    text = " ".join(segment.text.strip() for segment in segments)
    print(f"[STT] 인식된 텍스트: {text!r}")
    return text


def record_and_transcribe_tool(args: dict) -> str:
    """
    ReAct 도구 인터페이스: 마이크 녹음 후 텍스트로 변환.

    args:
        duration (float): 녹음 시간(초), 기본값 5
        language (str): 인식 언어 코드 ("ko" / "en" 등), 기본값 "ko"
    """
    if not _SD_AVAILABLE or not _WHISPER_AVAILABLE:
        return "ERROR: STT 의존성(sounddevice, faster-whisper)이 설치되지 않았습니다."

    duration = float(args.get("duration", 5.0))
    language = args.get("language", "ko")

    try:
        audio = record_audio(duration_sec=duration)
        text = transcribe_audio(audio, language=language)
        return text if text.strip() else "(인식된 텍스트 없음)"
    except Exception as e:
        return f"ERROR: STT 실패 — {e}"


def transcribe_file_tool(args: dict) -> str:
    """
    ReAct 도구 인터페이스: 오디오 파일을 텍스트로 변환.

    args:
        path (str): 오디오 파일 경로 (wav, mp3, m4a 등)
        language (str): 인식 언어 코드, 기본값 "ko"
    """
    if not _WHISPER_AVAILABLE:
        return "ERROR: faster-whisper가 설치되지 않았습니다."

    path = args.get("path", "")
    if not path or not os.path.isfile(path):
        return f"ERROR: 파일을 찾을 수 없습니다: {path}"

    language = args.get("language", "ko")

    try:
        model = _get_whisper_model()
        segments, _ = model.transcribe(path, language=language, beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments)
        return text if text.strip() else "(인식된 텍스트 없음)"
    except Exception as e:
        return f"ERROR: 파일 STT 실패 — {e}"
