import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

@dataclass
class AgentMessage:
    """에이전트 간 통신을 위한 메시지 규격"""
    sender: str
    recipient: str
    content: str
    msg_type: str = "REQUEST"  # REQUEST, RESPONSE, INFO, ERROR
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

class AgentActor(ABC):
    """
    모든 에이전트의 기본 클래스 (Actor Model)
    - 독립적인 상태(State)와 도구(Tools)를 가짐
    - 메시지를 주고받으며 협업
    """
    def __init__(self, name: str, persona: str, tools: Dict[str, Any] = None):
        self.name = name
        self.persona = persona
        self.tools = tools or {}
        self.inbox: List[AgentMessage] = []
        self.registry = None  # AgentRegistry 참조 (나중에 주입)

    def set_registry(self, registry):
        self.registry = registry

    def send_message(self, recipient_name: str, content: str, msg_type: str = "REQUEST", context_id: str = None, **kwargs) -> Any:
        """
        다른 에이전트에게 메시지를 보냄.
        Registry의 dispatch가 동기식으로 결과를 반환하면, 그 값을 리턴함.
        """
        if not self.registry:
            raise RuntimeError(f"Agent {self.name} is not registered in any registry.")
        
        msg = AgentMessage(
            sender=self.name,
            recipient=recipient_name,
            content=content,
            msg_type=msg_type,
            context_id=context_id or str(uuid.uuid4()),
            metadata=kwargs
        )
        return self.registry.dispatch(msg)

    def receive_message(self, message: AgentMessage):
        """메시지를 수신함 (Inbox에 저장)"""
        self.inbox.append(message)
        # 즉시 think()를 호출하고 결과를 반환 (동기 체인)
        return self.think(message)

    @abstractmethod
    def think(self, message: AgentMessage) -> Optional[str]:
        """
        메시지를 받고 스스로 생각하고 행동하는 메서드
        - 하위 클래스에서 ReAct 루프 등을 구현해야 함
        """
        pass
