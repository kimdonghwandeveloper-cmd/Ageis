import ollama
import json
from config import MODEL_NAME

CLASSIFIER_PROMPT = """
당신은 사용자 입력을 분석하여 적절한 파이프라인으로 라우팅하는 분류기입니다.
아래 카테고리 중 하나만 반환하세요:

- CHAT: 일반 대화, 질문, 설명 요청 (파일 읽기나 인터넷 검색이 불필요한 경우)
- FILE: 파일 읽기, 쓰기, 수정 관련 작업이 명시된 경우
- WEB: 웹 검색, URL 크롤링, 실시간 정보 수집이 필요한 경우
- TASK: 여러 도구를 조합해야 하거나 복잡한 단계가 필요한 경우 (예: "검색해서 요약해서 파일로 저장해줘")
- PERSONA: 에이전트 설정 변경 (이름, 말투, 규칙 수정 등)
- VISION: 이미지 분석, 사진 설명, 이미지에 관한 질문 (예: "이 이미지 분석해줘", "사진 설명해줘")
- VOICE: 음성 입력 처리, 마이크 녹음, 음성으로 명령하기 관련 요청
- SCHEDULE: 정해진 시간에 자동으로 태스크 실행, 스케줄 등록/삭제/조회 (예: "매일 오전 9시에 뉴스 요약해줘", "스케줄 목록 보여줘")
- SOCIETY: 여러 전문 에이전트(Researcher, Writer)가 협력해야 하는 복합 조사·작성 태스크 (예: "최신 AI 트렌드 조사해줘", "보고서 작성해줘", "심층 분석해줘")

출력 형식은 오직 카테고리 단어 하나여야 합니다 (예: CHAT). 설명이나 다른 텍스트를 붙이지 마세요.

사용자 입력: {user_input}
카테고리:"""

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
