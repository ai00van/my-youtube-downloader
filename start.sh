#!/bin/sh
set -eu

echo "=== Starting application ==="

# 1. YouTube cookies 생성
if [ -n "${YTDLP_COOKIES:-}" ]; then
    printf '%s\n' "$YTDLP_COOKIES" > /app/cookies.txt
    echo "[start.sh] cookies.txt 생성 완료"
else
    echo "[start.sh] WARNING: YTDLP_COOKIES가 설정되지 않았습니다."
fi


# 2. bgutil PO Token provider 시작
echo "[start.sh] bgutil 시작..."

node /opt/bgutil/build/main.js \
    --host 127.0.0.1 \
    --port 4416 &

BGUTIL_PID=$!


# 3. bgutil 준비 대기
echo "[start.sh] bgutil 준비 대기 중..."

i=0

while [ "$i" -lt 30 ]; do

    # bgutil 프로세스가 죽었는지 확인
    if ! kill -0 "$BGUTIL_PID" 2>/dev/null; then
        echo "[start.sh] ERROR: bgutil 프로세스가 종료되었습니다."
        exit 1
    fi

    # 4416 포트 확인
    if python3 -c '
import socket
s = socket.socket()
s.settimeout(1)

try:
    s.connect(("127.0.0.1", 4416))
    s.close()
    exit(0)
except:
    exit(1)
'; then
        echo "[start.sh] bgutil 준비 완료 (${i}초)"
        break
    fi

    i=$((i + 1))
    sleep 1
done

if [ "$i" -ge 30 ]; then
    echo "[start.sh] ERROR: bgutil이 30초 안에 시작되지 않았습니다."
    exit 1
fi


# 4. FastAPI 시작
PORT="${PORT:-10000}"

echo "[start.sh] API 서버 시작: port ${PORT}"

exec python3 -m uvicorn app:app \
    --host 0.0.0.0 \
    --port "$PORT"
