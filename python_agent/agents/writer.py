import ollama
from actor import AgentActor, AgentMessage


class WriterAgent(AgentActor):
    """
    작가 에이전트
    - 정보를 종합하여 보고서·요약·글 작성
    - 별도 도구 없이 LLM 작문 능력 활용
    """

    def __init__(self, name: str = "Writer"):
        super().__init__(
            name=name,
            persona=(
                "당신은 전문 작가입니다. "
                "주어진 정보를 읽기 좋게 정리하고, 명확한 구조로 글을 작성하세요."
            ),
        )

    def think(self, message: AgentMessage) -> str:
        """
        요청 내용을 잘 정리된 글로 작성하여 반환합니다.
        반환값은 send_message() 체인을 통해 호출자(Manager)에게 전달되므로
        별도로 send_message를 다시 호출하지 않습니다. (double-dispatch 방지)
        """
        prompt = f"[System] {self.persona}\n[Request] {message.content}"
        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response["message"]["content"]
        print(f"[Writer] 작성 완료 ({len(answer)}자)")
        return answer
