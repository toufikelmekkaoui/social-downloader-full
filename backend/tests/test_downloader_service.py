"""
tests/test_downloader_service.py
---------------------------------
Unit tests for VideoDownloaderService.
All real yt-dlp calls are mocked so the suite stays offline and fast.
"""

import os
import time
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from app.services.downloader import (
    VideoDownloaderService,
    VideoExtractionError,
    VideoDownloadError,
    VideoTooLargeError,
    _format_duration,
    _stable_id,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_download_dir(tmp_path):
    return str(tmp_path / "downloads")


@pytest.fixture()
def svc(tmp_download_dir):
    return VideoDownloaderService(
        download_dir=tmp_download_dir,
        cache_ttl=60,
        max_bytes=100 * 1024 * 1024,
    )


# ── Helper tests ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("seconds, expected", [
    (None, "0:00"),
    (0,    "0:00"),
    (45,   "0:45"),
    (90,   "1:30"),
    (3661, "1:01:01"),
])
def test_format_duration(seconds, expected):
    assert _format_duration(seconds) == expected


def test_stable_id_is_deterministic():
    assert _stable_id("http://example.com") == _stable_id("http://example.com")


def test_stable_id_differs_for_different_urls():
    assert _stable_id("http://a.com") != _stable_id("http://b.com")


# ── extract_info tests ────────────────────────────────────────────────────────

RAW_YTDLP_INFO = {
    "id": "abc123",
    "title": "My Test Video",
    "thumbnails": [{"url": "https://example.com/thumb_low.jpg"},
                   {"url": "https://example.com/thumb_high.jpg"}],
    "thumbnail": "https://example.com/thumb.jpg",
    "duration": 83,
    "uploader": "testuser",
    "uploader_url": "https://instagram.com/testuser",
    "extractor_key": "Instagram",
    "extractor": "instagram",
    "webpage_url": "https://www.instagram.com/reel/abc123/",
    "original_url": "https://www.instagram.com/reel/abc123/",
    "view_count": 10000,
    "like_count": 500,
    "upload_date": "20240101",
    "description": "A cool video",
    "formats": [
        {"format_id": "720p", "url": "https://cdn.example.com/720.mp4",
         "height": 720, "ext": "mp4", "vcodec": "avc1", "acodec": "mp4a",
         "filesize": 50_000_000, "fps": 30},
        {"format_id": "1080p", "url": "https://cdn.example.com/1080.mp4",
         "height": 1080, "ext": "mp4", "vcodec": "avc1", "acodec": "mp4a",
         "filesize": 120_000_000, "fps": 30},
    ],
}


def _make_mock_ydl(info=None, error=None):
    """Build a mock yt_dlp.YoutubeDL context manager."""
    mock_ydl = MagicMock()
    if error:
        mock_ydl.__enter__.return_value.extract_info.side_effect = error
    else:
        mock_ydl.__enter__.return_value.extract_info.return_value = info or RAW_YTDLP_INFO
        mock_ydl.__enter__.return_value.sanitize_info.return_value = info or RAW_YTDLP_INFO
    mock_ydl.__exit__ = MagicMock(return_value=False)
    return mock_ydl


def test_extract_info_returns_clean_dict(svc):
    with patch("yt_dlp.YoutubeDL", return_value=_make_mock_ydl()):
        info = svc.extract_info("https://www.instagram.com/reel/abc123/")

    assert info["id"] == "abc123"
    assert info["title"] == "My Test Video"
    assert info["duration"] == "1:23"
    assert info["platform"] == "Instagram"
    assert isinstance(info["formats"], list)


def test_extract_info_uses_cache(svc):
    """Second call must not create a new YoutubeDL instance."""
    with patch("yt_dlp.YoutubeDL", return_value=_make_mock_ydl()) as mock_class:
        svc.extract_info("https://www.instagram.com/reel/abc123/")
        svc.extract_info("https://www.instagram.com/reel/abc123/")
        assert mock_class.call_count == 1   # only one real extraction


def test_extract_info_cache_expires(svc):
    svc.cache_ttl = 0    # expire immediately
    with patch("yt_dlp.YoutubeDL", return_value=_make_mock_ydl()) as mock_class:
        svc.extract_info("https://www.instagram.com/reel/abc123/")
        time.sleep(0.01)
        svc.extract_info("https://www.instagram.com/reel/abc123/")
        assert mock_class.call_count == 2   # cache missed second time


def test_extract_info_raises_on_extractor_error(svc):
    from yt_dlp.utils import ExtractorError
    with patch("yt_dlp.YoutubeDL", return_value=_make_mock_ydl(error=ExtractorError("nope"))):
        with pytest.raises(VideoExtractionError):
            svc.extract_info("https://www.instagram.com/reel/fake/")


# ── download_video tests ──────────────────────────────────────────────────────

def test_download_video_returns_existing_fresh_file(svc, tmp_download_dir):
    """If the file is already on disk and fresh, skip yt-dlp."""
    url = "https://www.instagram.com/reel/abc123/"
    file_id = _stable_id(url)
    fake_file = os.path.join(tmp_download_dir, f"{file_id}.mp4")
    os.makedirs(tmp_download_dir, exist_ok=True)
    with open(fake_file, "wb") as f:
        f.write(b"\x00" * 100)

    with patch("yt_dlp.YoutubeDL") as mock_class:
        result = svc.download_video(url)
        assert result == fake_file
        mock_class.assert_not_called()   # yt-dlp must NOT have been called


def test_download_video_raises_on_download_error(svc, tmp_download_dir):
    from yt_dlp.utils import DownloadError
    with patch("yt_dlp.YoutubeDL", return_value=_make_mock_ydl(error=DownloadError("fail"))):
        with pytest.raises(VideoDownloadError):
            svc.download_video("https://www.instagram.com/reel/missing/")
