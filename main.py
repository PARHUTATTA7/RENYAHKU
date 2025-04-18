from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import subprocess

app = FastAPI()

@app.get("/getvideo")
def get_video(url: str = Query(...)):
    if not url.startswith("http"):
        return JSONResponse(status_code=400, content={"error": "Invalid URL"})

    try:
        result = subprocess.run(
        ["python3", "-m", "yt_dlp", "-f", "best[ext=mp4]", "-g", url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

        if result.returncode != 0:
            return JSONResponse(status_code=500, content={
                "error": "yt-dlp failed",
                "detail": result.stderr.strip()
            })

        return {"url": result.stdout.strip()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
