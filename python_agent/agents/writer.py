from actor import AgentActor, AgentMessage
import ollama

class WriterAgent(AgentActor):
    """
    작가 에이전트
    - 정보를 종합하여 보고서나 글을 작성
    - 별도 도구 없이 LLM의 작문 능력 활용
    """
    def __init__(self, name="Writer"):
        super().__init__(
            name=name,
            persona="당신은 전문 작가입니다. 주어진 정보를 읽기 좋게 정리하고, 명확한 구조로 글을 작성하세요."
        )

    def think(self, message: AgentMessage) -> str:
        prompt = f"""
        [System] {self.persona}
        [Request] {message.content}
        """
        
        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}]
        )
        
        answer = response["message"]["content"]
        
        if message.sender != "User":
            self.send_message(
                recipient_name=message.sender,
                content=answer,
                msg_type="RESPONSE",
                context_id=message.context_id
            )
            
        return answer
