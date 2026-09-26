FROM node:22-bookworm

ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

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
    --no-cache-dir \
    -r /app/requirements.txt

RUN git clone \
    --depth 1 \
    --branch 2.0.0 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    /opt/bgutil-ytdlp-pot-provider

WORKDIR /opt/bgutil-ytdlp-pot-provider/server

RUN npm ci \
    && npx tsc

WORKDIR /app

COPY app.py /app/app.py

RUN mkdir -p /app/downloads

EXPOSE 8000

CMD ["sh", "-c", "node /opt/bgutil-ytdlp-pot-provider/server/build/main.js --host 127.0.0.1 --port 4416 & exec python3 -m uvicorn app:app --host 0.0.0.0 --port 8000"]
