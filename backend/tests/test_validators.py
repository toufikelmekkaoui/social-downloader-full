"""
tests/test_validators.py
------------------------
Unit tests for URL validation helpers.
"""

import pytest
from app.utils.validators import detect_platform, is_supported_url, sanitize_url


# ── detect_platform ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("url, expected", [
    # Facebook variants
    ("https://www.facebook.com/video/1234567890", "facebook"),
    ("https://m.facebook.com/watch/?v=1234567890", "facebook"),
    ("https://web.facebook.com/reel/1234567890", "facebook"),
    ("https://fb.watch/abc123/", "facebook"),
    # Instagram variants
    ("https://www.instagram.com/reel/CxYz123/", "instagram"),
    ("https://www.instagram.com/p/CxYz123/", "instagram"),
    ("https://www.instagram.com/tv/CxYz123/", "instagram"),
    # TikTok variants
    ("https://www.tiktok.com/@user/video/7123456789", "tiktok"),
    ("https://vm.tiktok.com/ZTRshort/", "tiktok"),
    ("https://vt.tiktok.com/ZTRshort/", "tiktok"),
    # Unsupported
    ("https://www.youtube.com/watch?v=abc", None),
    ("https://twitter.com/i/status/123", None),
    ("https://example.com", None),
    ("not-a-url", None),
    ("", None),
])
def test_detect_platform(url, expected):
    assert detect_platform(url) == expected


# ── is_supported_url ──────────────────────────────────────────────────────────

def test_is_supported_url_true():
    assert is_supported_url("https://www.instagram.com/reel/abc/") is True


def test_is_supported_url_false():
    assert is_supported_url("https://www.youtube.com/watch?v=abc") is False


# ── sanitize_url ──────────────────────────────────────────────────────────────

def test_sanitize_strips_tracking_params():
    dirty  = "https://www.instagram.com/reel/CxYz123/?igshid=abc&utm_source=ig_web"
    clean  = sanitize_url(dirty)
    assert "igshid" not in clean
    assert "utm_source" not in clean
    assert "instagram.com" in clean


def test_sanitize_strips_fragment():
    url   = "https://www.facebook.com/video/123#comments"
    clean = sanitize_url(url)
    assert "#comments" not in clean


def test_sanitize_handles_garbage_gracefully():
    # Should not raise; returns the original string
    result = sanitize_url("not-a-url-at-all")
    assert isinstance(result, str)
