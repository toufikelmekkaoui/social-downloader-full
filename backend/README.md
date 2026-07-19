# Social Video Downloader — Flask Backend

> Production-ready Python/Flask API that powers the Social Video Downloader UI.  
> Extracts and streams MP4 videos from **Facebook**, **Instagram**, and **TikTok** using **yt-dlp**.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Quick Start (Local)](#quick-start-local)
5. [Environment Variables](#environment-variables)
6. [API Reference](#api-reference)
7. [Running Tests](#running-tests)
8. [Docker Deployment](#docker-deployment)
9. [Production Checklist](#production-checklist)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
React UI  ──POST /api/analyze──►  Flask App  ──►  VideoDownloaderService  ──►  yt-dlp
          ◄──  JSON metadata  ──              ◄──  sanitized info dict    ◄──

React UI  ──POST /api/download──► Flask App  ──►  VideoDownloaderService  ──►  yt-dlp + ffmpeg
          ◄──  MP4 stream      ──              ◄──  filepath               ◄──
```

**Key layers:**

| Layer | File(s) | Responsibility |
|-------|---------|----------------|
| Config | `app/config.py` | All settings loaded from env vars |
| Extensions | `app/extensions.py` | Flask-CORS, Flask-Limiter (singletons) |
| Factory | `app/factory.py` | `create_app()` — wires everything together |
| Routes | `app/api/routes.py` | REST endpoints, request validation |
| Errors | `app/api/errors.py` | Uniform JSON error envelope |
| Service | `app/services/downloader.py` | All yt-dlp logic, caching, file management |
| Validators | `app/utils/validators.py` | URL allowlist & sanitization |
| Cleaner | `app/utils/file_cleaner.py` | Background thread to purge stale files |
| Logger | `app/utils/logger.py` | Console + rotating-file logging |

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py               # BaseConfig, Dev/Test/Prod configs
│   ├── extensions.py           # Flask-CORS, Flask-Limiter
│   ├── factory.py              # create_app()
│   ├── api/
│   │   ├── __init__.py
│   │   ├── errors.py           # JSON error helpers + global handlers
│   │   └── routes.py           # /api/health, /api/analyze, /api/download
│   ├── services/
│   │   ├── __init__.py
│   │   └── downloader.py       # VideoDownloaderService (yt-dlp wrapper)
│   └── utils/
│       ├── __init__.py
│       ├── file_cleaner.py     # Daemon thread: deletes stale cached files
│       ├── logger.py           # Logging setup
│       └── validators.py       # URL detection & sanitization
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest fixtures
│   ├── test_health.py
│   ├── test_analyze.py
│   ├── test_validators.py
│   └── test_downloader_service.py
├── downloads/                  # Temp video cache (git-ignored)
├── logs/                       # Log files (git-ignored)
├── .env.example                # Copy to .env and fill in values
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── gunicorn.conf.py
├── requirements.txt
└── wsgi.py                     # WSGI entry point
```

---

## Prerequisites

| Tool | Minimum version | Notes |
|------|----------------|-------|
| Python | 3.11+ | 3.12 recommended |
| pip | latest | `pip install --upgrade pip` |
| ffmpeg | 6.x | **Required** for merging video+audio streams |
| (optional) Redis | 7.x | Multi-worker rate limiting |

### Install ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt-get install ffmpeg

# Windows (via Scoop)
scoop install ffmpeg
```

---

## Quick Start (Local)

```bash
# 1. Clone the repo and enter the backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and ALLOWED_ORIGINS

# 5. Run the development server
python wsgi.py
# → http://localhost:8000

# 6. Verify it works
curl http://localhost:8000/api/health
# {"status": "ok", "timestamp": 1700000000}
```

### Test a real URL

```bash
curl -s -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@username/video/1234567890"}' | python -m json.tool
```

---

## Environment Variables

Copy `.env.example` to `.env`.  All variables below can be set either in `.env` or as real OS environment variables (OS vars take precedence).

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | `development` \| `testing` \| `production` |
| `SECRET_KEY` | *(required in prod)* | Flask session signing key |
| `ALLOWED_ORIGINS` | `http://localhost:5173,…` | CORS whitelist (comma-separated) |
| `DOWNLOAD_DIR` | `./downloads` | Where MP4 files are cached |
| `CACHE_TTL_SECONDS` | `3600` | File / info cache lifetime (seconds) |
| `MAX_VIDEO_BYTES` | `524288000` | Max streamable file size (500 MB) |
| `RATELIMIT_DEFAULT` | `60 per minute` | Global rate limit |
| `RATELIMIT_ANALYZE` | `20 per minute` | `/api/analyze` rate limit |
| `RATELIMIT_DOWNLOAD` | `10 per minute` | `/api/download` rate limit |
| `RATELIMIT_STORAGE_URL` | `memory://` | `redis://…` for multi-worker setups |
| `YTDLP_FORMAT` | *(H.264+AAC selector)* | yt-dlp format string |
| `YTDLP_PROXY` | *(unset)* | Proxy for yt-dlp (e.g. `socks5://127.0.0.1:1080`) |
| `YTDLP_COOKIES_FILE` | *(unset)* | Path to Netscape cookies file |
| `YTDLP_SOCKET_TIMEOUT` | `30` | Per-request timeout (seconds) |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `PORT` | `8000` | Server port |

---

## API Reference

All endpoints return `Content-Type: application/json`.

### `GET /api/health`

Liveness probe.

**Response 200**
```json
{ "status": "ok", "timestamp": 1700000000 }
```

---

### `POST /api/analyze`

Extract video metadata **without** downloading.

**Request**
```json
{ "url": "https://www.instagram.com/reel/ABC123/" }
```

**Response 200**
```json
{
  "success": true,
  "platform": "instagram",
  "data": {
    "id":           "ABC123",
    "title":        "My Reel Title",
    "thumbnail":    "https://…/thumb.jpg",
    "duration":     "0:30",
    "duration_sec": 30,
    "uploader":     "someuser",
    "uploader_url": "https://instagram.com/someuser",
    "platform":     "Instagram",
    "webpage_url":  "https://www.instagram.com/reel/ABC123/",
    "view_count":   1234567,
    "like_count":   98765,
    "upload_date":  "20240101",
    "description":  "…",
    "formats": [
      { "format_id": "1080p-fmt", "label": "1080p", "ext": "mp4",
        "filesize": 120000000, "fps": 30, "vcodec": "avc1", "acodec": "mp4a" }
    ]
  }
}
```

**Error codes**

| HTTP | `code` | Meaning |
|------|--------|---------|
| 400 | `BAD_REQUEST` | Missing / malformed JSON body |
| 422 | `UNSUPPORTED_PLATFORM` | URL not from Facebook / Instagram / TikTok |
| 422 | `EXTRACTION_FAILED` | yt-dlp could not process the URL |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `SERVER_ERROR` | Unexpected error |

---

### `POST /api/download`

Download video and **stream the MP4** back to the client.

**Request**
```json
{
  "url":       "https://www.instagram.com/reel/ABC123/",
  "format_id": "1080p-fmt"
}
```
`format_id` is optional — omit it to use the best available quality.

**Response 200** — binary MP4 stream with:
```
Content-Type:        video/mp4
Content-Disposition: attachment; filename="My_Reel_Title.mp4"
Accept-Ranges:       bytes
```

**Error codes**

| HTTP | `code` | Meaning |
|------|--------|---------|
| 400 | `BAD_REQUEST` | Missing / malformed request |
| 413 | `VIDEO_TOO_LARGE` | File exceeds `MAX_VIDEO_BYTES` |
| 422 | `UNSUPPORTED_PLATFORM` | URL not supported |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `DOWNLOAD_FAILED` | Download or streaming error |

---

## Running Tests

```bash
# Install test dependencies (already in requirements.txt)
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Run a single file
pytest tests/test_validators.py -v
```

---

## Docker Deployment

### Build & run with Docker Compose

```bash
# Copy and fill in .env
cp .env.example .env

# Build and start
docker compose up --build

# Verify
curl http://localhost:8000/api/health
```

### Build image manually

```bash
docker build -t social-video-downloader .
docker run -p 8000:8000 --env-file .env social-video-downloader
```

---

## Production Checklist

- [ ] Set a strong random `SECRET_KEY` via environment variable
- [ ] Set `FLASK_ENV=production`
- [ ] Set `ALLOWED_ORIGINS` to your actual front-end domain(s)
- [ ] Use Redis for `RATELIMIT_STORAGE_URL` with multiple Gunicorn workers
- [ ] Mount a persistent volume for `DOWNLOAD_DIR`
- [ ] Place Nginx (or a CDN) in front of Gunicorn to handle SSL termination
- [ ] Keep `yt-dlp` updated regularly: `pip install -U yt-dlp`
- [ ] Monitor disk usage — `CACHE_TTL_SECONDS` controls how long files are kept
- [ ] Set `YTDLP_COOKIES_FILE` if Instagram/Facebook starts requiring login

### Nginx reverse-proxy snippet

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    client_max_body_size 1m;

    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        # Allow large MP4 streams without buffering into Nginx memory
        proxy_buffering    off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

---

## Troubleshooting

### `ffmpeg not found`
yt-dlp needs ffmpeg to merge separate video and audio streams.  
Install it system-wide (see [Prerequisites](#prerequisites)) or set `$PATH`.

### Instagram / Facebook requires login
Some content requires authentication.  
1. Export your browser cookies (using a browser extension like "Get cookies.txt LOCALLY")
2. Save the Netscape-format file and point `YTDLP_COOKIES_FILE` at it.

### Rate limit errors from the platform
The social platforms detect repeated requests from the same IP.  
- Reduce `RATELIMIT_DOWNLOAD` to slow request throughput.
- Set `YTDLP_PROXY` to route through a residential proxy.

### `Video is too large` error
Increase `MAX_VIDEO_BYTES` in `.env` (default 500 MB).

### yt-dlp fails on a previously working URL
Platforms change their internals frequently.  Update yt-dlp:
```bash
pip install -U yt-dlp
# or inside Docker
docker compose build --no-cache
```
