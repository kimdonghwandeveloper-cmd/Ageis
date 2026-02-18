"""
main.py — Python 에이전트 진입점 (Phase 2 완료 버전)

역할:
1. 사용자 입력을 받음
2. Router를 통해 의도 분류 (CHAT, FILE, WEB, TASK 등)
3. 적절한 핸들러(ReAct Agent 등)로 라우팅하여 실행
4. 결과 반환
"""

import sys
# Windows 콘솔 인코딩 문제 해결을 위해 필요할 수 있음
sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime
from router import classify_intent
from react_loop import ReActAgent
from memory import AgentMemory
from persona import build_system_prompt
from tools.file_reader import read_file_tool, write_file_tool
from tools.web_scraper import web_scrape_tool
import ollama

# 도구 등록
TOOLS = {
    "read_file": read_file_tool,
    "write_file": write_file_tool,
    "web_scrape": web_scrape_tool,
}

# 장기 기억 인스턴스 (Phase 3)
memory = AgentMemory()

# 에이전트 인스턴스 생성 (메모리 주입)
agent = ReActAgent(tools=TOOLS, model_name="llama3.2", memory=memory)

def handle_chat(user_input: str):
    """단순 대화 처리 (ReAct 루프 없이 바로 응답, 페르소나+기억 적용)"""
    print("[Main] Mode: CHAT")
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

def handle_task(user_input: str):
    """복합 작업 처리 (ReAct 루프 사용)"""
    print("[Main] Mode: TASK (ReAct)")
    return agent.run(user_input)

def handle_file(user_input: str):
    """파일 관련 작업도 ReAct 루프에 위임 (도구 사용 필요하므로)"""
    print("[Main] Mode: FILE (delegating to ReAct)")
    return agent.run(user_input)

def handle_web(user_input: str):
    """웹 검색 작업도 ReAct 루프에 위임"""
    print("[Main] Mode: WEB (delegating to ReAct)")
    return agent.run(user_input)

def main():
    print("=== Ageis Agent (Phase 3: The Soul) ===")
    print("Type '/quit' to exit.\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            
            if user_input.lower() in ["/quit", "/exit"]:
                print("Goodbye.")
                break
                
            # 1. 의도 분류
            intent = classify_intent(user_input)
            print(f"[Router] Detected Intent: {intent}")
            
            # 2. 라우팅
            if intent == "CHAT":
                response = handle_chat(user_input)
            elif intent in ["FILE", "WEB", "TASK"]:
                response = handle_task(user_input) # FILE, WEB도 ReAct가 처리하도록 통일
            elif intent == "PERSONA":
                response = "persona.yaml 파일을 직접 수정한 후 재시작해 주세요. (Agent_Workspace/persona.yaml)"
            else:
                response = handle_chat(user_input) # 기본

            # 3. 결과 출력
            print(f"\nAgent: {response}")
            
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except Exception as e:
            print(f"\n[Error] {e}")

if __name__ == "__main__":
    main()
