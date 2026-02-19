"""
main.py — Python 에이전트 진입점

모드:
  (인수 없음)  : Web UI 모드 [기본값] — Tauri 사이드카가 이 방식으로 실행함
  --cli        : Rich CLI 대시보드 모드
"""

import sys
import argparse

# Windows 콘솔 인코딩 UTF-8 강제 (cp949 깨짐 방지)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def main():
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
