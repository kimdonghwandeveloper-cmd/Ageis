"""
main.py — Python 에이전트 진입점 (Refactored)

역할:
1. 커맨드라인 인자 파싱 (--cli, --web 등)
2. 실행 모드에 따라 적절한 UI 진입점 호출
"""

import sys
import argparse
from router import classify_intent
from core_logic import handle_chat, handle_task

# Windows 콘솔 인코딩 문제 해결
sys.stdout.reconfigure(encoding='utf-8')

def standard_main():
    """기본 터미널 모드 (Plain Text)"""
    print("=== Ageis Agent (Standard Mode) ===")
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
                response = handle_task(user_input)
            elif intent == "PERSONA":
                response = "persona.yaml 파일을 직접 수정한 후 재시작해 주세요."
            else:
                response = handle_chat(user_input)

            # 3. 결과 출력
            print(f"\nAgent: {response}")
            
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except Exception as e:
            print(f"\n[Error] {e}")

def main():
    parser = argparse.ArgumentParser(description="Ageis AI Agent")
    parser.add_argument("--cli", action="store_true", help="Run with Rich CLI Dashboard")
    parser.add_argument("--web", action="store_true", help="Run with Web UI")
    args = parser.parse_args()

    if args.cli:
        from cli import cli_main
        cli_main(None) # agent 인스턴스는 core_logic에서 관리되므로 전달 불필요하거나 나중에 리팩토링
    elif args.web:
        from web_ui import web_main
        web_main()
    else:
        standard_main()

if __name__ == "__main__":
    main()
