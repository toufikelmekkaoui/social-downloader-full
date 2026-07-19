"""
utils/validators.py
-------------------
URL validation helpers that determine whether a submitted link
belongs to a supported social-media platform.
"""

import re
from urllib.parse import urlparse
from typing import Optional


# ── Supported platform patterns ───────────────────────────────────────────────

_PLATFORM_PATTERNS: dict[str, re.Pattern] = {
    "facebook": re.compile(
        r"^https?://(www\.|m\.|web\.)?(facebook\.com|fb\.watch)/.+",
        re.IGNORECASE,
    ),
    "instagram": re.compile(
        r"^https?://(www\.)?instagram\.com/(p|reel|tv|reels)/.+",
        re.IGNORECASE,
    ),
    "tiktok": re.compile(
        r"^https?://((www|vm|vt)\.)?tiktok\.com/.+",
        re.IGNORECASE,
    ),
}

# ── Public API ────────────────────────────────────────────────────────────────


def detect_platform(url: str) -> Optional[str]:
    """
    Return the canonical platform name ('facebook', 'instagram', 'tiktok')
    if *url* matches one of the supported patterns, else ``None``.
    """
    url = url.strip()
    for platform, pattern in _PLATFORM_PATTERNS.items():
        if pattern.match(url):
            return platform
    return None


def is_supported_url(url: str) -> bool:
    """Return ``True`` iff *url* is a recognised social-media video link."""
    return detect_platform(url) is not None


def sanitize_url(url: str) -> str:
    """
    Strip tracking query-parameters that are not needed for extraction
    (e.g. ``?igshid=…``, ``?fbclid=…``).  The clean URL is returned.
    """
    try:
        parsed = urlparse(url.strip())
        # Re-build without the query string and fragment
        clean = parsed._replace(query="", fragment="")
        return clean.geturl()
    except Exception:
        return url.strip()
