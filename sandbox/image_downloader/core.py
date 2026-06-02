"""Core image download logic — extract, deduplicate, download concurrently."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from sandbox.image_downloader.utils import infer_extension

if TYPE_CHECKING:
    from collections.abc import Coroutine

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
        return {}

    unique_urls: list[str] = list(dict.fromkeys(raw_urls))  # order-preserving dedup

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

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks: list[Coroutine] = [
            _download_single(session, semaphore, url, output_path, dict(headers))
            for url in unique_urls
        ]
        results: list[tuple[str, str] | None] = await asyncio.gather(*tasks)

    # -- 5. Build result mapping ----------------------------------------------
    unique_map: dict[str, str] = {}
    for entry in results:
        if entry is not None:
            abs_url, local_path = entry
            unique_map[abs_url] = local_path

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
    """Download one image and persist it to *output_path*.

    Returns ``(absolute_url, local_path)`` on success or ``None`` when the
    download fails or the HTTP status is not 200.
    """
    async with semaphore:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None

                body: bytes = await response.read()
                content_type: str | None = response.headers.get("Content-Type")

            ext: str = infer_extension(url, content_type)
            filename: str = f"{hashlib.md5(url.encode()).hexdigest()}{ext}"
            filepath: Path = output_path / filename

            filepath.write_bytes(body)
            return (url, str(filepath))

        except Exception:
            # Network errors, timeouts, decode failures — skip gracefully.
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
        print("=" * 60)
        print("Image Downloader — Smoke Test")
        print("=" * 60)

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
        print(f"\nSuccessfully downloaded: {success} unique image(s)")
        print(f"Failed / skipped:       {failed}")
        print(f"Total src entries:      {len(result)}")
        print(f"\nFirst {min(3, len(result))} mapping entries:")
        for i, (url, path) in enumerate(result.items()):
            if i >= 3:
                break
            print(f"  {url}")
            print(f"    → {path}")
            exists: str = "✓" if os.path.isfile(path) else "✗ MISSING"
            print(f"    file exists: {exists}")

        # Quick assertion
        for _, p in result.items():
            assert os.path.isfile(p), f"File not found: {p}"
        print("\n✅ All assertions passed — files written to disk.")

    asyncio.run(_main())
