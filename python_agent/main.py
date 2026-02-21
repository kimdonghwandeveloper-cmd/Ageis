"""
main.py — Python 에이전트 진입점

모드:
  (인수 없음)  : Web UI 모드 [기본값] — Tauri 사이드카가 이 방식으로 실행함
  --cli        : Rich CLI 대시보드 모드
"""

import sys
import os
import time
import argparse

# Windows 콘솔 인코딩 UTF-8 강제 (cp949 깨짐 방지)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass




def setup_logging():
    # 로그 파일은 실행 위치에 남김 (디버깅용)
    log_path = os.path.join(os.getcwd(), "sidecar_debug.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sidecar Started.\n")
        f.write(f"Initial CWD: {os.getcwd()}\n")
        f.write(f"Executable: {sys.executable}\n")

def find_and_set_workspace():
    """Workaround for Tauri Sidecar CWD issue."""
    # 후보 경로: 현재, 상위, 상상위, 실행파일 위치 부모
    candidates = [
        os.getcwd(),
        os.path.dirname(os.getcwd()), # ..
        os.path.dirname(os.path.dirname(os.getcwd())), # ../..
        os.path.dirname(sys.executable), # exe folder
    ]
    
    workspace_dir = None
    for path in candidates:
        check_path = os.path.join(path, "Agent_Workspace")
        if os.path.exists(check_path) and os.path.isdir(check_path):
            workspace_dir = path
            break
            
    if workspace_dir:
        os.chdir(workspace_dir)
        # 로그에 변경된 경로 기록
        try:
            with open("sidecar_debug.log", "a", encoding="utf-8") as f:
                f.write(f"Workspace Found. Changed CWD to: {os.getcwd()}\n")
        except:
            pass
    else:
        # 못 찾으면 그냥 둠 (하지만 로그 남김)
        try:
            with open("sidecar_debug.log", "a", encoding="utf-8") as f:
                f.write(f"WARNING: Agent_Workspace not found in candidates.\n")
        except:
            pass

def main():
    setup_logging()
    find_and_set_workspace()
    parser = argparse.ArgumentParser(description="Ageis AI Agent")
    parser.add_argument("--cli", action="store_true", help="Rich CLI 대시보드 모드로 실행")
    args = parser.parse_args()

    if args.cli:
        from cli import cli_main
        cli_main()
    else:
        # 기본값: Web UI 모드 (Tauri 사이드카는 인수 없이 실행)
        from web_ui import web_main
        web_main()


if __name__ == "__main__":
    main()
