import shutil
import uuid
from pathlib import Path

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
    allow_credentials=True,
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
    return """<!DOCTYPE html>
<html lang="ko">

<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
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
        }

        .download-link:hover {
            background: #157347;
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

    <div id="status">
        대기 중
    </div>

</div>


<script>
(function () {

    "use strict";


    const urlElement =
        document.getElementById("url");

    const formatElement =
        document.getElementById("format");

    const button =
        document.getElementById("downloadButton");

    const status =
        document.getElementById("status");


    if (
        !urlElement ||
        !formatElement ||
        !button ||
        !status
    ) {
        console.error(
            "필수 HTML 요소를 찾을 수 없습니다."
        );

        return;
    }


    async function downloadVideo() {

        const url =
            urlElement.value.trim();

        const format =
            formatElement.value;


        if (!url) {

            status.textContent =
                "YouTube 주소를 입력해주세요.";

            urlElement.focus();

            return;
        }


        if (
            !url.startsWith("http://") &&
            !url.startsWith("https://")
        ) {

            status.textContent =
                "올바른 YouTube 주소를 입력해주세요.";

            urlElement.focus();

            return;
        }


        button.disabled = true;

        button.textContent =
            "다운로드 중...";


        status.textContent =
            "다운로드를 준비하고 있습니다.\n" +
            "잠시 기다려주세요.";


        try {

            const response =
                await fetch(
                    "/api/download",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            url: url,
                            format: format
                        })
                    }
                );


            let data;


            try {

                data =
                    await response.json();

            } catch (jsonError) {

                throw new Error(
                    "서버에서 올바른 응답을 받지 못했습니다."
                );
            }


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "다운로드에 실패했습니다."
                );
            }


            status.innerHTML = "";


            const message =
                document.createElement("div");


            message.textContent =
                data.message ||
                "다운로드가 완료되었습니다.";


            status.appendChild(message);


            if (data.download_url) {

                const link =
                    document.createElement("a");


                link.href =
                    data.download_url;


                link.textContent =
                    "파일 다운로드";


                link.className =
                    "download-link";


                link.download = "";


                link.target = "_blank";


                link.rel =
                    "noopener noreferrer";


                status.appendChild(link);

            } else {

                const message2 =
                    document.createElement("div");


                message2.style.marginTop =
                    "10px";


                message2.textContent =
                    "다운로드 파일 주소를 받지 못했습니다.";


                status.appendChild(message2);
            }


        } catch (error) {

            console.error(
                "다운로드 오류:",
                error
            );


            status.textContent =
                "다운로드 오류가 발생했습니다.\n\n" +
                (
                    error &&
                    error.message
                        ? error.message
                        : String(error)
                );

        } finally {

            button.disabled = false;

            button.textContent =
                "다운로드";
        }
    }


    button.addEventListener(
        "click",
        downloadVideo
    );


    urlElement.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter"
            ) {

                event.preventDefault();

                downloadVideo();
            }
        }
    );


    console.log(
        "YouTube 다운로드 JavaScript 정상 로드"
    );

})();
</script>

</body>
</html>"""


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
                "key":
                    "FFmpegExtractAudio",

                "preferredcodec":
                    "mp3",

                "preferredquality":
                    "192",
            }
        ]

    else:

        ydl_format = "bv*+ba/best"

        postprocessors = []


    ydl_opts = {

        "format":
            ydl_format,

        "outtmpl":
            output_template,

        "merge_output_format":
            "mp4",

        "noplaylist":
            True,

        "quiet":
            False,

        "no_warnings":
            False,

        "verbose":
            True,

        "retries":
            3,

        "fragment_retries":
            3,

        "continuedl":
            True,

        "concurrent_fragment_downloads":
            1,

        "postprocessors":
            postprocessors,

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
            }
        },

        "js_runtimes": {
            "node": {}
        }
    }


    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([url])


        downloaded_file = find_downloaded_file(
            job_dir
        )


        if downloaded_file is None:

            raise RuntimeError(
                "다운로드된 파일을 찾을 수 없습니다."
            )


        return {
            "success":
                True,

            "message":
                "다운로드가 완료되었습니다.",

            "filename":
                downloaded_file.name,

            "download_url":
                (
                    f"/api/file/"
                    f"{job_id}/"
                    f"{downloaded_file.name}"
                ),
        }


    except yt_dlp.utils.DownloadError as exc:

        cleanup_directory(
            job_dir
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "YouTube 다운로드에 실패했습니다. "
                "Render 로그를 확인해주세요."
            ),
        ) from exc


    except Exception as exc:

        cleanup_directory(
            job_dir
        )


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
    )
