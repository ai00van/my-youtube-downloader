```dockerfile
# ============================================
# Stage 1: Build bgutil PO Token Provider
# ============================================

FROM node:22-bookworm-slim AS bgutil-builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
        build-essential \
        pkg-config \
        python3 \
        libcairo2-dev \
        libpango1.0-dev \
        libjpeg-dev \
        libgif-dev \
        librsvg2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

RUN git clone \
    --depth 1 \
    --branch 2.0.0 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    bgutil

WORKDIR /tmp/bgutil/server

RUN npm ci --no-audit --no-fund

RUN npx tsc


# ============================================
# Stage 2: Runtime
# ============================================

FROM node:22-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Python / ffmpeg / bgutil runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ffmpeg \
        ca-certificates \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libjpeg62-turbo \
        libgif7 \
        librsvg2-2 \
    && rm -rf /var/lib/apt/lists/*


# ============================================
# Application directory
# ============================================

WORKDIR /app


# ============================================
# Copy bgutil
# ============================================

COPY --from=bgutil-builder \
    /tmp/bgutil/server/build \
    /opt/bgutil/build

COPY --from=bgutil-builder \
    /tmp/bgutil/server/node_modules \
    /opt/bgutil/node_modules


# ============================================
# Python dependencies
# ============================================

COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install \
    --break-system-packages \
    --no-cache-dir \
    -r /app/requirements.txt


# ============================================
# Application files
# ============================================

COPY app.py /app/app.py
COPY start.sh /app/start.sh

RUN chmod +x /app/start.sh

RUN mkdir -p /app/downloads


# ============================================
# API port
# ============================================

EXPOSE 10000


# ============================================
# Start
# ============================================

CMD ["/app/start.sh"]
```
