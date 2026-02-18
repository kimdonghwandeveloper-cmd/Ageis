import json
import re
import ollama
from datetime import datetime

MAX_ITERATIONS = 10

REACT_SYSTEM_PROMPT = """
당신은 도구를 사용하여 사용자의 요청을 수행하는 지능형 에이전트입니다.
사용 가능한 도구는 다음과 같습니다:

{tool_descriptions}

문제를 해결하기 위해 다음 형식을 엄격히 따르십시오:

Thought: [현재 상황을 분석하고 다음에 무엇을 해야 할지 생각]
Action: [실행할 도구의 이름]
Action Input: [도구에 전달할 JSON 형식의 입력값]
Observation: [도구 실행 결과]
... (필요한 만큼 Thought/Action/Observation 반복)
Final Answer: [사용자에게 전달할 최종 답변]

알 수 없는 도구를 사용하지 마십시오.
모든 Action Input은 반드시 유효한 JSON 형식이어야 합니다.
Final Answer를 찾았다면 더 이상 Action을 생성하지 마십시오.
"""

class ReActAgent:
    def __init__(self, tools: dict, model_name: str = "llama3.2", memory=None):
        self.tools = tools          # {"tool_name": function}
        self.model_name = model_name
        self.memory = memory        # AgentMemory 인스턴스 (Phase 3)
        self.history = []

        # 도구 설명 문자열 생성 (프롬프트 주입용)
        self.tool_desc_str = self._generate_tool_descriptions()

    def _generate_tool_descriptions(self) -> str:
        desc = []
        for name, func in self.tools.items():
            # docstring의 첫 줄이나 전체를 설명으로 사용
            doc = func.__doc__.strip() if func.__doc__ else "No description."
            desc.append(f"- {name}: {doc}")
        return "\n".join(desc)

    def run(self, task: str) -> str:
        """사용자 태스크를 받아 ReAct 루프를 실행하고 최종 답변을 반환합니다."""
        print(f"\n[ReAct] Task started: {task}")

        # 시스템 프롬프트 구성: 페르소나+기억 + 도구 설명 결합
        react_prompt = REACT_SYSTEM_PROMPT.format(tool_descriptions=self.tool_desc_str)

        if self.memory:
            from persona import build_system_prompt
            persona_prompt = build_system_prompt(task, self.memory)
            system_prompt = persona_prompt + "\n\n" + react_prompt
        else:
            system_prompt = react_prompt

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task}"}
        ]
        
        for iteration in range(MAX_ITERATIONS):
            print(f"[ReAct] Iteration {iteration + 1}...")
            
            # 1. LLM 호출
            response = ollama.chat(model=self.model_name, messages=messages)
            output = response["message"]["content"]
            
            print(f"[ReAct] LLM Output:\n{output}\n")
            
            # 대화 기록에 추가 (Assistant의 응답)
            messages.append({"role": "assistant", "content": output})

            # 2. Final Answer 확인
            if "Final Answer:" in output:
                final_answer = output.split("Final Answer:")[-1].strip()
                # Phase 3: 대화 내용을 장기 기억에 저장
                if self.memory:
                    self.memory.save(
                        f"[Task] {task}\n[Answer] {final_answer}",
                        metadata={"type": "task", "timestamp": datetime.now().isoformat()}
                    )
                return final_answer

            # 3. Action 파싱
            action, action_input = self._parse_action(output)
            
            if action:
                # 4. 도구 실행
                if action in self.tools:
                    print(f"[ReAct] Executing Tool: {action} with input {action_input}")
                    try:
                        observation = self.tools[action](action_input)
                    except Exception as e:
                        observation = f"Tool execution error: {e}"
                else:
                    observation = f"Error: Tool '{action}' not found. Available tools: {list(self.tools.keys())}"
                
                print(f"[ReAct] Observation: {observation[:200]}..." if len(observation) > 200 else f"[ReAct] Observation: {observation}")

                # 5. Observation을 User 역할로 메시지에 추가 (Self-Correction 유도)
                obs_message = f"Observation: {observation}"
                messages.append({"role": "user", "content": obs_message})
            else:
                # Action을 찾지 못했지만 Final Answer도 없는 경우
                # (LLM이 형식에 맞지 않는 말을 했을 때)
                if iteration == MAX_ITERATIONS - 1:
                    break
                # 계속 진행하도록 유도
                messages.append({"role": "user", "content": "Observation: 형식을 지켜주세요. Action과 Action Input을 명시하거나 Final Answer를 내놓으세요."})

        return "최대 반복 횟수에 도달했습니다. 작업을 완료하지 못했을 수 있습니다."

    def _parse_action(self, text: str) -> tuple:
        """
        LLM 출력에서 Action과 Action Input을 추출합니다.
        정규식 또는 문자열 파싱 사용
        """
        # Action: 찾기
        action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", text)
        
        # Action Input: 찾기 (JSON 객체 { ... })
        # re.DOTALL: .이 개행 문자도 매칭하도록
        input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL)
        
        action = action_match.group(1).strip() if action_match else None
        action_input = {}
        
        if input_match:
            try:
                # JSON 파싱 시도
                json_str = input_match.group(1)
                # 흔한 JSON 오류 수정 시도 (작은 따옴표 -> 큰 따옴표 등은 복잡하므로 패스하거나 간단히 처리)
                action_input = json.loads(json_str)
            except json.JSONDecodeError:
                print("[ReAct] JSON Decode Error inside Action Input")
                action_input = {}
        
        return action, action_input
