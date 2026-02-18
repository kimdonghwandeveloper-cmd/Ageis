import importlib.util
import os
import sys

# 플러그인 디렉토리 설정 (프로젝트 루트 기준)
# python_agent/plugin_loader.py 에서 실행되므로, 
# 상위(..)/Agent_Workspace/plugins 를 가리킴
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
PLUGIN_DIR = os.path.join(PROJECT_ROOT, "Agent_Workspace", "plugins")

def load_plugins() -> dict:
    """
    Agent_Workspace/plugins/ 폴더의 .py 파일을 자동으로 도구로 등록합니다.
    
    Returns:
        dict: {"tool_name": tool_function} 형태의 딕셔너리
    """
    tools = {}
    
    # 플러그인 디렉토리가 없으면 생성 (안전장치)
    if not os.path.exists(PLUGIN_DIR):
        try:
            os.makedirs(PLUGIN_DIR)
        except OSError:
            pass # 생성 실패시 빈 딕셔너리 반환
        return tools

    print(f"[Plugin] Scanning: {PLUGIN_DIR}")

    for filename in os.listdir(PLUGIN_DIR):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
            
        filepath = os.path.join(PLUGIN_DIR, filename)
        module_name = filename[:-3] # .py 제거
        
        try:
            # 동적 모듈 로드
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # 플러그인 규격 확인 (TOOL_NAME, run 함수)
                if hasattr(module, "TOOL_NAME") and hasattr(module, "run"):
                    tool_name = module.TOOL_NAME
                    tool_func = module.run
                    
                    # 도구 설명이 있으면 함수 docstring으로 설정 (ReAct 루프가 사용)
                    if hasattr(module, "TOOL_DESCRIPTION"):
                        tool_func.__doc__ = module.TOOL_DESCRIPTION
                        
                    tools[tool_name] = tool_func
                    print(f"  [+] Loaded Plugin: {tool_name}")
                else:
                    print(f"  [-] Skipped {filename}: Missing TOOL_NAME or run()")
                    
        except Exception as e:
            print(f"  [!] Failed to load {filename}: {e}")
            
    return tools
