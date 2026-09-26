import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response

app = FastAPI()

LOCAL_SERVER = os.environ.get(
    "LOCAL_SERVER",
    https://sunglasses-planes-honolulu-toll.trycloudflare.com
)


@app.get("/", response_class=HTMLResponse)
async def home():
    async with httpx.AsyncClient() as client:
        r = await client.get(LOCAL_SERVER)
        return HTMLResponse(
            content=r.text,
            status_code=r.status_code
        )


@app.api_route(
    "/api/download",
    methods=["POST"]
)
async def download(request: Request):

    body = await request.body()

    async with httpx.AsyncClient(timeout=None) as client:

        r = await client.post(
            f"{LOCAL_SERVER}/api/download",
            content=body,
            headers={
                "Content-Type": "application/json"
            }
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
                r.headers.get(
                    "content-disposition",
                    ""
                )
        }
    )
