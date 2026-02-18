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

from router import classify_intent
from react_loop import ReActAgent
from tools.file_reader import read_file_tool, write_file_tool
from tools.web_scraper import web_scrape_tool
import ollama

# 도구 등록
TOOLS = {
    "read_file": read_file_tool,
    "write_file": write_file_tool,
    "web_scrape": web_scrape_tool,
}

# 에이전트 인스턴스 생성 (한 번 로드)
agent = ReActAgent(tools=TOOLS, model_name="llama3.2")

def handle_chat(user_input: str):
    """단순 대화 처리 (ReAct 루프 없이 바로 응답)"""
    print("[Main] Mode: CHAT")
    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": user_input}]
    )
    return response["message"]["content"]

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
    print("=== Ageis Agent (Phase 2: The Brain) ===")
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
                response = "Phase 3에서 구현될 기능입니다 (Persona Update)."
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
