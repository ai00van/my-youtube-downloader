FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y curl git ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN git clone --depth 1 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    /app/bgutil

WORKDIR /app/bgutil/server

RUN npm install

RUN npx tsc

WORKDIR /app

COPY app.py .

RUN mkdir -p /app/downloads

CMD ["sh", "-c", "node /app/bgutil/server/build/main.js & sleep 3 && python app.py"]
