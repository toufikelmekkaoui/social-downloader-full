# backend/api/index.py
import sys
import os

# إضافة backend للـ path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# ── Analyze ───────────────────────────────────────────────────────────────────
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
        "extract_flat": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # بناء قائمة formats مبسطة
        raw_formats = info.get("formats") or []
        formats = []

        for f in raw_formats:
            # نأخذ فقط الـ formats اللي عندهم video
            if not f.get("vcodec") or f.get("vcodec") == "none":
                continue

            height     = f.get("height")
            resolution = f"{height}p" if height else f.get("format_note", "unknown")

            formats.append({
                "format_id":  f.get("format_id", ""),
                "resolution": resolution,
                "ext":        f.get("ext", "mp4"),
                "filesize":   f.get("filesize") or f.get("filesize_approx"),
                "quality":    resolution,
            })

        # إزالة التكرار وترتيب من الأعلى للأدنى
        seen = set()
        unique_formats = []
        for f in reversed(formats):
            key = f["resolution"]
            if key not in seen:
                seen.add(key)
                unique_formats.append(f)
        unique_formats.reverse()

        # إذا ما لقينا formats - نزيدو واحد افتراضي
        if not unique_formats:
            unique_formats = [{
                "format_id":  "best",
                "resolution": "Best",
                "ext":        "mp4",
                "filesize":   None,
                "quality":    "Best",
            }]

        platform = (info.get("extractor_key") or
                    info.get("extractor") or "Unknown")

        return jsonify({
            "title":       info.get("title", "Unknown Title"),
            "thumbnail":   info.get("thumbnail", ""),
            "duration":    str(info.get("duration", "")),
            "platform":    platform,
            "uploader":    info.get("uploader", ""),
            "upload_date": info.get("upload_date"),
            "webpage_url": info.get("webpage_url", url),
            "view_count":  info.get("view_count"),
            "like_count":  info.get("like_count"),
            "formats":     unique_formats,
        })

    except yt_dlp.utils.DownloadError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        return jsonify({"error": f"Internal error: {str(exc)}"}), 500


# ── Download ──────────────────────────────────────────────────────────────────
@app.route("/api/download", methods=["POST"])
def download():
    body      = request.get_json(silent=True) or {}
    url       = (body.get("url") or "").strip()
    format_id = (body.get("format_id") or "best").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    # Vercel كيعطينا /tmp فقط للكتابة
    tmp_dir = "/tmp"

    ydl_opts = {
        "quiet":           True,
        "no_warnings":     True,
        "format":          f"{format_id}+bestaudio/best" if format_id != "best" else "best",
        "merge_output_format": "mp4",
        "outtmpl":         os.path.join(tmp_dir, "%(id)s.%(ext)s"),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info     = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace(".webm", ".mp4").replace(".mkv", ".mp4")

        if not os.path.exists(filename):
            # جرب نلقاو الملف في /tmp
            files = [f for f in os.listdir(tmp_dir)
                     if f.startswith(info.get("id", "")) and f.endswith(".mp4")]
            if not files:
                return jsonify({"error": "File not found after download"}), 500
            filename = os.path.join(tmp_dir, files[0])

        # إرجاع الملف مباشرة
        from flask import send_file
        return send_file(
            filename,
            mimetype="video/mp4",
            as_attachment=True,
            download_name=f"{info.get('title', 'video')[:60]}.mp4",
        )

    except yt_dlp.utils.DownloadError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        return jsonify({"error": f"Internal error: {str(exc)}"}), 500