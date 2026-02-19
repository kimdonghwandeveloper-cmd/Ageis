from actor import AgentActor, AgentMessage
import ollama
import json

class ManagerAgent(AgentActor):
    """
    관리자 에이전트 (Brain)
    - 사용자 입력을 분석하여 하위 에이전트(Researcher, Writer)에게 위임
    - 작업 결과를 취합하여 최종 답변 생성
    """
    def __init__(self, name="Manager"):
        super().__init__(
            name=name,
            persona="당신은 관리자입니다. 직접 일하지 말고 전문가에게 지시하세요. Researcher에게 조사를, Writer에게 작성을 맡길 수 있습니다."
        )
        self.pending_tasks = {}  # context_id -> original_user_message

    def think(self, message: AgentMessage) -> str:
        """
        1. 사용자 요청(REQUEST)이면 -> 작업 분배 (DELEGATE) 및 결과 대기
        2. 하위 에이전트 응답(RESPONSE)이면 -> 결과 반환
        """
        
        # 하위 에이전트가 보낸 응답은 receive_message를 통해 여기가 아닌
        # send_message의 반환값으로 처리되므로, 여기서는 RESPONSE 메시지가 직접 들어올 일은 드묾
        # (단, 비동기 호출 시에는 중요할 수 있음)
        if message.msg_type == "RESPONSE":
            print(f"[Manager] Received report from {message.sender}")
            return f"[{message.sender} 보고]: {message.content}"

        # 사용자 요청 처리
        prompt = f"""
        [System] {self.persona}
        [Request] {message.content}
        
        다음 형식의 JSON으로 응답하세요:
        {{
            "action": "DELEGATE" | "ANSWER",
            "target": "Researcher" | "Writer" | "None",
            "instruction": "하위 에이전트에게 내릴 지시 사항"
        }}
        """
        
        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt, "format": "json"}]
        )
        
        try:
            plan = json.loads(response["message"]["content"])
            
            if plan.get("action") == "DELEGATE":
                target = plan.get("target")
                instruction = plan.get("instruction")
                
                print(f"[Manager] {target}에게 위임 중: {instruction}")
                
                # 동기식 호출: 결과가 바로 돌아옴
                result = self.send_message(
                    recipient_name=target,
                    content=instruction,
                    msg_type="REQUEST",
                    context_id=message.context_id
                )
                
                # 결과를 받아서 사용자에게 최종 보고
                return f"[Manager] {target}에게 지시하여 다음 결과를 얻었습니다:\n\n{result}"
            
            else:
                return plan.get("instruction", "직접 답변합니다.")

        except json.JSONDecodeError:
            return "계획 수립에 실패했습니다."
