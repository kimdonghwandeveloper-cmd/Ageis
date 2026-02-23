import ollama
import json
from config import MODEL_NAME

CLASSIFIER_PROMPT = """You are a routing classifier. Read the user input and return exactly ONE category word.

CATEGORIES:
- CHAT    : General conversation, knowledge questions, explanations. No files or internet needed.
- FILE    : Any mention of files, folders, directories — reading, writing, listing, organizing, deleting.
- WEB     : Needs current/real-time information, web search, or scraping a URL.
- TASK    : Multi-step work combining tools (e.g. search then save, analyze then report).
- PERSONA : Changing the agent's name, personality, tone, or rules.
- VISION  : Analyzing an image or photo.
- VOICE   : Microphone recording or voice commands.
- SCHEDULE: Scheduling a task at a time (cron), or managing schedules.
- SOCIETY : Deep research or report writing requiring multiple specialized agents.

KEY RULES:
- If the user mentions ANY file, folder, or path → FILE or TASK (not CHAT)
- If vague but implies doing something with files → FILE
- If it needs both web + file, or multiple steps → TASK
- If it's about current events, news, prices, trends → WEB or TASK
- When in doubt between FILE and TASK → TASK

EXAMPLES:
"안녕" → CHAT
"파이썬이 뭐야" → CHAT
"내 이름을 Aria로 바꿔줘" → PERSONA
"바탕화면에 뭐가 있어" → FILE
"다운로드 폴더 정리해줘" → FILE
"문서 폴더에 있는 파일들 좀 봐줘" → FILE
"report.txt 읽어줘" → FILE
"메모 하나 만들어줘" → FILE
"오늘 날씨 어때" → WEB
"최신 뉴스 알려줘" → WEB
"AI 트렌드 검색해서 파일로 저장해줘" → TASK
"뉴스 요약해서 바탕화면에 저장해" → TASK
"매일 오전 9시에 뉴스 요약해줘" → SCHEDULE
"AI 트렌드 심층 분석 보고서 써줘" → SOCIETY

User input: {user_input}
Category:"""

def classify_intent(user_input: str) -> str:
    """
    사용자의 입력을 분석하여 의도(Category)를 반환합니다.
    """
    try:
        response = ollama.generate(
            model=MODEL_NAME,
            prompt=CLASSIFIER_PROMPT.format(user_input=user_input),
            options={
                "temperature": 0.0,  # 결정적인(deterministic) 결과를 위해 0 설정
                "num_predict": 10    # 짧은 단어 하나만 나오도록 제한
            }
        )
        category = response['response'].strip().upper()

        # 유효한 카테고리인지 1차 검증 (필수는 아니지만 안전장치)
        valid_categories = {"CHAT", "FILE", "WEB", "TASK", "PERSONA", "VISION", "VOICE", "SCHEDULE", "SOCIETY"}

        # 때때로 LLM이 설명과 함께 답할 수 있으므로, 키워드 포함 여부로 보정
        for valid in valid_categories:
            if valid in category:
                return valid

        return "CHAT"  # 기본값

    except Exception as e:
        print(f"[Router Error] Failed to classify intent: {e}")
        return "CHAT"  # 에러 시 안전하게 일반 대화로 처리
