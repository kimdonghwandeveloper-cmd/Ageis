import json
import ollama
from actor import AgentActor, AgentMessage


class ManagerAgent(AgentActor):
    """
    관리자 에이전트 (Brain)
    - 사용자 입력을 분석하여 하위 에이전트(Researcher, Writer)에게 위임
    - 작업 결과를 취합하여 최종 답변 생성
    """

    def __init__(self, name: str = "Manager"):
        super().__init__(
            name=name,
            persona=(
                "당신은 관리자입니다. 직접 일하지 말고 전문가에게 지시하세요. "
                "Researcher에게 조사를, Writer에게 작성을 맡길 수 있습니다."
            ),
        )

    def think(self, message: AgentMessage) -> str:
        # 하위 에이전트의 RESPONSE — 결과를 그대로 반환 (이미 send_message 반환값으로 처리됨)
        if message.msg_type == "RESPONSE":
            print(f"[Manager] Received report from {message.sender}")
            return message.content

        # 사용자 REQUEST — 위임 대상을 결정
        prompt = f"""[System] {self.persona}
[Request] {message.content}

다음 JSON 형식으로만 응답하세요:
{{
    "action": "DELEGATE" or "ANSWER",
    "target": "Researcher" or "Writer" or "None",
    "instruction": "하위 에이전트에게 내릴 구체적인 지시 사항"
}}"""

        # fix: format은 ollama.chat() 최상위 인자로 전달해야 함
        response = ollama.chat(
            model="llama3.2",
            format="json",
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            plan = json.loads(response["message"]["content"])
        except (json.JSONDecodeError, KeyError):
            return "계획 수립에 실패했습니다."

        action = plan.get("action", "ANSWER")
        target = plan.get("target", "None")
        instruction = plan.get("instruction", message.content)

        if action == "DELEGATE" and target in ("Researcher", "Writer"):
            print(f"[Manager] → {target}에게 위임: {instruction!r}")
            result = self.send_message(
                recipient_name=target,
                content=instruction,
                msg_type="REQUEST",
                context_id=message.context_id,
            )
            return f"[{target} 결과]\n\n{result}"

        # ANSWER — Manager가 직접 답변
        return instruction
