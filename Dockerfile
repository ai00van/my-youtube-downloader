FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Python + FFmpeg + Git 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ffmpeg \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install \
        --break-system-packages \
        -r /app/requirements.txt

# bgutil-ytdlp-pot-provider 2.0.0 설치
RUN git clone \
        --depth 1 \
        --branch 2.0.0 \
        https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
        /opt/bgutil-ytdlp-pot-provider \
    && cd /opt/bgutil-ytdlp-pot-provider/server \
    && npm ci --no-audit --no-fund \
    && npx tsc

# 애플리케이션 복사
COPY app.py /app/app.py

# 다운로드 폴더 생성
RUN mkdir -p /app/downloads

# app.py 문법 검사 + 패키지 검사 + bgutil 빌드 확인
RUN python3 -m py_compile /app/app.py \
    && python3 -c "import yt_dlp; print('yt-dlp:', yt_dlp.version.__version__)" \
    && test -f /opt/bgutil-ytdlp-pot-provider/server/build/main.js

# 포트
EXPOSE 10000

# bgutil 서버를 먼저 실행한 후 FastAPI 실행
CMD ["sh", "-c", "node /opt/bgutil-ytdlp-pot-provider/server/build/main.js --host 127.0.0.1 --port 4416 & exec python3 -m uvicorn app:app --host 0.0.0.0 --port 10000"]
