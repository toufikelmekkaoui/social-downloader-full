"""
utils/logger.py
---------------
Centralised logging setup.  Call ``setup_logging(level)`` once inside
the application factory.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
import os


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with console + rotating-file handlers."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console.setLevel(numeric_level)

    # Rotating file handler (5 MB × 3 backups)
    log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(numeric_level)

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.addHandler(console)
    root.addHandler(file_handler)

    # Silence noisy third-party loggers
    for noisy in ("urllib3", "yt_dlp.utils", "werkzeug"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
