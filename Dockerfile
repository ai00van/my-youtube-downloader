FROM python:3.11-slim

# Node.js 22를 별도 이미지에서 가져오기 위한 단계
FROM node:22-bookworm-slim AS node_runtime

# 최종 Python 이미지
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# FFmpeg:
# - 영상 MP4 병합
# - MP3/M4A/WAV/FLAC/OGG 변환
#
# Node.js:
# - yt-dlp JavaScript 처리
# - bgutil POT provider 실행
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22 복사
COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node_runtime /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf /usr/local/lib/node_modules/corepack/dist/corepack.js /usr/local/bin/corepack

# Python 패키지 설치
COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir -r /app/requirements.txt

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

# 다운로드 폴더 생성 및 문법/패키지 검사
RUN mkdir -p /app/downloads \
    && python3 -m py_compile /app/app.py \
    && python3 -c "import yt_dlp; import bgutil_ytdlp_pot_provider; print('yt-dlp:', yt_dlp.version.__version__); print('bgutil plugin: OK')" \
    && node --version \
    && ffmpeg -version | head -n 1

# Render의 PORT 사용
ENV PORT=10000

EXPOSE 10000

# bgutil provider를 먼저 실행하고 FastAPI 실행
CMD ["sh", "-c", "node /opt/bgutil-ytdlp-pot-provider/server/build/main.js --host 127.0.0.1 --port 4416 & exec uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
