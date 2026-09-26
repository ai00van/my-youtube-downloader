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

<body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-4 font-sans">

<div class="bg-slate-900 p-8 rounded-3xl shadow-2xl w-full max-w-xl border border-slate-800">

    <div class="flex items-center gap-3 mb-6">
        <div class="p-3 bg-red-600/20 text-red-500 rounded-2xl border border-red-500/30 text-2xl">
            🚀
        </div>

        <div>
            <h1 class="text-2xl font-black tracking-tight text-white">
                유튜브 통합 다운로더
            </h1>

            <p class="text-xs text-slate-400">
                영상 또는 음원을 다운로드하세요
            </p>
        </div>
    </div>

    <div class="space-y-5">

        <div>
            <label class="block text-xs font-semibold text-slate-400 mb-2">
                유튜브 링크
            </label>

            <input
                type="text"
                id="urlInput"
                placeholder="https://www.youtube.com/watch?v=..."
                class="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white text-sm"
            >
        </div>

        <div>
            <label class="block text-xs font-semibold text-slate-400 mb-2">
                다운로드 모드
            </label>

            <select
                id="modeInput"
                onchange="toggleMode()"
                class="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white text-sm"
            >
                <option value="video">🎥 영상 다운로드</option>
                <option value="audio">🎵 음원만 다운로드</option>
            </select>
        </div>

        <div id="audioOptionsDiv" class="hidden">

            <label class="block text-xs font-semibold text-slate-400 mb-2">
                음원 포맷
            </label>

            <select
                id="audioCodecInput"
                class="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white text-sm"
            >
                <option value="mp3">MP3</option>
                <option value="wav">WAV</option>
                <option value="flac">FLAC</option>
                <option value="m4a">M4A</option>
                <option value="ogg">OGG</option>
            </select>

        </div>

        <button
            onclick="startDownload()"
            id="downloadBtn"
            class="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3.5 px-4 rounded-xl"
        >
            다운로드 시작
        </button>

    </div>

    <div id="statusArea" class="mt-6 hidden">

        <div class="p-4 bg-slate-950 rounded-2xl border border-slate-800 text-center">

            <p id="statusText" class="text-sm font-medium text-slate-300">
                처리 중...
            </p>

        </div>

    </div>

</div>


<script>

function toggleMode() {

    const mode = document.getElementById("modeInput").value;
    const audioDiv = document.getElementById("audioOptionsDiv");
    const btn = document.getElementById("downloadBtn");

    if (mode === "audio") {

        audioDiv.classList.remove("hidden");

        btn.className =
            "w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3.5 px-4 rounded-xl";

    } else {

        audioDiv.classList.add("hidden");

        btn.className =
            "w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3.5 px-4 rounded-xl";

    }
}


async function startDownload() {

    const url =
        document.getElementById("urlInput").value.trim();

    const mode =
        document.getElementById("modeInput").value;

    const audio_codec =
        document.getElementById("audioCodecInput").value;

    const btn =
        document.getElementById("downloadBtn");

    const statusArea =
        document.getElementById("statusArea");

    const statusText =
        document.getElementById("statusText");


    if (!url) {

        alert("유튜브 링크를 입력해주세요.");

        return;
    }


    btn.disabled = true;

    statusArea.classList.remove("hidden");

    statusText.innerText =
        "다운로드를 준비하고 있습니다...";


    try {

        const response = await fetch(
            "/download",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    url: url,
                    mode: mode,
                    audio_codec: audio_codec
                })
            }
        );


        if (!response.ok) {

            let errorMessage =
                "다운로드에 실패했습니다.";

            try {

                const err =
                    await response.json();

                errorMessage =
                    err.detail || errorMessage;

            } catch (e) {}

            throw new Error(errorMessage);
        }


        statusText.innerText =
            "다운로드 완료! 파일을 저장합니다...";


        const blob =
            await response.blob();

        const downloadUrl =
            window.URL.createObjectURL(blob);

        const a =
            document.createElement("a");

        a.href = downloadUrl;


        let filename =
            mode === "video"
                ? "downloaded_video.mp4"
                : "extracted_audio." + audio_codec;


        const disposition =
            response.headers.get("content-disposition");


        if (
            disposition &&
            disposition.includes("filename=")
        ) {

            filename =
                decodeURIComponent(
                    disposition
                        .split("filename=")[1]
                        .replace(/["']/g, "")
                );
        }


        a.download = filename;

        document.body.appendChild(a);

        a.click();

        a.remove();

        window.URL.revokeObjectURL(downloadUrl);


        statusText.innerText =
            "성공적으로 저장되었습니다!";


    } catch (error) {

        statusText.innerText =
            "오류 발생: " + error.message;

    } finally {

        btn.disabled = false;

    }
}

</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_index():

    return HTML_CONTENT


@app.post("/download")
async def download_media(data: DownloadRequest):

    try:

        # 기존 다운로드 파일 삭제
        for f in glob.glob(
            os.path.join(DOWNLOAD_DIR, "*")
        ):

            try:
                os.remove(f)

            except Exception:
                pass


        # yt-dlp 기본 설정
        ydl_opts = {
            "outtmpl": os.path.join(
                DOWNLOAD_DIR,
                "%(title)s.%(ext)s"
            ),
            "restrictfilenames": True,
            "noplaylist": True,
        }


        # 음원 다운로드
        if data.mode == "audio":

            ydl_opts.update({

                "format": "bestaudio/best",

                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": data.audio_codec,
                        "preferredquality": (
                            "320"
                            if data.audio_codec in ["mp3", "m4a"]
                            else None
                        ),
                    }
                ],
            })


        # 영상 다운로드
        else:

            ydl_opts.update({

                "format": "bv*+ba/b",

                "merge_output_format": "mp4",
            })


        # yt-dlp 실행
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                data.url,
                download=True
            )

            filename = ydl.prepare_filename(info)


        # 최종 파일 이름
        if data.mode == "audio":

            base, _ = os.path.splitext(filename)

            filename = base + "." + data.audio_codec

        else:

            base, _ = os.path.splitext(filename)

            filename = base + ".mp4"


        # 파일 확인
        if not os.path.exists(filename):

            files = glob.glob(
                os.path.join(DOWNLOAD_DIR, "*")
            )

            if not files:

                raise HTTPException(
                    status_code=500,
                    detail="다운로드된 파일을 찾을 수 없습니다."
                )

            filename = max(
                files,
                key=os.path.getctime
            )


        # 파일 보내기
        return FileResponse(
            path=filename,
            filename=os.path.basename(filename),
            media_type="application/octet-stream"
        )


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ==========================================
# 서버 시작
# ==========================================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            8000
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
