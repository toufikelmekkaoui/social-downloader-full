import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/analyze", methods=["POST"])
def analyze():
    body = request.get_json(silent=True) or {}
    url  = (body.get("url") or "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        raw_formats = info.get("formats") or []
        formats = []

        for f in raw_formats:
            # نختار الفيديوهات التي تحتوي على صوت وصورة معاً
            if f.get("vcodec") != "none" and f.get("acodec") != "none":
                height = f.get("height")
                resolution = f"{height}p" if height else "HD"
                
                formats.append({
                    "format_id":  f.get("format_id"),
                    "resolution": resolution,
                    "ext":        f.get("ext", "mp4"),
                    "url":        f.get("url"), # رابط التحميل المباشر
                    "quality":    resolution,
                })

        # إذا لم نجد صيغ مدمجة، نأخذ الرابط المباشر العام
        if not formats:
            formats.append({
                "format_id":  "best",
                "resolution": "Best Quality",
                "ext":        "mp4",
                "url":        info.get("url"),
                "quality":    "Best",
            })

        return jsonify({
            "title":       info.get("title", "Social Video"),
            "thumbnail":   info.get("thumbnail", ""),
            "duration":    str(info.get("duration", "")),
            "platform":    info.get("extractor_key", "Social Media"),
            "uploader":    info.get("uploader", ""),
            "download_url": info.get("url"), # رابط مباشر
            "formats":     formats,
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/download", methods=["POST"])
def download():
    body = request.get_json(silent=True) or {}
    url  = (body.get("url") or "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        direct_url = info.get("url")
        return jsonify({"download_url": direct_url})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run()