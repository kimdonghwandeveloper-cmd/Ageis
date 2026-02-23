"""
core_logic.py — Ageis Agent 핵심 로직 (Phase 1~8 통합)

UI(CLI, Web, Scheduler, EventMonitor)에서 공통으로 사용하는
핸들러 함수들과 에이전트 인스턴스를 정의합니다.

Phase 8에서 Multi-Agent Society가 추가되었으나,
기존 handle_chat / handle_task / handle_vision / handle_voice는 그대로 유지합니다.
"""
from datetime import datetime
import ollama

from config import MODEL_NAME
from router import classify_intent
from react_loop import ReActAgent
from memory import AgentMemory
from persona import build_system_prompt
from tools.file_reader import read_file_tool, write_file_tool, list_dir_tool
from tools.web_scraper import web_scrape_tool
from tools.web_search import web_search_tool
from tools.vision_tool import analyze_image_tool
from tools.stt_tool import record_and_transcribe_tool, transcribe_file_tool
from tools.tts_tool import speak_tool
from plugin_loader import load_plugins

# Phase 8: Multi-Agent Society
from actor import AgentMessage
from registry import AgentRegistry
from agents.manager import ManagerAgent
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent

# ─── 도구 등록 ───────────────────────────────────────────────────────────────

TOOLS = {
    "read_file": read_file_tool,
    "write_file": write_file_tool,
    "list_dir": list_dir_tool,
    "web_search": web_search_tool,
    "web_scrape": web_scrape_tool,
    "vision_analyze": analyze_image_tool,
    "stt_record": record_and_transcribe_tool,
    "stt_file": transcribe_file_tool,
    "tts_speak": speak_tool,
}

plugin_tools = load_plugins()
if plugin_tools:
    print(f"[Core] Loaded {len(plugin_tools)} plugins: {', '.join(plugin_tools.keys())}")
    TOOLS.update(plugin_tools)

# ─── 단일 에이전트 (ReAct) ────────────────────────────────────────────────────

memory = AgentMemory()
agent = ReActAgent(tools=TOOLS, model_name=MODEL_NAME, memory=memory)

# ─── Phase 8: Multi-Agent Society ────────────────────────────────────────────

_registry = AgentRegistry()
_manager = ManagerAgent()
_researcher = ResearcherAgent()
_writer = WriterAgent()

for _a in (_manager, _researcher, _writer):
    _registry.register(_a)

print(f"[Core] Society Formed: [{_manager.name}, {_researcher.name}, {_writer.name}]")


# ─── 핸들러 함수 ─────────────────────────────────────────────────────────────

def handle_chat(user_input: str) -> str:
    """단순 대화 처리 — ReAct 루프 없이 바로 응답, 페르소나+기억 적용."""
    print("[Core] Mode: CHAT")
    system_prompt = build_system_prompt(user_input, memory)
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
    )
    answer = response["message"]["content"]
    memory.save(
        f"[Chat] User: {user_input}\nAgent: {answer}",
        metadata={"type": "chat", "timestamp": datetime.now().isoformat()},
    )
    return answer


def handle_task(user_input: str) -> str:
    """복합 작업 처리 — ReAct 루프 사용."""
    print("[Core] Mode: TASK (ReAct)")
    return agent.run(user_input)


def handle_vision(image_path: str = "", base64_image: str = "", prompt: str = "") -> str:
    """이미지 분석 처리 — llava 모델 직접 호출."""
    print("[Core] Mode: VISION")
    result = analyze_image_tool({
        "path": image_path,
        "base64_image": base64_image,
        "prompt": prompt or "이 이미지에 무엇이 있나요? 자세히 설명해주세요.",
    })
    memory.save(
        f"[Vision] prompt={prompt or '(기본 설명)'}\nResult: {result[:200]}",
        metadata={"type": "vision", "timestamp": datetime.now().isoformat()},
    )
    return result


def handle_voice(duration_sec: float = 5.0, language: str = "ko", tts_response: bool = True) -> str:
    """음성 파이프라인 — STT → handle_chat → TTS."""
    print("[Core] Mode: VOICE")
    from tools.stt_tool import record_and_transcribe_tool
    from tools.tts_tool import speak_async

    transcribed = record_and_transcribe_tool({"duration": duration_sec, "language": language})
    if transcribed.startswith("ERROR:"):
        return transcribed

    try:
        print(f"[Core/VOICE] 인식된 입력: {transcribed!r}".encode('utf-8', 'replace').decode('utf-8'))
    except:
        pass
    response = handle_chat(transcribed)

    if tts_response:
        try:
            speak_async(response)
        except Exception as e:
            try:
                print(f"[Core/VOICE] TTS 재생 실패: {e}".encode('utf-8', 'replace').decode('utf-8'))
            except:
                pass

    return f"[음성 입력] {transcribed}\n\n{response}"


def handle_society(user_input: str) -> str:
    """멀티에이전트 처리 — Phase 8: Manager → Researcher/Writer 위임."""
    print("[Core] Mode: SOCIETY (Multi-Agent)")
    msg = AgentMessage(
        sender="User",
        recipient="Manager",
        content=user_input,
        msg_type="REQUEST",
    )
    result = _manager.receive_message(msg)
    memory.save(
        f"[Society] User: {user_input}\nResult: {str(result)[:300]}",
        metadata={"type": "society", "timestamp": datetime.now().isoformat()},
    )
    return result or "멀티에이전트 처리 중 오류가 발생했습니다."
