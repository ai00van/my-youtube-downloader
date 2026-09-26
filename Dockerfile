FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 기본 프로그램 설치
RUN apt-get update && \
    apt-get install -y \
    curl \
    git \
    ffmpeg \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Node.js 22 설치
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get update && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# 작업 폴더
WORKDIR /app

# Python 패키지 설치
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# bgutil POT Provider 설치
RUN git clone --depth 1 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    /app/bgutil

WORKDIR /app/bgutil/server

RUN npm install
RUN npx tsc

# 다시 앱 폴더로
WORKDIR /app

# FastAPI 앱 복사
COPY app.py .

# 다운로드 폴더
RUN mkdir -p /app/downloads

# Node.js를 yt-dlp JS 런타임으로 사용
ENV YTDLP_JS_RUNTIME=node

# 서버 시작
CMD ["sh", "-c", "node /app/bgutil/server/build/main.js & sleep 5 && python app.py"]
