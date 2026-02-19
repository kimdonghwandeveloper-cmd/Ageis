"""
core_logic.py — Ageis Agent 핵심 로직 (Phase 8: The Society)

UI(CLI, Web, Main)에서 공통으로 사용할 에이전트 인스턴스와 핸들러 함수들을 정의합니다.
Phase 8에서는 단일 ReAct Agent 대신 Multi-Agent System의 Manager에게 작업을 위임합니다.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from actor import AgentMessage
from agents.manager import ManagerAgent
from memory import AgentMemory

class AgentCore:
    """
    UI와 Multi-Agent System 사이의 중개자 (Facade Pattern)
    """
    def __init__(
        self,
        grpc_client,
        tools: Dict[str, Any],
        memory: AgentMemory,
        persona: Dict[str, Any],
        manager_agent: ManagerAgent
    ):
        self.grpc_client = grpc_client
        self.tools = tools
        self.memory = memory
        self.persona = persona
        self.manager = manager_agent

    def handle_chat(self, user_input: str, stream: bool = False) -> str:
        """
        사용자 입력을 Manager Agent에게 전달하고 응답을 받음
        """
        print(f"[Core] User Request: {user_input}")
        
        # 1. Manager에게 메시지 전송 (가상의 User 송신자)
        # Manager의 think() 메서드를 직접 호출하거나, 메시지를 보내고 결과를 기다림
        
        msg = AgentMessage(
            sender="User",
            recipient="Manager",
            content=user_input,
            msg_type="REQUEST"
        )
        
        # Manager가 생각하고 답을 줌 (동기식 호출 가정)
        response = self.manager.receive_message(msg)
        
        # 2. 결과 저장
        self.memory.save(
            f"[Chat] User: {user_input}\nManager: {response}",
            metadata={"type": "chat", "timestamp": datetime.now().isoformat()}
        )
        
        return response

    def handle_task(self, user_input: str) -> str:
        """
        복합 작업 처리 (현재는 handle_chat과 동일하게 Manager에게 위임)
        """
        return self.handle_chat(user_input)

# 전역 인스턴스 (main.py에서 초기화 후 주입됨)
# 모듈 레벨 함수들은 하위 호환성을 위해 유지하되, 실제로는 AgentCore 인스턴스를 사용해야 함
