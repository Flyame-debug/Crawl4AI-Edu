"""Core image download logic — extract, deduplicate, download concurrently."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from sandbox.image_downloader.utils import infer_extension

if TYPE_CHECKING:
    from collections.abc import Coroutine

# ---------------------------------------------------------------------------
# Logger — configured once with a console StreamHandler.
# ---------------------------------------------------------------------------
_logger: logging.Logger = logging.getLogger("image_downloader")
if not _logger.handlers:
    _handler: logging.StreamHandler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Fallback User-Agent list — used when the shared ua_pool is unavailable.
# ---------------------------------------------------------------------------
_FALLBACK_UAS: list[str] = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
]

# HTTP status codes that should *not* trigger a retry (client errors).
_NO_RETRY_STATUSES: frozenset[int] = frozenset({400, 401, 403, 404, 405, 410})


# ===================================================================
# Public API
# ===================================================================


async def download_images(
    html: str,
    base_url: str,
    output_dir: str = "sandbox/images",
    concurrency: int = 5,
) -> dict[str, str]:
    """Extract ``<img src>`` URLs from *html*, download them concurrently, and
    return a mapping ``{original_src_url: local_absolute_path}``.

    Parameters
    ----------
    html:
        Raw HTML string to scan for ``<img>`` tags.
    base_url:
        Used to resolve relative ``src`` attributes into absolute URLs.
    output_dir:
        Directory where downloaded images are saved (created automatically).
    concurrency:
        Maximum number of concurrent downloads (``asyncio.Semaphore``).

    Returns
    -------
    dict[str, str]
        Every *original* ``src`` URL (including duplicates) mapped to the same
        local file path when the same absolute URL appears more than once.
    """
    # -- 1. Extract & deduplicate absolute image URLs -------------------------
    raw_urls: list[str] = _extract_image_urls(html, base_url)
    if not raw_urls:
        _logger.info("No <img> URLs found in HTML — nothing to download.")
        return {}

    unique_urls: list[str] = list(dict.fromkeys(raw_urls))  # order-preserving dedup
    dedup_skipped: int = len(raw_urls) - len(unique_urls)
    _logger.info(
        "Extracted %d image URL(s) from HTML (%d unique, %d duplicate(s) skipped).",
        len(raw_urls),
        len(unique_urls),
        dedup_skipped,
    )

    # -- 2. Prepare output directory ------------------------------------------
    output_path: Path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    # -- 3. Obtain a User-Agent (prefer the shared pool) ----------------------
    headers: dict[str, str] = {"Referer": base_url}
    try:
        from sandbox.fetcher.ua_pool import get_random_ua

        headers["User-Agent"] = get_random_ua()
    except ImportError:
        import random

        headers["User-Agent"] = random.choice(_FALLBACK_UAS)

    # -- 4. Download unique URLs concurrently ---------------------------------
    semaphore: asyncio.Semaphore = asyncio.Semaphore(concurrency)
    timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=10)

    _logger.info("Starting download of %d image(s) (concurrency=%d).", len(unique_urls), concurrency)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks: list[Coroutine] = [
            _download_single(session, semaphore, url, output_path, dict(headers))
            for url in unique_urls
        ]
        results: list[tuple[str, str] | None] = await asyncio.gather(*tasks)

    # -- 5. Build result mapping ----------------------------------------------
    unique_map: dict[str, str] = {}
    success_count: int = 0
    for entry in results:
        if entry is not None:
            abs_url, local_path = entry
            unique_map[abs_url] = local_path
            success_count += 1
            _logger.info("Downloaded: %s → %s", abs_url, local_path)

    failed_count: int = len(unique_urls) - success_count
    _logger.info(
        "Download complete: %d succeeded, %d failed.",
        success_count,
        failed_count,
    )

    url_to_path: dict[str, str] = {}
    for raw_url in raw_urls:
        mapped: str | None = unique_map.get(raw_url)
        if mapped is not None:
            url_to_path[raw_url] = mapped

    return url_to_path


# ===================================================================
# Internal helpers
# ===================================================================


def _extract_image_urls(html: str, base_url: str) -> list[str]:
    """Return every absolute image URL found in ``<img src>`` attributes.

    Skips empty/missing ``src``, ``data:`` URIs, and ``javascript:``
    pseudo-protocols.
    """
    soup: BeautifulSoup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []

    for img in soup.find_all("img"):
        src: str | None = img.get("src")
        if not src:
            continue
        src = src.strip()
        if not src or src.startswith(("data:", "javascript:")):
            _logger.debug("Skipping non-downloadable src: %s", src[:80])
            continue
        absolute_url: str = urljoin(base_url, src)
        urls.append(absolute_url)

    return urls


async def _download_single(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    url: str,
    output_path: Path,
    headers: dict[str, str],
) -> tuple[str, str] | None:
    """Download one image with up to 2 retries (exponential backoff).

    Retry policy
    ------------
    * Connection errors, timeouts, and HTTP 5xx → retry (max 2).
    * HTTP 4xx (403, 404, …) → no retry, skip immediately.
    * Backoff: 1 s before first retry, 2 s before second retry.

    Each attempt acquires the *semaphore* so concurrency limits are honoured
    across retries.
    """
    max_retries: int = 2
    retry_delays: tuple[float, ...] = (1.0, 2.0)

    for attempt in range(max_retries + 1):
        async with semaphore:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        body: bytes = await response.read()
                        content_type: str | None = response.headers.get("Content-Type")
                        content_disposition: str | None = response.headers.get(
                            "Content-Disposition"
                        )

                        ext: str = infer_extension(
                            url, content_type, content_disposition=content_disposition
                        )
                        filename: str = (
                            f"{hashlib.md5(url.encode()).hexdigest()}{ext}"
                        )
                        filepath: Path = output_path / filename

                        filepath.write_bytes(body)
                        return (url, str(filepath))

                    # -- Non-200 status ----------------------------------------
                    status: int = response.status
                    if status in _NO_RETRY_STATUSES:
                        _logger.warning(
                            "HTTP %d for %s — client error, skipping.", status, url
                        )
                        return None

                    if status >= 500:
                        _logger.warning(
                            "HTTP %d (server error) for %s (attempt %d/%d).",
                            status,
                            url,
                            attempt + 1,
                            max_retries + 1,
                        )
                    else:
                        _logger.warning(
                            "Unexpected HTTP %d for %s — skipping.", status, url
                        )
                        return None

            except (
                aiohttp.ClientConnectionError,
                asyncio.TimeoutError,
            ) as exc:
                _logger.warning(
                    "Network error for %s: %s (attempt %d/%d).",
                    url,
                    exc,
                    attempt + 1,
                    max_retries + 1,
                )
            except OSError as exc:
                _logger.error(
                    "File-system error writing %s: %s.", url, exc
                )
                return None
            except Exception as exc:
                _logger.error(
                    "Unexpected error for %s: %s — skipping.", url, exc
                )
                return None

        # -- Backoff before next retry ----------------------------------------
        if attempt < max_retries:
            delay: float = retry_delays[attempt]
            _logger.info("Retrying %s in %.1fs …", url, delay)
            await asyncio.sleep(delay)

    _logger.error("All %d attempt(s) exhausted for %s — giving up.", max_retries + 1, url)
    return None


# ===================================================================
# Test / demo
# ===================================================================

if __name__ == "__main__":
    import os
    import sys

    # Ensure the sandbox package is importable when run as a script.
    _PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(_PROJECT_ROOT))

    TEST_HTML: str = """\
<html>
<body>
  <img src="https://picsum.photos/200/300?random=1" alt="photo 1">
  <img src="https://picsum.photos/200/300?random=2" alt="photo 2">
  <img src="https://picsum.photos/200/300?random=3" alt="photo 3">
  <img src="https://picsum.photos/200/300?random=1" alt="duplicate of photo 1">
  <img src="data:image/png;base64,iVBORw0KGgo=" alt="should-be-skipped">
</body>
</html>"""

    TEST_OUTPUT_DIR: str = str(
        Path(__file__).resolve().parent.parent / "test_images"
    )

    async def _main() -> None:
        _logger.info("=" * 60)
        _logger.info("Image Downloader — Smoke Test")
        _logger.info("=" * 60)

        result: dict[str, str] = await download_images(
            html=TEST_HTML,
            base_url="https://example.com",
            output_dir=TEST_OUTPUT_DIR,
            concurrency=3,
        )

        success: int = len(set(result.values()))
        failed: int = len(
            set(_extract_image_urls(TEST_HTML, "https://example.com"))
        ) - success
        _logger.info("Successfully downloaded: %d unique image(s)", success)
        _logger.info("Failed / skipped:       %d", failed)
        _logger.info("Total src entries:      %d", len(result))
        _logger.info("First %d mapping entries:", min(3, len(result)))
        for i, (url, path) in enumerate(result.items()):
            if i >= 3:
                break
            _logger.info("  %s", url)
            _logger.info("    → %s", path)
            exists: str = "✓" if os.path.isfile(path) else "✗ MISSING"
            _logger.info("    file exists: %s", exists)

        # Quick assertion
        for _, p in result.items():
            assert os.path.isfile(p), f"File not found: {p}"
        _logger.info("All assertions passed — files written to disk.")

    asyncio.run(_main())
