# 예제 플러그인: 커스텀 도구
# 이 파일은 자동으로 로드되어 ReAct 에이전트가 사용할 수 있습니다.

TOOL_NAME = "my_custom_tool"
TOOL_DESCRIPTION = "사용자가 정의한 플러그인 도구입니다. 입력받은 내용을 그대로 반환합니다."

def run(args: dict) -> str:
    """
    예제 플러그인 실행 함수
    Args:
        args (dict): 도구 입력값 (예: {"message": "hello"})
    Returns:
        str: 실행 결과
    """
    msg = args.get("message", "No message provided")
    return f"✨ [Plugin Effect] You said: '{msg}' ✨"
