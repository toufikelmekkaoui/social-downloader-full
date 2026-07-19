"""
config.py
---------
Centralised configuration for every environment.
Load secrets from environment variables; sane defaults
are provided for local development.
"""

import os
from datetime import timedelta


class BaseConfig:
    # ── Flask core ────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production-please")
    JSON_SORT_KEYS: bool = False

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed front-end origins, e.g.
    #   ALLOWED_ORIGINS=http://localhost:5173,https://yourapp.com
    ALLOWED_ORIGINS: list[str] = [
        o.strip()
        for o in os.environ.get(
            "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
        ).split(",")
        if o.strip()
    ]

    # ── Download / Storage ────────────────────────────────────────────────────
    # Where finished files are stored on the server before streaming
    DOWNLOAD_DIR: str = os.environ.get(
        "DOWNLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "downloads")
    )
    # How long (seconds) a cached file is kept before being purged
    CACHE_TTL_SECONDS: int = int(os.environ.get("CACHE_TTL_SECONDS", 3600))  # 1 hour
    # Maximum file size the server will stream (bytes) – default 500 MB
    MAX_VIDEO_BYTES: int = int(os.environ.get("MAX_VIDEO_BYTES", 500 * 1024 * 1024))

    # ── Rate limiting (via Flask-Limiter) ─────────────────────────────────────
    RATELIMIT_DEFAULT: str = os.environ.get("RATELIMIT_DEFAULT", "60 per minute")
    RATELIMIT_ANALYZE: str = os.environ.get("RATELIMIT_ANALYZE", "20 per minute")
    RATELIMIT_DOWNLOAD: str = os.environ.get("RATELIMIT_DOWNLOAD", "10 per minute")
    # Redis URI – fall back to in-memory if not set (not suitable for multi-worker)
    RATELIMIT_STORAGE_URL: str = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")

    # ── yt-dlp options ────────────────────────────────────────────────────────
    # Prefer MP4 with H.264 + AAC so browsers / devices can play natively
    YTDLP_FORMAT: str = os.environ.get(
        "YTDLP_FORMAT",
        "bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    )
    YTDLP_MERGE_FORMAT: str = "mp4"
    # Optional proxy for all yt-dlp requests, e.g. "socks5://127.0.0.1:1080"
    YTDLP_PROXY: str | None = os.environ.get("YTDLP_PROXY", None)
    # Path to cookies file (Netscape format) for authenticated platforms
    YTDLP_COOKIES_FILE: str | None = os.environ.get("YTDLP_COOKIES_FILE", None)
    # Socket / read timeout for yt-dlp HTTP requests (seconds)
    YTDLP_SOCKET_TIMEOUT: int = int(os.environ.get("YTDLP_SOCKET_TIMEOUT", 30))

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")


class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True
    TESTING: bool = False
    LOG_LEVEL: str = "DEBUG"


class TestingConfig(BaseConfig):
    DEBUG: bool = True
    TESTING: bool = True


class ProductionConfig(BaseConfig):
    DEBUG: bool = False
    TESTING: bool = False
    # In production, ALWAYS set SECRET_KEY via environment variable.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "OVERRIDE_ME")


# ── Selector ─────────────────────────────────────────────────────────────────
_config_map: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config() -> BaseConfig:
    """Return the correct config object based on FLASK_ENV."""
    env = os.environ.get("FLASK_ENV", "development").lower()
    return _config_map.get(env, DevelopmentConfig)()
