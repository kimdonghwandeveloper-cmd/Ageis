from typing import Dict, Any, Optional
from actor import AgentActor, AgentMessage

class AgentRegistry:
    """
    모든 에이전트를 관리하고 메시지를 중계하는 중앙 허브 (Message Bus)
    """
    def __init__(self):
        self._agents: Dict[str, AgentActor] = {}

    def register(self, agent: AgentActor):
        """에이전트를 레지스트리에 등록"""
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' is already registered.")
        
        self._agents[agent.name] = agent
        agent.set_registry(self)
        print(f"[Registry] Registered agent: {agent.name}")

    def get_agent(self, name: str) -> Optional[AgentActor]:
        return self._agents.get(name)

    def dispatch(self, message: AgentMessage) -> Any:
        """메시지를 수신자에게 전달하고, 처리 결과(있는 경우)를 반환"""
        recipient = self._agents.get(message.recipient)
        
        print(f" >>> [MSG] {message.sender} -> {message.recipient} ({message.msg_type})")

        if not recipient:
            print(f"ERROR: Recipient '{message.recipient}' not found.")
            return None

        # 동기식 호출: 수신자의 처리 결과를 반환
        return recipient.receive_message(message)
