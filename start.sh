#!/bin/sh
set -e

# 1) 쿠키: YTDLP_COOKIES 환경변수에 cookies.txt(Netscape 형식) 내용이 들어있으면
#    파일로 기록한다. Render 등에서는 파일 업로드보다 환경변수가 다루기 쉽다.
if [ -n "$YTDLP_COOKIES" ]; then
    printf '%s\n' "$YTDLP_COOKIES" > /app/cookies.txt
    echo "[start.sh] YTDLP_COOKIES 환경변수로부터 /app/cookies.txt 생성 완료"
else
    echo "[start.sh] YTDLP_COOKIES 미설정 - 쿠키 없이 진행 (LOGIN_REQUIRED 위험)"
fi

# 2) bgutil PO Token provider를 백그라운드로 기동
node /opt/bgutil/build/main.js --host 127.0.0.1 --port 4416 &

# 3) bgutil이 실제로 리스닝을 시작할 때까지 최대 30초 대기.
echo "[start.sh] bgutil(127.0.0.1:4416) 준비 대기 중..."
i=0
while [ "$i" -lt 30 ]; do
    if python3 -c "
import socket, sys
s = socket.socket()
s.settimeout(1)
sys.exit(0 if s.connect_ex(('127.0.0.1', 4416)) == 0 else 1)
"; then
        echo "[start.sh] bgutil 준비 완료 (${i}초 후)"
        break
    fi
    i=$((i + 1))
    sleep 1
done

if [ "$i" -eq 30 ]; then
    echo "[start.sh] 경고: 30초 내에 bgutil이 준비되지 않았습니다. 그대로 진행합니다."
fi

# 4) API 서버 기동
exec python3 -m uvicorn app:app --host 0.0.0.0 --port "${PORT:-10000}"
