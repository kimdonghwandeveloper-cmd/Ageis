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
from plugin_loader import load_plugins

# 도구 등록
TOOLS = {
    "read_file": read_file_tool,
    "write_file": write_file_tool,
    "web_scrape": web_scrape_tool,
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
