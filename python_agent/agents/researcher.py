import ollama
from actor import AgentActor, AgentMessage
from tools.web_scraper import web_scrape_tool
from tools.file_reader import read_file_tool
from config import MODEL_NAME


class ResearcherAgent(AgentActor):
    """
    조사 전문가 에이전트
    - web_scrape / read_file 도구 사용
    - 팩트 위주의 정보 수집 후 결과 반환
    """

    def __init__(self, name: str = "Researcher"):
        super().__init__(
            name=name,
            persona="당신은 꼼꼼한 조사 전문가입니다. 팩트 기반으로 정보를 수집하고 출처를 명시하세요.",
            tools={"web_scrape": web_scrape_tool, "read_file": read_file_tool},
        )

    def think(self, message: AgentMessage) -> str:
        """
        도구를 활용해 조사하고 결과를 문자열로 반환합니다.
        반환값은 send_message() 호출 체인을 통해 호출자(Manager)에게 전달되므로
        별도로 send_message를 다시 호출하지 않습니다. (double-dispatch 방지)
        """
        # 1단계: 도구 사용 여부 결정
        prompt_plan = f"""[System] {self.persona}
[Request] {message.content}

사용 가능한 도구: web_scrape(url), read_file(path)
도구를 사용해야 하면 다음 형식으로 응답하세요:
  TOOL: web_scrape
  INPUT: <URL>
도구가 불필요하면 바로 답변을 작성하세요."""

        plan_response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt_plan}],
        )
        plan_text = plan_response["message"]["content"]

        # 도구 호출 파싱
        tool_result = ""
        if "TOOL: web_scrape" in plan_text:
            lines = plan_text.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("INPUT:") and i > 0:
                    url = line.replace("INPUT:", "").strip()
                    tool_result = self.tools["web_scrape"]({"url": url})
                    print(f"[Researcher] web_scrape({url!r}) → {len(tool_result)}자")
                    break
        elif "TOOL: read_file" in plan_text:
            lines = plan_text.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("INPUT:") and i > 0:
                    path = line.replace("INPUT:", "").strip()
                    tool_result = self.tools["read_file"]({"path": path})
                    print(f"[Researcher] read_file({path!r}) → {len(tool_result)}자")
                    break

        # 2단계: 수집 결과를 바탕으로 최종 정리
        if tool_result:
            synthesis_prompt = f"""다음 수집 자료를 바탕으로 '{message.content}' 요청에 답하세요.

[수집 자료]
{tool_result[:2000]}

팩트 위주로 간결하게 정리해주세요."""
            synth = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": synthesis_prompt}],
            )
            answer = synth["message"]["content"]
        else:
            # 도구 없이 LLM 지식 활용
            answer = plan_text

        print(f"[Researcher] 조사 완료 ({len(answer)}자)")
        return answer
