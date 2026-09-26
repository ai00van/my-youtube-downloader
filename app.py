import os

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response

app = FastAPI()

# PC의 Quick Tunnel이 알려주는 현재 주소
LOCAL_SERVER = ""

# PC와 Render 사이에서 주소 변경 요청을 인증하기 위한 키
UPDATE_TOKEN = os.environ.get("UPDATE_TOKEN", "change-this-token")


@app.get("/", response_class=HTMLResponse)
async def home():
    if not LOCAL_SERVER:
        return HTMLResponse(
            "<h2>서버 연결 대기 중...</h2>",
            status_code=503
        )

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(LOCAL_SERVER)

    return HTMLResponse(
        content=r.text,
        status_code=r.status_code
    )


@app.post("/api/update-server")
async def update_server(request: Request):
    global LOCAL_SERVER

    token = request.headers.get("X-Update-Token")
    if token != UPDATE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

    body = await request.json()
    new_server = str(body.get("url", "")).strip().rstrip("/")

    if not new_server.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid server URL")

    if not new_server.endswith(".trycloudflare.com"):
        raise HTTPException(status_code=400, detail="Only Quick Tunnel URL is allowed")

    LOCAL_SERVER = new_server

    return {
        "success": True,
        "server": LOCAL_SERVER
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "local_server": LOCAL_SERVER
    }


@app.api_route("/api/download", methods=["POST"])
async def download(request: Request):
    if not LOCAL_SERVER:
        raise HTTPException(status_code=503, detail="Local server is not connected")

    body = await request.body()

    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.post(
            f"{LOCAL_SERVER}/api/download",
            content=body,
            headers={"Content-Type": "application/json"}
        )

    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get(
            "content-type",
            "application/json"
        )
    )


@app.get("/api/file/{job_id}/{filename:path}")
async def file(job_id: str, filename: str):
    if not LOCAL_SERVER:
        raise HTTPException(status_code=503, detail="Local server is not connected")

    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.get(
            f"{LOCAL_SERVER}/api/file/{job_id}/{filename}"
        )

    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get(
            "content-type",
            "application/octet-stream"
        ),
        headers={
            "Content-Disposition":
                r.headers.get("content-disposition", "")
        }
    )
