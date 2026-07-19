"""
tests/test_analyze.py
---------------------
Tests for the POST /api/analyze endpoint.
All external yt-dlp calls are mocked so the tests run offline.
"""

import pytest
from unittest.mock import patch, MagicMock


# ── Helpers ───────────────────────────────────────────────────────────────────

FAKE_INFO = {
    "id": "abc123",
    "title": "Test Video",
    "thumbnail": "https://example.com/thumb.jpg",
    "duration": "1:23",
    "duration_sec": 83,
    "uploader": "testuser",
    "uploader_url": None,
    "platform": "Instagram",
    "webpage_url": "https://www.instagram.com/reel/abc123/",
    "view_count": 10000,
    "like_count": 500,
    "upload_date": "20240101",
    "description": "A test video",
    "formats": [
        {"format_id": "best", "label": "Best", "ext": "mp4",
         "filesize": None, "fps": None, "vcodec": None, "acodec": None},
    ],
}


def _mock_extract(url):
    return FAKE_INFO


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_analyze_missing_body(client):
    resp = client.post("/api/analyze", content_type="application/json", data="")
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] is True
    assert body["code"] == "BAD_REQUEST"


def test_analyze_missing_url_field(client):
    resp = client.post("/api/analyze", json={"foo": "bar"})
    assert resp.status_code == 400


def test_analyze_empty_url(client):
    resp = client.post("/api/analyze", json={"url": "   "})
    assert resp.status_code == 400


def test_analyze_unsupported_platform(client):
    resp = client.post("/api/analyze", json={"url": "https://www.example.com/video/123"})
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["code"] == "UNSUPPORTED_PLATFORM"


@pytest.mark.parametrize("url", [
    "https://www.facebook.com/video/1234567890",
    "https://www.instagram.com/reel/abc123/",
    "https://www.tiktok.com/@user/video/9876543210",
    "https://vm.tiktok.com/ZTRshort/",
    "https://fb.watch/abc123/",
])
def test_analyze_supported_platforms_accepted(client, url):
    """
    With a mocked downloader service the request must pass validation
    and reach yt-dlp (which we mock to return FAKE_INFO).
    """
    with patch(
        "app.api.routes._svc",
        return_value=MagicMock(extract_info=_mock_extract),
    ):
        resp = client.post("/api/analyze", json={"url": url})
        # Should be 200 (valid platform + mocked yt-dlp)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert "data" in body


def test_analyze_extraction_error(client):
    """When yt-dlp raises VideoExtractionError, return 422."""
    from app.services.downloader import VideoExtractionError

    with patch(
        "app.api.routes._svc",
        return_value=MagicMock(
            extract_info=MagicMock(side_effect=VideoExtractionError("not found"))
        ),
    ):
        resp = client.post(
            "/api/analyze",
            json={"url": "https://www.instagram.com/reel/fake123/"},
        )
        assert resp.status_code == 422
        body = resp.get_json()
        assert body["code"] == "EXTRACTION_FAILED"
