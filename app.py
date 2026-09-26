import json
import shutil
import uuid
from pathlib import Path
from urllib.parse import quote

import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field


app = FastAPI(title="YouTube 통합 다운로드 서버")


DOWNLOAD_ROOT = Path("/app/downloads")
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DownloadRequest(BaseModel):
    url: str = Field(..., min_length=1)
    format: str = Field(default="video")


def cleanup_directory(directory: Path) -> None:
    if not directory.exists():
        return

    try:
        shutil.rmtree(directory, ignore_errors=True)
    except Exception:
        pass


def find_downloaded_file(directory: Path) -> Path | None:
    if not directory.exists():
        return None

    files = []

    for pattern in (
        "*.mp4",
        "*.webm",
        "*.mkv",
        "*.mp3",
        "*.m4a",
        "*.opus",
    ):
        files.extend(directory.glob(pattern))

    if not files:
        return None

    files.sort(
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    return files[0]


@app.get("/", response_class=HTMLResponse)
async def home():
    html = """<!DOCTYPE html>
<html lang="ko">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <meta
        http-equiv="Cache-Control"
        content="no-cache, no-store, must-revalidate"
    >

    <meta
        http-equiv="Pragma"
        content="no-cache"
    >

    <meta
        http-equiv="Expires"
        content="0"
    >

    <title>YouTube 다운로드</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 30px 15px;
            background: #f5f5f5;
            font-family: Arial, sans-serif;
        }

        .container {
            width: 100%;
            max-width: 700px;
            margin: 0 auto;
            padding: 30px;
            background: #ffffff;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
        }

        h1 {
            margin: 0 0 25px;
            text-align: center;
        }

        input,
        select,
        button {
            width: 100%;
            padding: 14px;
            margin-top: 12px;
            border-radius: 8px;
            border: 1px solid #cccccc;
            font-size: 16px;
        }

        button {
            border: none;
            background: #111111;
            color: #ffffff;
            cursor: pointer;
        }

        button:hover {
            background: #333333;
        }

        button:disabled {
            background: #999999;
            cursor: not-allowed;
        }

        #status {
            margin-top: 20px;
            padding: 15px;
            background: #f1f1f1;
            border-radius: 8px;
            white-space: pre-wrap;
            word-break: break-word;
            min-height: 50px;
        }

        .download-link {
            display: block;
            margin-top: 15px;
            padding: 14px;
            text-align: center;
            background: #198754;
            color: #ffffff;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
        }

        .download-link:hover {
            background: #157347;
        }

        .error {
            color: #b00020;
        }

        .success {
            color: #146c43;
        }
    </style>
</head>

<body>

<div class="container">

    <h1>YouTube 다운로드</h1>

    <input
        id="url"
        type="url"
        placeholder="YouTube 영상 주소를 입력하세요"
        autocomplete="off"
    >

    <select id="format">
        <option value="video">영상 + 음성</option>
        <option value="audio">음성만</option>
    </select>

    <button
        id="downloadButton"
        type="button"
    >
        다운로드
    </button>

    <div id="status">대기 중</div>

</div>


<script>
"use strict";

document.addEventListener("DOMContentLoaded", function () {

    const urlInput = document.getElementById("url");
    const formatSelect = document.getElementById("format");
    const downloadButton = document.getElementById("downloadButton");
    const statusBox = document.getElementById("status");

    console.log("YouTube 다운로드 페이지 로드 완료");

    if (!urlInput || !formatSelect || !downloadButton || !statusBox) {
        console.error("HTML 요소를 찾을 수 없습니다.");
        return;
    }

    async function downloadVideo() {

        console.log("다운로드 버튼 클릭");

        const url = urlInput.value.trim();
        const format = formatSelect.value;

        if (!url) {
            statusBox.className = "error";
            statusBox.textContent = "YouTube 주소를 입력해주세요.";
            urlInput.focus();
            return;
        }

        if (
            !url.startsWith("http://") &&
            !url.startsWith("https://")
        ) {
            statusBox.className = "error";
            statusBox.textContent =
                "올바른 YouTube 주소를 입력해주세요.";
            urlInput.focus();
            return;
        }

        downloadButton.disabled = true;
        downloadButton.textContent = "다운로드 중...";

        statusBox.className = "";
        statusBox.textContent =
            "서버에 다운로드를 요청했습니다.\\n\\n" +
            "영상 크기에 따라 시간이 걸릴 수 있습니다.\\n" +
            "창을 닫지 마세요.";

        try {

            console.log("API 요청 시작");

            const response = await fetch(
                "/api/download",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        url: url,
                        format: format
                    }),
                    cache: "no-store"
                }
            );

            console.log(
                "API 응답:",
                response.status
            );

            const responseText = await response.text();

            console.log(
                "API 응답 내용:",
                responseText
            );

            let data;

            try {
                data = JSON.parse(responseText);
            } catch (e) {
                throw new Error(
                    "서버 응답을 읽을 수 없습니다.\\n" +
                    "HTTP 상태: " +
                    response.status
                );
            }

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "다운로드에 실패했습니다."
                );
            }

            if (!data.download_url) {
                throw new Error(
                    "다운로드 파일 주소가 없습니다."
                );
            }

            statusBox.className = "success";
            statusBox.textContent = "";

            const completeMessage =
                document.createElement("div");

            completeMessage.textContent =
                data.message ||
                "다운로드가 완료되었습니다.";

            statusBox.appendChild(
                completeMessage
            );

            const fileName =
                document.createElement("div");

            fileName.style.marginTop = "8px";
            fileName.textContent =
                data.filename || "";

            statusBox.appendChild(
                fileName
            );

            const link =
                document.createElement("a");

            link.href =
                data.download_url;

            link.textContent =
                "파일 다운로드";

            link.className =
                "download-link";

            link.setAttribute(
                "download",
                ""
            );

            statusBox.appendChild(
                link
            );

            console.log(
                "다운로드 링크 생성 완료:",
                data.download_url
            );

        } catch (error) {

            console.error(
                "다운로드 오류:",
                error
            );

            statusBox.className = "error";

            statusBox.textContent =
                "다운로드 오류가 발생했습니다.\\n\\n" +
                (
                    error &&
                    error.message
                        ? error.message
                        : String(error)
                );

        } finally {

            downloadButton.disabled = false;
            downloadButton.textContent = "다운로드";
        }
    }


    downloadButton.addEventListener(
        "click",
        function (event) {
            event.preventDefault();
            downloadVideo();
        }
    );


    urlInput.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Enter") {

                event.preventDefault();

                downloadVideo();
            }
        }
    );


    console.log(
        "다운로드 버튼 이벤트 연결 완료"
    );

});
</script>

</body>
</html>"""

    response = HTMLResponse(content=html)

    response.headers["Cache-Control"] = (
        "no-cache, no-store, must-revalidate"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "yt_dlp": yt_dlp.version.__version__,
        "bgutil": "configured",
    }


@app.post("/api/download")
async def download_video(
    request: DownloadRequest,
):
    url = request.url.strip()

    if not url:
        raise HTTPException(
            status_code=400,
            detail="YouTube 주소를 입력해주세요.",
        )

    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        raise HTTPException(
            status_code=400,
            detail="올바른 URL을 입력해주세요.",
        )

    if request.format not in (
        "video",
        "audio",
    ):
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 다운로드 형식입니다.",
        )

    job_id = uuid.uuid4().hex

    job_dir = DOWNLOAD_ROOT / job_id

    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_template = str(
        job_dir / "%(title)s.%(ext)s"
    )

    if request.format == "audio":

        ydl_format = "bestaudio/best"

        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    else:

        ydl_format = "bv*+ba/best"

        postprocessors = []

    ydl_opts = {
        "format": ydl_format,

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        "noplaylist": True,

        "quiet": False,

        "no_warnings": False,

        "verbose": True,

        "retries": 3,

        "fragment_retries": 3,

        "continuedl": True,

        "concurrent_fragment_downloads": 1,

        "postprocessors": postprocessors,

        "extractor_args": {
            "youtube": {
                "player_client": [
                    "mweb"
                ]
            },
            "youtubepot-bgutilhttp": {
                "base_url": [
                    "http://127.0.0.1:4416"
                ]
            },
        },

        "js_runtimes": {
            "node": {}
        },
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        downloaded_file = find_downloaded_file(
            job_dir
        )

        if downloaded_file is None:

            raise RuntimeError(
                "다운로드된 파일을 찾을 수 없습니다."
            )

        encoded_filename = quote(
            downloaded_file.name,
            safe=""
        )

        return {
            "success": True,

            "message":
                "다운로드가 완료되었습니다.",

            "filename":
                downloaded_file.name,

            "download_url":
                (
                    "/api/file/"
                    + job_id
                    + "/"
                    + encoded_filename
                ),
        }

    except yt_dlp.utils.DownloadError as exc:

        print(
            "yt-dlp DownloadError:",
            repr(exc)
        )

        cleanup_directory(job_dir)

        raise HTTPException(
            status_code=500,
            detail=(
                "YouTube 다운로드에 실패했습니다. "
                "Render 로그를 확인해주세요."
            ),
        ) from exc

    except Exception as exc:

        print(
            "다운로드 예외:",
            repr(exc)
        )

        cleanup_directory(job_dir)

        raise HTTPException(
            status_code=500,
            detail=(
                f"다운로드 오류: {str(exc)}"
            ),
        ) from exc


@app.get(
    "/api/file/{job_id}/{filename:path}"
)
async def download_file(
    job_id: str,
    filename: str,
):

    safe_job_id = Path(job_id).name

    safe_filename = Path(filename).name

    file_path = (
        DOWNLOAD_ROOT
        / safe_job_id
        / safe_filename
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="파일을 찾을 수 없습니다.",
        )

    if not file_path.is_file():

        raise HTTPException(
            status_code=404,
            detail="파일을 찾을 수 없습니다.",
        )

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )
