FROM node:26-bookworm-slim AS bgutil-builder

USER node

WORKDIR /app

RUN git clone --depth 1 --branch 2.0.0 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    /tmp/bgutil

WORKDIR /tmp/bgutil/server

RUN npm ci --no-audit --no-fund

RUN npx tsc


FROM node:26-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ffmpeg \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=bgutil-builder \
    /tmp/bgutil/server/build \
    /opt/bgutil/build

COPY --from=bgutil-builder \
    /tmp/bgutil/server/node_modules \
    /opt/bgutil/node_modules

COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install \
    --break-system-packages \
    --no-cache-dir \
    -r /app/requirements.txt

COPY app.py /app/app.py

RUN mkdir -p /app/downloads

EXPOSE 4416

CMD ["sh", "-c", "node /opt/bgutil/build/main.js --host 127.0.0.1 --port 4416 & exec python3 -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
