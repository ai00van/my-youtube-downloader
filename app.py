from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import yt_dlp
import os
import glob


app = FastAPI(title="유튜브 통합 다운로더")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class DownloadRequest(BaseModel):
    url: str
    mode: str = "video"
    audio_codec: str = "mp3"


HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ko">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>유튜브 통합 다운로더</title>

    <script src="https://cdn.tailwindcss.com"></script>
</head>

<body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-4">

<div class="bg-slate-900 p-8 rounded-3xl shadow-2xl w-full max-w-xl border border-slate-800">

    <h1 class="text-2xl font-bold mb-2">
        🚀 유튜브 통합 다운로더
    </h1>

    <p class="text-sm text-slate-400 mb-6">
        영상 다운로드 / 음원 추출
    </p>


    <div class="space-y-5">

        <div>

            <label class="block text-sm text-slate-400 mb-2">
                유튜브 링크
            </label>

            <input
                id="urlInput"
                type="text"
                placeholder="https://www.youtube.com/watch?v=..."
                class="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white"
            >

        </div>


        <div>

            <label class="block text-sm text-slate-400 mb-2">
                다운로드 방식
            </label>

            <select
                id="modeInput"
                onchange="toggleAudio()"
                class="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white"
            >

                <option value="video">
                    🎥 영상 다운로드
                </option>

                <option value="audio">
                    🎵 음원 추출
                </option>

            </select>

        </div>


        <div id="audioOptions" class="hidden">

            <label class="block text-sm text-slate-400 mb-2">
                음원 형식
            </label>

            <select
                id="audioCodec"
                class="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white"
            >

                <option value="mp3">MP3</option>
                <option value="wav">WAV</option>
                <option value="flac">FLAC</option>
                <option value="m4a">M4A</option>
                <option value="ogg">OGG</option>

            </select>

        </div>


        <button
            id="downloadButton"
            onclick="startDownload()"
            class="w-full bg-red-600 hover:bg-red-700 py-4 rounded-xl font-bold"
        >
            다운로드 시작
        </button>


        <div
            id="status"
            class="hidden text-center text-sm text-slate-300 bg-slate-950 p-4 rounded-xl"
        >
        </div>

    </div>

</div>


<script>

function toggleAudio() {

    const mode =
        document.getElementById("modeInput").value;

    const audioOptions =
        document.getElementById("audioOptions");

    if (mode === "audio") {

        audioOptions.classList.remove("hidden");

    } else {

        audioOptions.classList.add("hidden");

    }

}


async function startDownload() {

    const url =
        document.getElementById("urlInput").value.trim();

    const mode =
        document.getElementById("modeInput").value;

    const audioCodec =
        document.getElementById("audioCodec").value;

    const button =
        document.getElementById("downloadButton");

    const status =
        document.getElementById("status");


    if (!url) {

        alert("유튜브 링크를 입력해주세요.");

        return;

    }


    button.disabled = true;

    button.classList.add(
        "opacity-50",
        "cursor-not-allowed"
    );


    status.classList.remove("hidden");

    status.innerText =
        "다운로드 중입니다. 잠시 기다려주세요...";


    try {

        const response =
            await fetch("/download", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    url: url,

                    mode: mode,

                    audio_codec: audioCodec

                })

            });


        if (!response.ok) {

            let message =
                "다운로드에 실패했습니다.";

            try {

                const error =
                    await response.json();

                message =
                    error.detail || message;

            } catch (e) {

            }

            throw new Error(message);

        }


        const blob =
            await response.blob();


        const downloadUrl =
            window.URL.createObjectURL(blob);


        const link =
            document.createElement("a");


        link.href = downloadUrl;


        let filename =
            mode === "video"
                ? "youtube_video.mp4"
                : "youtube_audio." + audioCodec;


        const disposition =
            response.headers.get(
                "content-disposition"
            );


        if (disposition) {

            const match =
                disposition.match(
                    /filename="?([^"]+)"?/i
                );

            if (match && match[1]) {

                filename =
                    decodeURIComponent(match[1]);

            }

        }


        link.download = filename;

        document.body.appendChild(link);

        link.click();

        link.remove();


        window.URL.revokeObjectURL(downloadUrl);


        status.innerText =
            "다운로드가 완료되었습니다.";


    } catch (error) {

        status.innerText =
            "오류 발생: " + error.message;

    } finally {

        button.disabled = false;

        button.classList.remove(
            "opacity-50",
            "cursor-not-allowed"
        );

    }

}

</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():

    return HTML_CONTENT


@app.post("/download")
async def download(data: DownloadRequest):

    url = data.url.strip()


    if not url:

        raise HTTPException(
            status_code=400,
            detail="유튜브 URL을 입력해주세요."
        )


    if data.mode not in ["video", "audio"]:

        raise HTTPException(
            status_code=400,
            detail="잘못된 다운로드 방식입니다."
        )


    if data.audio_codec not in [
        "mp3",
        "wav",
        "flac",
        "m4a",
        "ogg"
    ]:

        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 음원 형식입니다."
        )


    # 기존 파일 삭제

    for file_path in glob.glob(
        os.path.join(DOWNLOAD_DIR, "*")
    ):

        try:

            if os.path.isfile(file_path):

                os.remove(file_path)

        except Exception:

            pass


    # ==========================================
    # yt-dlp 설정
    # ==========================================

    ydl_opts = {

        "outtmpl": os.path.join(
            DOWNLOAD_DIR,
            "%(title)s.%(ext)s"
        ),

        "restrictfilenames": True,

        "noplaylist": True,

        "quiet": False,

        "no_warnings": False,

        "extractor_args": {

            "youtube": [
                "player_client=mweb"
            ],

            "youtubepot-bgutilhttp": [
                "base_url=http://127.0.0.1:4416"
            ]

        }

    }


    # ==========================================
    # 영상 다운로드
    # ==========================================

    if data.mode == "video":

        ydl_opts.update({

            "format": "bv*+ba/b",

            "merge_output_format": "mp4"

        })


    # ==========================================
    # 음원 다운로드
    # ==========================================

    else:

        ydl_opts.update({

            "format": "bestaudio/best",

            "postprocessors": [

                {

                    "key": "FFmpegExtractAudio",

                    "preferredcodec": data.audio_codec,

                    "preferredquality": "320"

                }

            ]

        })


    # ==========================================
    # 다운로드 실행
    # ==========================================

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

    except Exception as e:

        print(
            "================================"
        )

        print(
            "YT-DLP ERROR:"
        )

        print(
            repr(e)
        )

        print(
            "================================"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


    # ==========================================
    # 다운로드된 파일 찾기
    # ==========================================

    files = []

    for file_path in glob.glob(
        os.path.join(DOWNLOAD_DIR, "*")
    ):

        if os.path.isfile(file_path):

            files.append(file_path)


    if not files:

        raise HTTPException(
            status_code=500,
            detail="다운로드된 파일을 찾을 수 없습니다."
        )


    # 가장 최근 파일

    filename = max(
        files,
        key=os.path.getctime
    )


    return FileResponse(

        path=filename,

        filename=os.path.basename(filename),

        media_type="application/octet-stream"

    )


# ==========================================
# Render 실행
# ==========================================

if __name__ == "__main__":

    import uvicorn


    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )


    print(
        "유튜브 통합 다운로드 서버가 시작되었습니다!"
    )


    uvicorn.run(

        app,

        host="0.0.0.0",

        port=port

    )
