# Python 3.11 슬림 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (음성 인식/합성 및 빌드 도구를 위함)
# Windows 데스크톱 네이티브 의존성(pyttsx3, sounddevice 등)의 리눅스 호환을 위한 라이브러리들
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    espeak \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 빠르고 가벼운 패키지 매니저 uv 설치
RUN pip install --no-cache-dir uv

# 프로젝트 패키지 설정 파일 복사
COPY pyproject.toml uv.lock ./

# uv를 사용하여 سیستم 레벨(-system)에 패키지 설치
RUN uv pip install --system -r pyproject.toml

# 에이전트 소스코드 및 웹 UI HTML 복사
COPY python_agent/ ./python_agent/
COPY desktop/index.html ./desktop/index.html

# 작업 결과물이 저장될 볼륨 마운트 준비
RUN mkdir -p /app/Agent_Workspace

# 외부 포트 연결
EXPOSE 8000

# Ollama가 로컬이 아닌 Docker 네트워크(ollama 컨테이너)를 보도록 환경변수 설정
ENV OLLAMA_HOST=http://ollama:11434

# 파이썬 웹 백엔드 실행
CMD ["python", "python_agent/web_ui.py"]
