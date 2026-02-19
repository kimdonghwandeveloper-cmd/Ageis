"""
main.py — Python 에이전트 진입점 (Phase 8: The Society)

역할:
1. Multi-Agent System 초기화 (Registry, Agents)
2. AgentCore에 Manager Agent 주입
3. UI 모드 실행 (CLI / Web / Standard)
"""

import sys
import argparse
from pathlib import Path

# --- Core Modules ---
from core_logic import AgentCore
from grpc_client import AgentGrpcClient
from memory import AgentMemory
from persona import load_persona
from plugin_loader import load_plugins

# --- Multi-Agent Modules ---
from registry import AgentRegistry
from agents.manager import ManagerAgent
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent

# Global Configs
SERVER_ADDRESS = "localhost:50051"
WORKSPACE_DIR = Path("../Agent_Workspace").resolve()
DNA_PATH = WORKSPACE_DIR / "persona.yaml"

# Windows Console Encoding Fix
sys.stdout.reconfigure(encoding='utf-8')

def initialize_system():
    """시스템 컴포넌트 초기화 및 조립"""
    print("🚀 Ageis Agent Initiating... (Phase 8: The Society)")

    # 1. Body (gRPC)
    grpc_client = AgentGrpcClient(SERVER_ADDRESS)

    # 2. Soul (Memory & Persona)
    memory = AgentMemory()
    persona_data = load_persona(DNA_PATH)
    print(f"👻 Persona Loaded: {persona_data.get('name', 'Unknown')}")

    # 3. Expansion (Plugins)
    plugins = load_plugins()
    if plugins:
        print(f"🔌 Plugins Loaded: {', '.join(plugins.keys())}")

    # 4. Society (Multi-Agent Registry)
    registry = AgentRegistry()
    
    # 에이전트 생성
    manager = ManagerAgent(name="Manager")
    researcher = ResearcherAgent(name="Researcher")
    writer = WriterAgent(name="Writer")
    
    # 에이전트 등록
    registry.register(manager)
    registry.register(researcher)
    registry.register(writer)
    print("👥 Society Formed: [Manager, Researcher, Writer]")

    # 5. Core Logic Assembly
    # AgentCore는 이제 Manager를 통해 모든 작업을 처리함
    core = AgentCore(
        grpc_client=grpc_client,
        tools=plugins,      # 레거시 호환성 (플러그인은 Researcher 등이 사용 가능하게 전달 필요)
        memory=memory,
        persona=persona_data,
        manager_agent=manager # [NEW] Manager 주입
    )
    
    # *중요*: 하위 에이전트들에게도 Core/Tools 접근 권한이 필요할 수 있음
    # 현재 구조에서는 단순화하여 Manager가 지시만 내리는 구조로 시작
    
    return core

def standard_main(agent_core):
    """기본 터미널 모드"""
    print("\n=== Ageis Agent (Standard Mode) ===")
    print("Type '/quit' to exit.\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            
            if user_input.lower() in ["/quit", "/exit"]:
                print("Goodbye.")
                break
                
            # Core를 통해 Manager에게 전달
            response = agent_core.handle_chat(user_input)
            print(f"\nAgeis: {response}")
            
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except Exception as e:
            print(f"\n[Error] {e}")

def main():
    parser = argparse.ArgumentParser(description="Ageis AI Agent (Phase 8)")
    parser.add_argument("--cli", action="store_true", help="Run with Rich CLI Dashboard")
    parser.add_argument("--web", action="store_true", help="Run with Web UI")
    args = parser.parse_args()

    # 시스템 초기화
    agent_core = initialize_system()

    # 모드 선택
    if args.cli:
        from cli import cli_main
        cli_main(agent_core)
    elif args.web:
        from web_ui import run_web_server # 함수명 확인 필요
        # web_ui.py가 모듈화되어 있어야 함. 현재 구조 확인 필요.
        # 기존 web_ui.py는 직접실행 구조일 수 있음.
        # 임시로 기존 방식(import) 사용 시도
        from web_ui import main as web_main_func
        web_main_func(agent_core)
    else:
        standard_main(agent_core)

if __name__ == "__main__":
    main()
