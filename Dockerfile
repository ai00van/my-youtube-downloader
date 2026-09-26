FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ffmpeg \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install \
        --break-system-packages \
        -r /app/requirements.txt

RUN git clone \
        --depth 1 \
        --branch 2.0.0 \
        https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
        /opt/bgutil-ytdlp-pot-provider \
    && cd /opt/bgutil-ytdlp-pot-provider/server \
    && npm ci --no-audit --no-fund \
    && npx tsc

COPY app.py /app/app.py

RUN mkdir -p /app/downloads

RUN python3 -m py_compile /app/app.py \
    && python3 -c "import yt_dlp; print('yt-dlp:', yt_dlp.version.__version__)" \
    && test -f /opt/bgutil-ytdlp-pot-provider/server/build/main.js

EXPOSE 10000

CMD ["sh", "-c", "node /opt/bgutil-ytdlp-pot-provider/server/build/main.js --host 127.0.0.1 --port 4416 & exec python3 -m uvicorn app:app --host 0.0.0.0 --port 10000"]
