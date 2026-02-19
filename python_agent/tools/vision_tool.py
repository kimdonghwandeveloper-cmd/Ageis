"""
vision_tool.py — Phase 6-A: 이미지 분석 도구 (llava 모델 사용)

사용법:
  - 이미지 파일 경로 또는 base64 인코딩 문자열을 받아 ollama llava 모델로 분석
  - ReAct 루프에서 "vision_analyze" 도구로 호출 가능
"""
import base64
import os
import ollama

VISION_MODEL = "llava"  # ollama pull llava 필요


def _load_image_as_base64(path: str) -> str:
    """이미지 파일을 base64 문자열로 변환"""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image_tool(args: dict) -> str:
    """
    이미지를 분석하여 텍스트 설명을 반환합니다.

    args:
        path (str): 이미지 파일 경로 (선택)
        base64_image (str): base64 인코딩된 이미지 데이터 (선택)
        prompt (str): 분석 질문 (기본값: "이 이미지에 무엇이 있나요? 자세히 설명해주세요.")
    """
    prompt = args.get("prompt", "이 이미지에 무엇이 있나요? 자세히 설명해주세요.")
    image_path = args.get("path", "")
    b64_data = args.get("base64_image", "")

    if not image_path and not b64_data:
        return "ERROR: 이미지 경로(path) 또는 base64 데이터(base64_image)를 제공해야 합니다."

    try:
        if image_path:
            if not os.path.isfile(image_path):
                return f"ERROR: 파일을 찾을 수 없습니다: {image_path}"
            b64_data = _load_image_as_base64(image_path)

        response = ollama.chat(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64_data],
                }
            ],
        )
        return response["message"]["content"]

    except Exception as e:
        return f"ERROR: 이미지 분석 실패 — {e}"
