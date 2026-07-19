"""
factory.py
----------
Flask application factory.

Usage
─────
    from app.factory import create_app
    app = create_app()
"""

import logging
import os

from flask import Flask

from app.config import get_config
from app.extensions import cors, limiter
from app.utils.logger import setup_logging
from app.utils.file_cleaner import FileCleaner

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Create, configure, and return the Flask application object."""
    cfg = get_config()

    # ── Logging must be set up before anything else ───────────────────────────
    setup_logging(cfg.LOG_LEVEL)

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(cfg)

    # ── Extensions ────────────────────────────────────────────────────────────
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": cfg.ALLOWED_ORIGINS}},
        supports_credentials=False,
        expose_headers=["Content-Disposition", "X-Response-Time"],
    )

    limiter.init_app(app)

    # ── Error handlers ────────────────────────────────────────────────────────
    from app.api.errors import register_error_handlers
    register_error_handlers(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.api.routes import api_bp
    app.register_blueprint(api_bp)

    # ── VideoDownloaderService (stored on app.extensions) ─────────────────────
    from app.services.downloader import VideoDownloaderService

    download_dir = os.path.abspath(cfg.DOWNLOAD_DIR)
    os.makedirs(download_dir, exist_ok=True)

    svc = VideoDownloaderService(
        download_dir=download_dir,
        fmt=cfg.YTDLP_FORMAT,
        merge_fmt=cfg.YTDLP_MERGE_FORMAT,
        proxy=cfg.YTDLP_PROXY,
        cookies_file=cfg.YTDLP_COOKIES_FILE,
        socket_timeout=cfg.YTDLP_SOCKET_TIMEOUT,
        cache_ttl=cfg.CACHE_TTL_SECONDS,
        max_bytes=cfg.MAX_VIDEO_BYTES,
    )
    app.extensions["downloader_service"] = svc

    # ── Background file cleaner ───────────────────────────────────────────────
    cleaner = FileCleaner(
        directory=download_dir,
        ttl_seconds=cfg.CACHE_TTL_SECONDS,
        interval=300,   # sweep every 5 minutes
    )
    cleaner.start()

    logger.info(
        "Social Video Downloader API ready (env=%s, download_dir=%s)",
        os.environ.get("FLASK_ENV", "development"),
        download_dir,
    )

    return app
