# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Social Video Downloader (Flask backend)
# Multi-stage build: keeps the final image lean.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: build dependencies ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="your@email.com"
LABEL description="Social Video Downloader — Flask/yt-dlp backend"

# ffmpeg is required by yt-dlp to merge video + audio streams
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p downloads logs \
 && chown -R appuser:appuser /app

USER appuser

# ── Runtime environment ───────────────────────────────────────────────────────
ENV FLASK_ENV=production \
    PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
