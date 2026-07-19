"""
utils/file_cleaner.py
---------------------
Background thread that periodically removes stale cached video files
from the DOWNLOAD_DIR so the server does not fill up its disk.
"""

import logging
import os
import threading
import time

logger = logging.getLogger(__name__)


class FileCleaner:
    """
    Periodically delete files in *directory* that are older than
    *ttl_seconds* seconds.  Runs in a daemon thread so it stops
    automatically when the main process exits.
    """

    def __init__(self, directory: str, ttl_seconds: int, interval: int = 300) -> None:
        self.directory = directory
        self.ttl_seconds = ttl_seconds
        self.interval = interval          # how often to sweep (seconds)
        self._thread: threading.Thread | None = None

    # ── Public interface ──────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="FileCleaner")
        self._thread.start()
        logger.info(
            "FileCleaner started (dir=%s, ttl=%ds, interval=%ds)",
            self.directory,
            self.ttl_seconds,
            self.interval,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self) -> None:
        while True:
            try:
                self._sweep()
            except Exception as exc:
                logger.warning("FileCleaner sweep error: %s", exc)
            time.sleep(self.interval)

    def _sweep(self) -> None:
        if not os.path.isdir(self.directory):
            return
        now = time.time()
        removed = 0
        for filename in os.listdir(self.directory):
            filepath = os.path.join(self.directory, filename)
            if not os.path.isfile(filepath):
                continue
            age = now - os.path.getmtime(filepath)
            if age > self.ttl_seconds:
                try:
                    os.remove(filepath)
                    removed += 1
                    logger.debug("Removed stale file: %s (age=%.0fs)", filename, age)
                except OSError as exc:
                    logger.warning("Could not remove %s: %s", filepath, exc)
        if removed:
            logger.info("FileCleaner: removed %d stale file(s)", removed)
