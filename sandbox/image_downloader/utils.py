"""Utility helpers for the image downloader module."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

# Recognised image file extensions (lowercase, with dot).
_VALID_EXTENSIONS: set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".svg",
    ".ico",
    ".tiff",
}

# Mapping from MIME Content-Type to file extension.
_CONTENT_TYPE_MAP: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
    "image/tiff": ".tiff",
    "image/vnd.microsoft.icon": ".ico",
}


def _extract_filename_from_cd(content_disposition: str | None) -> str | None:
    """Extract a filename from a ``Content-Disposition`` header value.

    Supports both quoted (``filename="pic.jpg"``) and unquoted
    (``filename=pic.jpg``) forms.  Returns ``None`` when *content_disposition*
    is falsy or contains no recognisable filename.
    """
    if not content_disposition:
        return None

    # Prefer quoted form:  filename="name.ext"
    m = re.search(r'filename\s*=\s*"([^"]*)"', content_disposition, re.IGNORECASE)
    if m:
        return m.group(1)

    # Fall back to unquoted form:  filename=name.ext
    m = re.search(r"filename\s*=\s*([^\s;]+)", content_disposition, re.IGNORECASE)
    if m:
        return m.group(1)

    return None


def infer_extension(
    url: str,
    content_type: str | None = None,
    *,
    content_disposition: str | None = None,
) -> str:
    """Return a file extension for *url*.

    Resolution priority:
    1.  Extension extracted from the URL path (e.g. ``/photo.png`` → ``.png``).
    2.  ``Content-Type`` MIME → extension mapping.
    3.  ``Content-Disposition`` header filename, if present and carrying a valid
        image extension.
    4.  Default ``.jpg``.
    """
    # --- 1. URL path ---------------------------------------------------------
    parsed = urlparse(url)
    path: str = parsed.path
    if path:
        filename: str = os.path.basename(path)
        if filename:
            _name, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext == ".jpeg":
                return ".jpg"
            if ext in _VALID_EXTENSIONS:
                return ext

    # --- 2. Content-Type -----------------------------------------------------
    if content_type:
        ct: str = content_type.split(";", 1)[0].strip().lower()
        if ct in _CONTENT_TYPE_MAP:
            return _CONTENT_TYPE_MAP[ct]

    # --- 3. Content-Disposition ----------------------------------------------
    if content_disposition:
        cd_filename: str | None = _extract_filename_from_cd(content_disposition)
        if cd_filename:
            _name, ext = os.path.splitext(cd_filename)
            ext = ext.lower()
            if ext == ".jpeg":
                return ".jpg"
            if ext in _VALID_EXTENSIONS:
                return ext

    # --- 4. Fallback ---------------------------------------------------------
    return ".jpg"


# ---------------------------------------------------------------------------
# Quick smoke tests
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # URL path
    assert infer_extension("https://example.com/photo.png") == ".png"
    assert infer_extension("https://example.com/photo.jpeg") == ".jpg"
    # Content-Type
    assert infer_extension("https://example.com/photo", "image/webp") == ".webp"
    assert infer_extension("https://example.com/photo", "image/x-icon") == ".ico"
    assert infer_extension("https://example.com/photo", "image/tiff") == ".tiff"
    assert (
        infer_extension("https://example.com/photo", "image/vnd.microsoft.icon")
        == ".ico"
    )
    # Content-Disposition
    assert (
        infer_extension(
            "https://example.com/dynamic",
            content_disposition='attachment; filename="banner.png"',
        )
        == ".png"
    )
    assert (
        infer_extension(
            "https://example.com/dynamic",
            content_disposition="attachment; filename=icon.ico",
        )
        == ".ico"
    )
    # Priority: URL > Content-Type > Content-Disposition > default
    assert (
        infer_extension(
            "https://example.com/photo.png",
            "image/jpeg",
            content_disposition='attachment; filename="icon.ico"',
        )
        == ".png"
    )  # URL wins
    assert (
        infer_extension(
            "https://example.com/photo",
            "image/png",
            content_disposition='attachment; filename="icon.ico"',
        )
        == ".png"
    )  # Content-Type wins over CD
    # Default
    assert infer_extension("https://example.com/photo") == ".jpg"
    # No CD → None extracted
    assert _extract_filename_from_cd(None) is None
    assert _extract_filename_from_cd("") is None
    print("utils.py — all assertions passed.")
