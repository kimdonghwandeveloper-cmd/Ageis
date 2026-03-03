# config.py — 모델 및 전역 설정
# 모델 변경 시 이 파일만 수정하면 됩니다.

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

MODEL_NAME = "qwen2.5:3b"
