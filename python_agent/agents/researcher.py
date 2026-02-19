from actor import AgentActor, AgentMessage
from tools.web_scraper import web_scrape_tool
from tools.file_reader import read_file_tool
import ollama

class ResearcherAgent(AgentActor):
    """
    조사 전문가 에이전트
    - 웹 검색 및 파일 읽기 도구 사용
    - 팩트 위주의 정보 수집
    """
    def __init__(self, name="Researcher"):
        super().__init__(
            name=name,
            persona="당신은 꼼꼼한 조사 전문가입니다. 팩트 기반으로 정보를 수집하고 출처를 명시하세요.",
            tools={"web_scrape": web_scrape_tool, "read_file": read_file_tool}
        )

    def think(self, message: AgentMessage) -> str:
        """
        메시지를 받으면 도구를 사용하여 정보를 찾고 결과를 반환
        (여기서는 간단히 LLM + Tool 직접 호출 흐름 구현)
        """
        prompt = f"""
        [System] {self.persona}
        [Request] {message.content}
        
        필요하다면 제공된 도구(web_scrape, read_file)를 사용할 수 있다고 가정하고,
        지금은 간단히 LLM의 지식을 활용해 답변하거나 도구 사용 계획을 말해주세요.
        """
        
        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}]
        )
        
        answer = response["message"]["content"]
        
        # 결과를 요청자에게 회신
        if message.sender != "User":  # User는 직접 회신 불가 (main loop에서 처리)
            self.send_message(
                recipient_name=message.sender,
                content=answer,
                msg_type="RESPONSE",
                context_id=message.context_id
            )
        
        return answer
