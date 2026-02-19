"""
core_logic.py — Ageis Agent 핵심 로직 (UI 독립적)

UI(CLI, Web, Main)에서 공통으로 사용할 에이전트 인스턴스와 핸들러 함수들을 정의합니다.
"""
from datetime import datetime
import ollama

from router import classify_intent
from react_loop import ReActAgent
from memory import AgentMemory
from persona import build_system_prompt
from tools.file_reader import read_file_tool, write_file_tool
from tools.web_scraper import web_scrape_tool
from tools.vision_tool import analyze_image_tool
from tools.stt_tool import record_and_transcribe_tool, transcribe_file_tool
from tools.tts_tool import speak_tool
from plugin_loader import load_plugins

# 도구 등록
TOOLS = {
    "read_file": read_file_tool,
    "write_file": write_file_tool,
    "web_scrape": web_scrape_tool,
    "vision_analyze": analyze_image_tool,
    "stt_record": record_and_transcribe_tool,
    "stt_file": transcribe_file_tool,
    "tts_speak": speak_tool,
}

# 플러그인 로드 및 병합
plugin_tools = load_plugins()
if plugin_tools:
    print(f"[Core] Loaded {len(plugin_tools)} plugins: {', '.join(plugin_tools.keys())}")
    TOOLS.update(plugin_tools)

# 장기 기억 인스턴스
memory = AgentMemory()

# 에이전트 인스턴스 생성
agent = ReActAgent(tools=TOOLS, model_name="llama3.2", memory=memory)

def handle_chat(user_input: str) -> str:
    """단순 대화 처리 (ReAct 루프 없이 바로 응답, 페르소나+기억 적용)"""
    print("[Core] Mode: CHAT")
    system_prompt = build_system_prompt(user_input, memory)
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
    )
    answer = response["message"]["content"]
    
    # 대화 내용을 장기 기억에 저장
    memory.save(
        f"[Chat] User: {user_input}\nAgent: {answer}",
        metadata={"type": "chat", "timestamp": datetime.now().isoformat()}
    )
    return answer

def handle_task(user_input: str) -> str:
    """복합 작업 처리 (ReAct 루프 사용)"""
    print("[Core] Mode: TASK (ReAct)")
    return agent.run(user_input)


def handle_vision(image_path: str = "", base64_image: str = "", prompt: str = "") -> str:
    """이미지 분석 처리 (llava 모델 직접 호출)"""
    print("[Core] Mode: VISION")
    from tools.vision_tool import analyze_image_tool
    result = analyze_image_tool({
        "path": image_path,
        "base64_image": base64_image,
        "prompt": prompt or "이 이미지에 무엇이 있나요? 자세히 설명해주세요.",
    })
    memory.save(
        f"[Vision] prompt={prompt or '(기본 설명)'}\nResult: {result[:200]}",
        metadata={"type": "vision", "timestamp": datetime.now().isoformat()}
    )
    return result


def handle_voice(duration_sec: float = 5.0, language: str = "ko", tts_response: bool = True) -> str:
    """
    음성 입력을 받아 처리하고, 응답을 TTS로 읽어주는 파이프라인.
    1. 마이크 녹음 → STT (faster-whisper)
    2. STT 텍스트 → 일반 대화 처리 (handle_chat)
    3. 응답 → TTS 재생 (pyttsx3, async)
    """
    print("[Core] Mode: VOICE")
    from tools.stt_tool import record_and_transcribe_tool
    from tools.tts_tool import speak_async

    # STT: 마이크 녹음 → 텍스트
    transcribed = record_and_transcribe_tool({"duration": duration_sec, "language": language})
    if transcribed.startswith("ERROR:"):
        return transcribed

    print(f"[Core/VOICE] 인식된 입력: {transcribed!r}")

    # 인식된 텍스트로 일반 대화 처리
    response = handle_chat(transcribed)

    # TTS: 응답 음성 재생 (비동기)
    if tts_response:
        try:
            speak_async(response)
        except Exception as e:
            print(f"[Core/VOICE] TTS 재생 실패: {e}")

    return f"[음성 입력] {transcribed}\n\n{response}"
