"""
services/downloader.py
----------------------
All yt-dlp interactions live here.  The rest of the application
calls only ``VideoDownloaderService`` – never yt-dlp directly.

Design decisions:
  • ``extract_info``  — runs yt-dlp with download=False so we can
      return rich metadata to the UI quickly.
  • ``download_video`` — downloads the file to DOWNLOAD_DIR with a
      stable filename derived from the video ID, then returns the
      absolute path so the route can stream it back.
  • A lightweight in-process ``dict`` cache avoids re-fetching
      metadata within the same TTL window.
  • All yt-dlp errors are caught and re-raised as typed exceptions
      so the API layer can produce consistent JSON error responses.
"""

import hashlib
import logging
import os
import time
from typing import Optional

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

logger = logging.getLogger(__name__)


# ── Custom exceptions ─────────────────────────────────────────────────────────


class UnsupportedPlatformError(Exception):
    """The URL does not belong to a platform we support."""


class VideoExtractionError(Exception):
    """yt-dlp could not extract video information."""


class VideoDownloadError(Exception):
    """yt-dlp failed to download the video file."""


class VideoTooLargeError(Exception):
    """The video file exceeds the server's configured size limit."""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _stable_id(url: str) -> str:
    """Return a short, filesystem-safe hash of *url*."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _format_duration(seconds: Optional[float]) -> str:
    """Convert raw seconds to ``M:SS`` or ``H:MM:SS`` display string."""
    if not seconds:
        return "0:00"
    seconds = int(seconds)
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _pick_best_thumbnail(info: dict) -> Optional[str]:
    """
    Choose the highest-resolution thumbnail from the ``thumbnails`` list
    or fall back to the top-level ``thumbnail`` key.
    """
    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        # yt-dlp usually lists thumbnails worst-to-best; pick the last one
        for thumb in reversed(thumbnails):
            url = thumb.get("url", "")
            if url.startswith("http"):
                return url
    return info.get("thumbnail")


# ── Service class ─────────────────────────────────────────────────────────────


class VideoDownloaderService:
    """
    Thin wrapper around ``yt_dlp.YoutubeDL`` that exposes two clean
    methods:  ``extract_info`` and ``download_video``.

    Parameters
    ----------
    download_dir : str
        Absolute path where downloaded MP4 files are stored temporarily.
    fmt : str
        yt-dlp format selector string.
    merge_fmt : str
        Output container after merging streams (always ``"mp4"`` for us).
    proxy : str | None
        Optional HTTP/SOCKS proxy for yt-dlp requests.
    cookies_file : str | None
        Optional path to a Netscape-format cookies file.
    socket_timeout : int
        Per-request socket timeout in seconds.
    cache_ttl : int
        How long (seconds) to cache ``extract_info`` results in memory.
    max_bytes : int
        Reject files larger than this (bytes) before streaming.
    """

    def __init__(
        self,
        download_dir: str,
        fmt: str = "bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        merge_fmt: str = "mp4",
        proxy: Optional[str] = None,
        cookies_file: Optional[str] = None,
        socket_timeout: int = 30,
        cache_ttl: int = 3600,
        max_bytes: int = 500 * 1024 * 1024,
    ) -> None:
        self.download_dir = download_dir
        self.fmt = fmt
        self.merge_fmt = merge_fmt
        self.proxy = proxy
        self.cookies_file = cookies_file
        self.socket_timeout = socket_timeout
        self.cache_ttl = cache_ttl
        self.max_bytes = max_bytes

        os.makedirs(self.download_dir, exist_ok=True)

        # Simple in-memory cache: { url_hash: (timestamp, info_dict) }
        self._cache: dict[str, tuple[float, dict]] = {}

    # ── Common yt-dlp option builder ──────────────────────────────────────────

    def _base_opts(self) -> dict:
        opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": self.socket_timeout,
            # Prefer H.264/AAC in MP4 containers for maximum compatibility
            "format": self.fmt,
            "merge_output_format": self.merge_fmt,
            # Retry logic
            "retries": 3,
            "fragment_retries": 3,
            # Geo-bypass (best-effort)
            "geo_bypass": True,
            # User-agent spoofing
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            },
        }
        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookies_file and os.path.isfile(self.cookies_file):
            opts["cookiefile"] = self.cookies_file
        return opts

    # ── Public: extract metadata ──────────────────────────────────────────────

    def extract_info(self, url: str) -> dict:
        """
        Return a JSON-serialisable metadata dict for *url*.

        Keys guaranteed to be present
        (others may be ``None`` if the platform does not expose them):
            id, title, thumbnail, duration_str, uploader, platform,
            view_count, like_count, formats
        """
        cache_key = _stable_id(url)
        now = time.monotonic()

        # Return cached result if it is still fresh
        if cache_key in self._cache:
            ts, cached = self._cache[cache_key]
            if now - ts < self.cache_ttl:
                logger.debug("Cache hit for %s", url)
                return cached

        opts = self._base_opts()
        opts["skip_download"] = True

        logger.info("Extracting info for: %s", url)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                raw = ydl.extract_info(url, download=False)
                raw = ydl.sanitize_info(raw)
        except ExtractorError as exc:
            logger.warning("ExtractorError for %s: %s", url, exc)
            raise VideoExtractionError(str(exc)) from exc
        except DownloadError as exc:
            logger.warning("DownloadError (info) for %s: %s", url, exc)
            raise VideoExtractionError(str(exc)) from exc
        except Exception as exc:
            logger.exception("Unexpected error extracting %s", url)
            raise VideoExtractionError(f"Unexpected error: {exc}") from exc

        if not raw:
            raise VideoExtractionError("yt-dlp returned empty info dict.")

        # Build a clean, stable response dict
        result = self._build_info_dict(raw)
        self._cache[cache_key] = (now, result)
        return result

    def _build_info_dict(self, raw: dict) -> dict:
        """Map the raw yt-dlp dict to our clean API schema."""
        formats_raw = raw.get("formats") or []
        available_formats = self._summarise_formats(formats_raw)
        duration_sec = raw.get("duration")

        return {
            "id":             raw.get("id", ""),
            "title":          raw.get("title") or raw.get("description") or "Untitled Video",
            "thumbnail":      _pick_best_thumbnail(raw),
            "duration":       _format_duration(duration_sec),
            "duration_sec":   duration_sec,
            "uploader":       raw.get("uploader") or raw.get("channel") or "Unknown",
            "uploader_url":   raw.get("uploader_url"),
            "platform":       (raw.get("extractor_key") or raw.get("extractor") or "").title(),
            "webpage_url":    raw.get("webpage_url") or raw.get("original_url"),
            "view_count":     raw.get("view_count"),
            "like_count":     raw.get("like_count"),
            "upload_date":    raw.get("upload_date"),   # YYYYMMDD string
            "description":    (raw.get("description") or "")[:500],
            "formats":        available_formats,
        }

    @staticmethod
    def _summarise_formats(formats: list[dict]) -> list[dict]:
        """
        Return a trimmed list of available quality options suitable
        for display in the front-end quality picker.
        """
        seen_heights: set = set()
        result: list[dict] = []

        for f in reversed(formats):          # yt-dlp: worst → best, so reverse
            if not f.get("url"):
                continue
            height = f.get("height")
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            ext    = f.get("ext", "?")

            # Skip audio-only or video-only fragments for the summary
            if vcodec == "none" or acodec == "none":
                continue

            label = f"{height}p" if height else "Best"
            if label in seen_heights:
                continue
            seen_heights.add(label)

            result.append({
                "format_id":  f.get("format_id"),
                "label":      label,
                "ext":        ext,
                "filesize":   f.get("filesize") or f.get("filesize_approx"),
                "fps":        f.get("fps"),
                "vcodec":     vcodec,
                "acodec":     acodec,
            })

            if len(result) >= 5:
                break

        # Always surface at least one entry
        if not result:
            result.append({"format_id": "best", "label": "Best", "ext": "mp4",
                           "filesize": None, "fps": None, "vcodec": None, "acodec": None})

        return result

    # ── Public: download to disk ──────────────────────────────────────────────

    def download_video(self, url: str, format_id: Optional[str] = None) -> str:
        """
        Download the video at *url* to ``self.download_dir`` and return
        the absolute path of the resulting MP4 file.

        Parameters
        ----------
        url       : The original share URL.
        format_id : Optional specific yt-dlp format_id to download.
                    Falls back to the configured best-quality selector.
        """
        file_id   = _stable_id(url + (format_id or ""))
        out_tmpl  = os.path.join(self.download_dir, f"{file_id}.%(ext)s")
        final_mp4 = os.path.join(self.download_dir, f"{file_id}.mp4")

        # If the file is already on disk and still fresh, skip re-download
        if os.path.isfile(final_mp4):
            age = time.time() - os.path.getmtime(final_mp4)
            if age < self.cache_ttl:
                logger.info("File cache hit: %s", final_mp4)
                return final_mp4

        opts = self._base_opts()
        opts["outtmpl"] = out_tmpl

        if format_id and format_id != "best":
            opts["format"] = format_id

        # Progress hook – validates file size before returning
        def _progress_hook(d: dict) -> None:
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                if total and total > self.max_bytes:
                    raise VideoTooLargeError(
                        f"Video is too large ({total / 1e6:.1f} MB). "
                        f"Limit is {self.max_bytes / 1e6:.0f} MB."
                    )

        opts["progress_hooks"] = [_progress_hook]

        logger.info("Starting download: %s (format=%s)", url, format_id or "auto")
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                error_code = ydl.download([url])
                if error_code:
                    raise VideoDownloadError(f"yt-dlp exited with code {error_code}")
        except VideoTooLargeError:
            raise
        except DownloadError as exc:
            logger.warning("DownloadError for %s: %s", url, exc)
            raise VideoDownloadError(str(exc)) from exc
        except Exception as exc:
            logger.exception("Unexpected download error for %s", url)
            raise VideoDownloadError(f"Unexpected error: {exc}") from exc

        # Locate the written file (extension may vary if merge failed)
        for ext in ("mp4", "mkv", "webm", "mov"):
            candidate = os.path.join(self.download_dir, f"{file_id}.{ext}")
            if os.path.isfile(candidate):
                logger.info("Download complete: %s", candidate)
                return candidate

        raise VideoDownloadError("Download finished but output file was not found.")
