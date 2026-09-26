```sh
#!/bin/sh
set -eu

echo "=== Starting application ==="

# 1. YouTube cookies
if [ -n "${YTDLP_COOKIES:-}" ]; then
    printf '%s\n' "$YTDLP_COOKIES" > /app/cookies.txt
    echo "[start.sh] cookies.txt 생성 완료"
else
    echo "[start.sh] WARNING: YTDLP_COOKIES가 설정되지 않았습니다."
fi


# 2. Start bgutil PO Token provider
echo "[start.sh] bgutil 시작..."

node /opt/bgutil/build/main.js \
    --host 127.0.0.1 \
    --port 4416 &

BGUTIL_PID=$!

echo "[start.sh] bgutil PID: $BGUTIL_PID"

# bgutil 초기화 대기
sleep 20

# bgutil 프로세스 확인
if ! kill -0 "$BGUTIL_PID" 2>/dev/null; then
    echo "[start.sh] ERROR: bgutil 프로세스가 종료되었습니다."
    exit 1
fi

echo "[start.sh] bgutil 실행 확인"


# 3. Start API server
PORT="${PORT:-10000}"

echo "[start.sh] API 서버 시작: port $PORT"

exec python3 -m uvicorn app:app \
    --host 0.0.0.0 \
    --port "$PORT"
```
