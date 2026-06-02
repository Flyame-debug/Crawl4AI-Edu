"""Utility helpers for the image downloader module."""

import os
from urllib.parse import urlparse

# Recognised image file extensions (lowercase, with dot).
_VALID_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}

# Mapping from MIME Content-Type to file extension.
_CONTENT_TYPE_MAP: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
}


def infer_extension(url: str, content_type: str | None = None) -> str:
    """Return a file extension for *url*, consulting *content_type* if needed.

    1.  Try the path component of the URL.
    2.  Fall back to Content-Type → extension mapping.
    3.  Default to ``.jpg`` when neither source provides a usable extension.
    """
    # --- 1. Extract from URL path ------------------------------------------------
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

    # --- 2. Extract from Content-Type -------------------------------------------
    if content_type:
        ct: str = content_type.split(";", 1)[0].strip().lower()
        if ct in _CONTENT_TYPE_MAP:
            return _CONTENT_TYPE_MAP[ct]

    # --- 3. Fallback ------------------------------------------------------------
    return ".jpg"


if __name__ == "__main__":
    # Quick smoke tests
    assert infer_extension("https://example.com/photo.png") == ".png"
    assert infer_extension("https://example.com/photo.jpeg") == ".jpg"
    assert infer_extension("https://example.com/photo", "image/webp") == ".webp"
    assert infer_extension("https://example.com/photo") == ".jpg"
    assert infer_extension("https://example.com/photo.svg", "image/svg+xml") == ".svg"
    print("utils.py — all assertions passed.")
