from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.route("/get_youtube_url")
def get_youtube_url():
    video_url = request.args.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    ydl_opts = {
        "quiet": True,
        "format": "18",  # mp4 360p
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
            return jsonify({"url": info["url"]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
