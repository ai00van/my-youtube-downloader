import os
import glob
import uuid
import shutil

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp


app = FastAPI(title="YouTube 통합 다운로드 서버")

DOWNLOAD_DIR = "/app/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DownloadRequest(BaseModel):
    url: str
    mode: str = "video"
    audio_codec: str = "mp3"


HTML_PAGE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    max-width: 700px;
    margin: 0 auto;
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 3px 15px rgba(0,0,0,0.08);
}

h1 {
    text-align: center;
    margin-top: 0;
}

.description {
    text-align: center;
    color: #666;
    margin-bottom: 30px;
}

input[type="text"] {
    width: 100%;
    padding: 14px;
    font-size: 16px;
    border: 1px solid #ccc;
    border-radius: 8px;
    margin-bottom: 20px;
}

.mode {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
}

.mode label {
    flex: 1;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
    cursor: pointer;
}

select {
    width: 100%;
    padding: 12px;
    font-size: 16px;
    border-radius: 8px;
    border: 1px solid #ccc;
    margin-bottom: 20px;
}

button {
    width: 100%;
    padding: 15px;
    font-size: 18px;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    background: #111;
    color: white;
    cursor: pointer;
}

button:disabled {
    background: #999;
    cursor: not-allowed;
}

#status {
    margin-top: 20px;
    text-align: center;
    white-space: pre-wrap;
    line-height: 1.5;
}

.hidden {
    display: none;
}
</style>
</head>

<body>

<div class="container">

<h1>YouTube 다운로드</h1>

<div class="description">
가족이 함께 사용할 수 있는 통합 다운로드 서버
</div>

<input
    type="text"
    id="url"
    placeholder="YouTube 주소를 입력하세요"
>

<div class="mode">

<label>
<input
    type="radio"
    name="mode"
    value="video"
    checked
>
영상
</label>

<label>
<input
    type="radio"
    name="mode"
    value="audio"
>
음악
</label>

</div>

<div id="audioOptions" class="hidden">

<select id="audioCodec">
<option value="mp3">MP3</option>
<option value="wav">WAV</option>
<option value="flac">FLAC</option>
<option value="m4a">M4A</option>
<option value="ogg">OGG</option>
</select>

</div>

<button id="downloadButton" type="button">
다운로드
</button>

<div id="status"></div>

</div>

<script>
"use strict";

const NEWLINE = String.fromCharCode(10);


function changeMode() {

    const selected =
        document.querySelector(
            'input[name="mode"]:checked'
        );

    const audioOptions =
        document.getElementById("audioOptions");

    if (!selected) {
        return;
    }

    if (selected.value === "audio") {
        audioOptions.classList.remove("hidden");
    } else {
        audioOptions.classList.add("hidden");
    }
}


async function downloadVideo() {

    const urlElement =
        document.getElementById("url");

    const button =
        document.getElementById("downloadButton");

    const status =
        document.getElementById("status");

    const modeElement =
        document.querySelector(
            'input[name="mode"]:checked'
        );

    const audioCodecElement =
        document.getElementById("audioCodec");


    if (!urlElement || !button || !status || !modeElement) {

        console.error(
            "필수 HTML 요소를 찾을 수 없습니다."
        );

        return;
    }


    const url =
        urlElement.value.trim();

    const mode =
        modeElement.value;

    const audioCodec =
        audioCodecElement
            ? audioCodecElement.value
            : "mp3";


    if (!url) {

        status.innerText =
            "YouTube 주소를 입력해주세요.";

        return;
    }


    button.disabled = true;

    status.innerText =
        "다운로드 준비 중입니다." +
        NEWLINE +
        "잠시 기다려주세요.";


    try {

        console.log("다운로드 요청 시작");
        console.log("URL:", url);
        console.log("MODE:", mode);


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
                        audio_codec: audioCodec
                    })
                }
            );


        console.log(
            "서버 응답:",
            response.status,
            response.statusText
        );


        if (!response.ok) {

            let errorMessage =
                "다운로드 서버에서 오류가 발생했습니다.";

            try {

                const errorData =
                    await response.json();

                if (errorData.detail) {
                    errorMessage =
                        errorData.detail;
                }

            } catch (jsonError) {

                try {

                    const text =
                        await response.text();

                    if (text) {
                        errorMessage = text;
                    }

                } catch (textError) {

                    console.error(textError);

                }
            }

            throw new Error(errorMessage);
        }


        const blob =
            await response.blob();


        if (!blob || blob.size === 0) {

            throw new Error(
                "다운로드된 파일이 비어 있습니다."
            );
        }


        const downloadUrl =
            window.URL.createObjectURL(blob);


        const a =
            document.createElement("a");

        a.href =
            downloadUrl;


        let filename =
            mode === "audio"
                ? "download.mp3"
                : "download.mp4";


        const disposition =
            response.headers.get(
                "Content-Disposition"
            );


        if (disposition) {

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

                } catch (decodeError) {

                    console.error(
                        decodeError
                    );
                }

            } else {

                const normalMatch =
                    disposition.match(
                        /filename="?([^"]+)"?/i
                    );


                if (normalMatch) {

                    filename =
                        normalMatch[1];

                }
            }
        }


        a.download =
            filename;


        document.body.appendChild(a);

        a.click();

        a.remove();


        setTimeout(
            function() {
                window.URL.revokeObjectURL(
                    downloadUrl
                );
            },
            1000
        );


        status.innerText =
            "다운로드가 완료되었습니다.";

    } catch (error) {

        console.error(
            "다운로드 오류:",
            error
        );


        status.innerText =
            "다운로드 오류가 발생했습니다." +
            NEWLINE +
            NEWLINE +
            (
                error && error.message
                    ? error.message
                    : String(error)
            );

    } finally {

        button.disabled = false;

    }
}


document.addEventListener(
    "DOMContentLoaded",
    function() {

        const downloadButton =
            document.getElementById(
                "downloadButton"
            );


        const modeInputs =
            document.querySelectorAll(
                'input[name="mode"]'
            );


        modeInputs.forEach(
            function(input) {

                input.addEventListener(
                    "change",
                    changeMode
                );

            }
        );


        if (downloadButton) {

            downloadButton.addEventListener(
                "click",
                downloadVideo
            );

        }


        changeMode();


        console.log(
            "YouTube 다운로드 페이지 초기화 완료"
        );

    }
);

</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE


@app.post("/download")
async def download(request: DownloadRequest):

    url = request.url.strip()

    if not url:

        raise HTTPException(
            status_code=400,
            detail="YouTube 주소가 없습니다."
        )


    job_id = str(uuid.uuid4())

    job_dir = os.path.join(
        DOWNLOAD_DIR,
        job_id
    )

    os.makedirs(
        job_dir,
        exist_ok=True
    )


    ydl_opts = {

        "outtmpl":
            os.path.join(
                job_dir,
                "%(title)s.%(ext)s"
            ),

        "restrictfilenames": True,

        "noplaylist": True,

        "quiet": False,

        "no_warnings": False,

        "verbose": True,

        "js_runtimes": {
            "node": "/usr/bin/node"
        },

        "extractor_args": {

            "youtube": [
                "player_client=mweb,default"
            ],

            "youtubepot-bgutilhttp": [
                "base_url=http://127.0.0.1:4416"
            ]

        }

    }


    if request.mode == "video":

        ydl_opts.update({

            "format":
                "bv*+ba/b",

            "merge_output_format":
                "mp4"

        })


    elif request.mode == "audio":

        codec =
            request.audio_codec.lower()

        codec_map = {

            "mp3": "mp3",
            "wav": "wav",
            "flac": "flac",
            "m4a": "m4a",
            "ogg": "vorbis"

        }


        if codec not in codec_map:

            shutil.rmtree(
                job_dir,
                ignore_errors=True
            )

            raise HTTPException(
                status_code=400,
                detail="지원하지 않는 오디오 형식입니다."
            )


        ydl_opts.update({

            "format":
                "bestaudio/best",

            "postprocessors": [

                {
                    "key":
                        "FFmpegExtractAudio",

                    "preferredcodec":
                        codec_map[codec],

                    "preferredquality":
                        "320"
                }

            ]

        })


    else:

        shutil.rmtree(
            job_dir,
            ignore_errors=True
        )

        raise HTTPException(
            status_code=400,
            detail="잘못된 다운로드 형식입니다."
        )


    try:

        print("=" * 60)

        print(
            "YouTube 다운로드 시작"
        )

        print(
            "URL:",
            url
        )

        print(
            "MODE:",
            request.mode
        )

        print(
            "JS Runtime:",
            "/usr/bin/node"
        )

        print(
            "POT Server:",
            "http://127.0.0.1:4416"
        )

        print("=" * 60)


        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([url])


    except Exception as e:

        print("=" * 60)

        print(
            "YT-DLP ERROR:"
        )

        print(
            repr(e)
        )

        print("=" * 60)


        shutil.rmtree(
            job_dir,
            ignore_errors=True
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


    files = [

        file

        for file in glob.glob(
            os.path.join(
                job_dir,
                "*"
            )
        )

        if os.path.isfile(file)

    ]


    if not files:

        shutil.rmtree(
            job_dir,
            ignore_errors=True
        )

        raise HTTPException(
            status_code=500,
            detail="다운로드된 파일을 찾을 수 없습니다."
        )


    output_file = max(
        files,
        key=os.path.getmtime
    )


    filename = os.path.basename(
        output_file
    )


    return FileResponse(

        output_file,

        filename=filename,

        media_type=
            "application/octet-stream"

    )


if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            "10000"
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
