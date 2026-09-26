FROM node:22-bookworm-slim AS bgutil-builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

RUN git clone --depth 1 --branch 2.0.0 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git bgutil

WORKDIR /opt/bgutil/server

RUN npm ci --no-audit --no-fund
RUN npx tsc


FROM node:22-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=bgutil-builder /opt/bgutil/server/build /opt/bgutil/server/build
COPY --from=bgutil-builder /opt/bgutil/server/node_modules /opt/bgutil/server/node_modules
COPY --from=bgutil-builder /opt/bgutil/server/package.json /opt/bgutil/server/package.json

COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install \
    --no-cache-dir \
    --break-system-packages \
    -r /app/requirements.txt

COPY app.py /app/app.py

RUN mkdir -p /app/downloads

CMD ["sh", "-c", "node /opt/bgutil/server/build/main.js --host 127.0.0.1 --port 4416 & exec python3 -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
