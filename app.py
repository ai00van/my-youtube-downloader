import glob
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

import yt_dlp


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
    mode: str = "video"
    audio_format: str = "mp3"


HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>YouTube 다운로드</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f5f5f5;
    color: #222;
}

.wrap {
    max-width: 720px;
    margin: 50px auto;
    padding: 24px;
}

.card {
    background: #fff;
    border-radius: 16px;
    padding: 28px;
    box-shadow: 0 5px 24px rgba(0, 0, 0, .08);
}

h1 {
    margin-top: 0;
}

input,
select,
button {
    width: 100%;
    padding: 13px;
    margin-top: 8px;
    border: 1px solid #ccc;
    border-radius: 9px;
    font-size: 15px;
}

button {
    border: 0;
    background: #111;
    color: #fff;
    cursor: pointer;
    font-weight: 700;
}

button:disabled {
    opacity: .5;
    cursor: not-allowed;
}

.row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

.status {
    margin-top: 18px;
    padding: 14px;
    border-radius: 9px;
    background: #f0f0f0;
    white-space: pre-wrap;
}

.hidden {
    display: none;
}

.small {
    font-size: 13px;
    color: #666;
}

@media (max-width: 600px) {
    .row {
        grid-template-columns: 1fr;
    }

    .wrap {
        margin: 15px auto;
        padding: 12px;
    }
}
</style>
</head>

<body>

<div class="wrap">
    <div class="card">

        <h1>YouTube 다운로드</h1>

        <p class="small">
            공개적으로 접근 가능한 영상 다운로드용 서버
        </p>

        <label for="url">YouTube URL</label>

        <input
            id="url"
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            autocomplete="off"
        >

        <div class="row">

            <div>
                <label for="mode">형식</label>

                <select id="mode" onchange="toggleAudio()">
                    <option value="video">영상 MP4</option>
                    <option value="audio">오디오</option>
                </select>
            </div>

            <div id="audioBox" class="hidden">

                <label for="audioFormat">오디오 형식</label>

                <select id="audioFormat">
                    <option value="mp3">MP3</option>
                    <option value="m4a">M4A</option>
                    <option value="wav">WAV</option>
                    <option value="flac">FLAC</option>
                    <option value="ogg">OGG</option>
                </select>

            </div>

        </div>

        <button
            id="downloadButton"
            onclick="downloadVideo()"
        >
            다운로드
        </button>

        <div
            id="status"
            class="status hidden"
        ></div>

    </div>
</div>


<script>

function toggleAudio() {

    const mode =
        document.getElementById("mode").value;

    const audioBox =
        document.getElementById("audioBox");

    audioBox.classList.toggle(
        "hidden",
        mode !== "audio"
    );
}


function setStatus(message) {

    const box =
        document.getElementById("status");

    box.textContent = message;

    box.classList.remove("hidden");
}


async function downloadVideo() {

    const url =
        document.getElementById("url").value.trim();

    const mode =
        document.getElementById("mode").value;

    const audioFormat =
        document.getElementById("audioFormat").value;

    const button =
        document.getElementById("downloadButton");


    if (!url) {

        setStatus(
            "YouTube URL을 입력해주세요."
        );

        return;
    }


    button.disabled = true;

    setStatus(
        "다운로드를 준비하는 중입니다.\n잠시 기다려주세요..."
    );


    try {

        const response =
            await fetch(
                "/download",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        url: url,
                        mode: mode,
                        audio_format: audioFormat
                    })
                }
            );


        if (!response.ok) {

            let message =
                "다운로드에 실패했습니다.";


            try {

                const data =
                    await response.json();

                if (data.detail) {
                    message = data.detail;
                }

            } catch (error) {
                // JSON 응답이 아닌 경우 기본 메시지 사용
            }


            throw new Error(message);
        }


        const blob =
            await response.blob();


        const disposition =
            response.headers.get(
                "Content-Disposition"
            ) || "";


        let filename =
            mode === "video"
                ? "video.mp4"
                : "audio." + audioFormat;


        const utf8Match =
            disposition.match(
                /filename\*=UTF-8''([^;]+)/i
            );


        if (utf8Match) {

            try {

                filename =
                    decodeURIComponent(
                        utf8Match[1]
                    );

            } catch (error) {
                // 기본 파일명 유지
            }

        }


        const objectUrl =
            URL.createObjectURL(blob);


        const anchor =
            document.createElement("a");


        anchor.href = objectUrl;
        anchor.download = filename;

        document.body.appendChild(anchor);

        anchor.click();

        anchor.remove();


        setTimeout(
            () => URL.revokeObjectURL(objectUrl),
            1000
        );


        setStatus(
            "다운로드가 완료되었습니다."
        );

    } catch (error) {

        setStatus(
            error.message ||
            "다운로드 중 오류가 발생했습니다."
        );

    } finally {

        button.disabled = false;
    }
}


toggleAudio();

</script>

</body>
</html>
"""


def cleanup_job(job_dir: Path) -> None:
    shutil.rmtree(
        job_dir,
        ignore_errors=True
    )


def find_downloaded_file(
    job_dir: Path,
) -> Path | None:

    files = [
        Path(path)
        for path in glob.glob(
            str(job_dir / "*")
        )
        if Path(path).is_file()
        and not Path(path).name.endswith(
            (
                ".part",
                ".ytdl",
                ".temp",
            )
        )
    ]


    if not files:
        return None


    files.sort(
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


    return files[0]


def safe_error_message(
    error: Exception,
) -> str:

    message = str(error)


    if (
        "Sign in to confirm you’re not a bot"
        in message
        or
        "Sign in to confirm you're not a bot"
        in message
    ):

        return (
            "YouTube가 현재 서버 요청을 봇으로 판단하여 "
            "다운로드를 차단했습니다. "
            "잠시 후 다시 시도하거나 다른 영상으로 "
            "테스트해주세요."
        )


    if (
        "PO Token" in message
        or
        "POT" in message
        or
        "pot" in message.lower()
    ):

        return (
            "YouTube 인증 토큰 처리에 실패했습니다. "
            "잠시 후 다시 시도하거나 다른 영상으로 "
            "테스트해주세요."
        )


    if (
        "Requested format is not available"
        in message
    ):

        return (
            "요청한 영상 형식을 사용할 수 없습니다. "
            "다른 영상으로 테스트해주세요."
        )


    if (
        "ffmpeg" in message.lower()
        and
        (
            "not found" in message.lower()
            or
            "missing" in message.lower()
        )
    ):

        return (
            "서버의 FFmpeg 처리에 문제가 발생했습니다."
        )


    return (
        "다운로드 중 오류가 발생했습니다."
    )


@app.get(
    "/",
    response_class=HTMLResponse,
)
async def index() -> str:

    return HTML


@app.get("/health")
async def health() -> dict:

    return {
        "status": "ok"
    }


@app.post("/download")
async def download(
    request: DownloadRequest,
):

    url = request.url.strip()

    mode = request.mode.strip().lower()

    audio_format = (
        request.audio_format
        .strip()
        .lower()
    )


    valid_youtube_urls = (
        "https://www.youtube.com/",
        "https://youtube.com/",
        "https://m.youtube.com/",
        "https://youtu.be/",
    )


    if not url.startswith(
        valid_youtube_urls
    ):

        raise HTTPException(
            status_code=400,
            detail="YouTube URL만 입력해주세요.",
        )


    if mode not in {
        "video",
        "audio",
    }:

        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 다운로드 형식입니다.",
        )


    if audio_format not in {
        "mp3",
        "m4a",
        "wav",
        "flac",
        "ogg",
    }:

        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 오디오 형식입니다.",
        )


    job_id = uuid.uuid4().hex

    job_dir = (
        DOWNLOAD_ROOT / job_id
    )


    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_template = str(
        job_dir
        / "%(title).150B [%(id)s].%(ext)s"
    )


    common_options = {

        "outtmpl": output_template,

        "noplaylist": True,

        "quiet": True,

        "no_warnings": True,

        "retries": 3,

        "fragment_retries": 3,

        "concurrent_fragment_downloads": 4,

        "socket_timeout": 30,

        "windowsfilenames": True,

        "js_runtimes": {
            "node": {},
        },

        "extractor_args": {
            "youtubepot-bgutilhttp": {
                "base_url": "http://127.0.0.1:4416",
            },
        },
    }


    if mode == "video":

        ydl_opts = {
            **common_options,

            "format": "bv*+ba/b",

            "merge_output_format": "mp4",
        }

    else:

        ydl_opts = {
            **common_options,

            "format": "bestaudio/best",

            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",

                    "preferredcodec": audio_format,

                    "preferredquality": "192",
                }
            ],
        }


    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([url])


        downloaded = find_downloaded_file(
            job_dir
        )


        if downloaded is None:

            raise RuntimeError(
                "다운로드된 파일을 찾을 수 없습니다."
            )


        response = FileResponse(
            path=str(downloaded),

            media_type=(
                "video/mp4"
                if mode == "video"
                else "audio/"
                + audio_format
            ),

            filename=downloaded.name,

            background=BackgroundTask(
                cleanup_job,
                job_dir,
            ),
        )


        return response


    except HTTPException:

        cleanup_job(job_dir)

        raise


    except Exception as exc:

        cleanup_job(job_dir)

        raise HTTPException(
            status_code=500,
            detail=safe_error_message(exc),
        ) from exc


if __name__ == "__main__":

    import uvicorn


    port = int(
        os.environ.get(
            "PORT",
            "10000",
        )
    )


    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
    )
