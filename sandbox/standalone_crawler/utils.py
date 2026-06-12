"""Low-level helper functions for the standalone crawler.

Provides URL hashing, normalisation, directory creation, and logger setup.
All functions are pure standard-library utilities with no sandbox-internal
dependencies.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse


def url_to_filename(url: str) -> str:
    """Return the MD5 hex digest of *url* (filename only, no path)."""
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def normalize_url(url: str, base_url: str = "") -> str:
    """Resolve relative *url* against *base_url* and strip the fragment.

    Args:
        url: Absolute or relative URL.
        base_url: Base URL for resolving relative references.

    Returns:
        An absolute URL with no ``#fragment`` component.
    """
    if base_url:
        url = urljoin(base_url, url)
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


def ensure_dir(path: str) -> None:
    """Recursively create *path* if it does not exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


# Module-level logger configuration (once).
_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Return a :class:`logging.Logger` configured for console INFO output.

    Each distinct *name* receives a logger with a single
    ``StreamHandler`` that includes timestamp, module name, level, and
    message.  Handlers are cached so repeated calls for the same *name*
    do not add duplicate handlers.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)

    _loggers[name] = logger
    return logger


if __name__ == "__main__":
    # Quick smoke tests
    test_url = "https://example.com/page?q=1#section"
    assert url_to_filename(test_url) == hashlib.md5(test_url.encode()).hexdigest()
    print(f"url_to_filename('{test_url}') = {url_to_filename(test_url)}")

    normalized = normalize_url("/path", "https://example.com/base/")
    assert normalized == "https://example.com/path"
    print(f"normalize_url('/path', 'https://example.com/base/') = {normalized}")

    frag = normalize_url("https://example.com/a#foo")
    assert frag == "https://example.com/a"
    print(f"normalize_url('.../a#foo') = {frag}")

    test_dir = os.path.join(os.path.dirname(__file__), "_test_ensure_dir")
    ensure_dir(test_dir)
    assert os.path.isdir(test_dir)
    os.rmdir(test_dir)
    print("ensure_dir works.")

    lg = get_logger("test_utils")
    assert isinstance(lg, logging.Logger)
    print("get_logger works.")

    print("utils.py — all assertions passed.")
