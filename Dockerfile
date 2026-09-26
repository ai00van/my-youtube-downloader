FROM python:3.11-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        nodejs \
        npm \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install -r /app/requirements.txt

# bgutil-ytdlp-pot-provider 2.0.0 설치
RUN git clone --depth 1 --branch 2.0.0 \
        https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
        /opt/bgutil-ytdlp-pot-provider \
    && cd /opt/bgutil-ytdlp-pot-provider/server \
    && npm ci --omit=dev --no-audit --no-fund \
    && npm ci --no-audit --no-fund \
    && npx tsc \
    && npm prune --omit=dev

# 애플리케이션 복사
COPY app.py /app/app.py

# 다운로드 폴더 생성 및 문법 검사
RUN mkdir -p /app/downloads \
    && python3 -m py_compile /app/app.py \
    && python3 -c "import yt_dlp; print('yt-dlp:', yt_dlp.version.__version__)"

# 포트
EXPOSE 10000

# 서버 실행
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
