"""
tts_tool.py — Phase 6-B: 음성 합성 도구 (TTS: Text-To-Speech)

사용 기술:
  - pyttsx3: Windows SAPI / macOS NSSpeechSynthesizer / Linux eSpeak 직접 사용
              (오프라인, 설치 간단, 크로스플랫폼)

설치:
  uv add pyttsx3

참고:
  - Windows: 별도 설치 불필요 (SAPI 내장)
  - Linux: espeak 필요 `sudo apt install espeak`
"""
import threading

try:
    import pyttsx3
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False
    print("[TTS] pyttsx3 없음 — TTS 기능 비활성화. `uv add pyttsx3` 실행하세요.")

# pyttsx3 엔진은 한 번만 생성해서 재사용 (스레드 안전 주의)
_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        # 기본 속도 조절 (단어/분, 기본값 ~200)
        _engine.setProperty("rate", 170)
        # 볼륨 (0.0 ~ 1.0)
        _engine.setProperty("volume", 1.0)
    return _engine


def speak(text: str, rate: int = 170, volume: float = 1.0) -> None:
    """
    텍스트를 음성으로 즉시 재생합니다 (블로킹).
    """
    if not _PYTTSX3_AVAILABLE:
        raise RuntimeError("pyttsx3가 설치되지 않았습니다.")

    with _engine_lock:
        engine = _get_engine()
        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)
        engine.say(text)
        engine.runAndWait()


def speak_async(text: str, rate: int = 170, volume: float = 1.0) -> threading.Thread:
    """
    텍스트를 백그라운드 스레드에서 비동기로 재생합니다.
    반환된 Thread 객체로 완료 여부 확인 가능.
    """
    t = threading.Thread(target=speak, args=(text, rate, volume), daemon=True)
    t.start()
    return t


def speak_tool(args: dict) -> str:
    """
    ReAct 도구 인터페이스: 텍스트를 음성으로 변환하여 재생.

    args:
        text (str): 읽어줄 텍스트
        rate (int): 말하기 속도 (단어/분), 기본값 170
        volume (float): 볼륨 (0.0 ~ 1.0), 기본값 1.0
        async_mode (bool): True이면 비동기 재생, 기본값 False
    """
    if not _PYTTSX3_AVAILABLE:
        return "ERROR: pyttsx3가 설치되지 않았습니다. `uv add pyttsx3` 를 실행하세요."

    text = args.get("text", "")
    if not text.strip():
        return "ERROR: 읽어줄 텍스트(text)를 제공해야 합니다."

    rate = int(args.get("rate", 170))
    volume = float(args.get("volume", 1.0))
    async_mode = bool(args.get("async_mode", False))

    try:
        if async_mode:
            speak_async(text, rate=rate, volume=volume)
            return f"[TTS] 비동기 재생 시작: {text[:50]}..."
        else:
            speak(text, rate=rate, volume=volume)
            return f"[TTS] 재생 완료: {text[:50]}..."
    except Exception as e:
        return f"ERROR: TTS 실패 — {e}"
