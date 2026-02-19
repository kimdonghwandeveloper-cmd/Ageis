"""
persona.py — 동적 시스템 프롬프트 (페르소나) 모듈

역할:
- persona.yaml 파일에서 에이전트 성격/제약 설정 로드
- RAG 기억 + 페르소나 설정을 결합하여 최종 시스템 프롬프트 생성
"""

import sys
from pathlib import Path
import yaml
from memory import AgentMemory


def _default_persona_path() -> Path:
    """번들(frozen) 여부에 따라 persona.yaml 경로 반환."""
    if getattr(sys, 'frozen', False):
        # exe 옆 Agent_Workspace 우선, 없으면 번들 내장 기본값 사용
        user_path = Path(sys.executable).parent / "Agent_Workspace" / "persona.yaml"
        if user_path.exists():
            return user_path
        return Path(sys._MEIPASS) / "Agent_Workspace" / "persona.yaml"
    return Path(__file__).resolve().parent.parent / "Agent_Workspace" / "persona.yaml"


def load_persona(path: str = None) -> dict:
    """persona.yaml 파일을 읽어 딕셔너리로 반환"""
    resolved = Path(path) if path else _default_persona_path()
    with open(resolved, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_system_prompt(user_query: str, memory: AgentMemory) -> str:
    """페르소나 설정 + RAG 결과를 조합하여 시스템 프롬프트 문자열 반환"""
    persona = load_persona()
    recalled_memories = memory.recall(user_query)
    memories_text = "\n".join(f"- {m}" for m in recalled_memories)

    system_prompt = f"""당신의 이름은 {persona['name']}입니다.
성격: {persona['personality']['description']}
말투: {persona['personality']['tone']} / 언어: {persona['personality']['language']}
상세도: {persona['personality']['verbosity']}

[절대 금지 행동]
{chr(10).join(f"- {r}" for r in persona['restrictions']['absolute_forbidden'])}

[콘텐츠 정책]
{chr(10).join(f"- {r}" for r in persona['restrictions']['content_policy'])}

[관련 기억 (RAG 검색 결과)]
{memories_text if memories_text else "관련 기억 없음"}

위 페르소나와 기억을 바탕으로 사용자 요청에 응답하세요."""

    return system_prompt
