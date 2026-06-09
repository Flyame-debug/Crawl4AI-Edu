"""Single-page processing handler.

Fetches HTML, downloads/upload images (API mode) or saves locally, extracts links.
Supports two modes:

- **API mode** (``api_client`` provided): images are downloaded as bytes,
  converted to base64, uploaded via the backend API, and the page snapshot is
  saved through ``save_page_snapshot``. Images are NOT written to local disk.

- **Local mode** (``api_client`` is ``None``): the original behaviour is preserved
  — fetch HTML, extract links, no local file persistence.  (Image download and
  local HTML saving can be added later without changing the API-mode path.)
"""

from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path
from typing import Any, TYPE_CHECKING

import aiohttp

# Ensure sandbox/ and project root are on sys.path for all import styles.
_sandbox = str(Path(__file__).resolve().parent.parent)
_project_root = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_sandbox, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from fetcher import FetchError, async_fetch
from link import extract_links

from .utils import get_logger, normalize_url

if TYPE_CHECKING:
    from .api_client import APIClient

logger = get_logger("standalone_crawler.handlers")

# HTTP statuses that should NOT trigger a retry for image downloads.
_NO_RETRY_STATUSES: frozenset[int] = frozenset({400, 401, 403, 404, 405, 410})

# Default concurrency for image uploads in API mode.
_DEFAULT_IMAGE_CONCURRENCY: int = 5


# ===================================================================
# Public API
# ===================================================================


async def process_page(
    url: str,
    current_depth: int,
    bloom_filter: Any,
    allowed_domains: list[str] | None = None,
    white_list_patterns: list[str] | None = None,
    api_client: APIClient | None = None,
    task_id: str | None = None,
    seed_meta: dict[str, Any] | None = None,
    image_concurrency: int = _DEFAULT_IMAGE_CONCURRENCY,
    output_dir: str | None = None,
    mapping_path: str | None = None,
) -> dict[str, Any]:
    """Process a single page: fetch → (upload images) → extract links.

    Args:
        url: Absolute URL of the page to process.
        current_depth: BFS depth of this page (0 = seed).
        bloom_filter: Object with ``add(url)`` and ``contains(url)`` methods.
        allowed_domains: Optional domain whitelist for link extraction.
        white_list_patterns: Optional URL-path regex whitelist.
        api_client: When provided, images are uploaded via API and the page
            snapshot is saved.  When ``None``, local-only behaviour is used.
        task_id: Crawl task ID (required when *api_client* is provided).
        seed_meta: Optional seed metadata dict (may contain ``category``, ``school``).
        image_concurrency: Max concurrent image uploads (API mode only).

    Returns:
        A dict with keys ``success``, ``url``, ``depth``, ``links``,
        ``images`` (list of {original_url, stored_url} dicts in API mode,
        empty dict in local mode), and ``error``.
    """
    _domains = allowed_domains if allowed_domains is not None else []
    _patterns = white_list_patterns if white_list_patterns is not None else []

    result: dict[str, Any] = {
        "success": False,
        "url": url,
        "depth": current_depth,
        "links": [],
        "images": [],
        "error": None,
    }

    # 1. Fetch HTML ------------------------------------------------------------
    try:
        html: str = await async_fetch(url)
    except FetchError as exc:
        result["error"] = str(exc)
        logger.warning("Fetch failed for %s: %s", url, exc)
        return result
    except Exception as exc:
        result["error"] = f"Unexpected fetch error: {exc}"
        logger.error("Unexpected error fetching %s: %s", url, exc)
        return result

    # 2. Handle images & page persistence --------------------------------------
    images_for_result: list[dict[str, str]] = []

    if api_client is not None:
        # --- API mode: download bytes → base64 → upload → save snapshot -------
        try:
            category: str | None = None
            if seed_meta:
                category = seed_meta.get("category")
            images_for_result = await _upload_images_for_page(
                html, url, api_client, concurrency=image_concurrency,
            )
            await api_client.save_page_snapshot(
                url=url,
                markdown=html,
                category=category,
                images=images_for_result if images_for_result else None,
            )
            logger.info("Page snapshot saved via API: %s (images=%d)", url, len(images_for_result))
        except Exception as exc:
            logger.error("API upload failed for %s: %s — continuing.", url, exc)
            # Do not abort — link extraction still proceeds.
    else:
        # --- Local mode: save HTML + download images to disk ------------------
        html_path: str | None = None
        img_paths: list[str] = []
        if output_dir:
            try:
                html_path, img_paths = await _save_page_locally(
                    html, url, output_dir, concurrency=image_concurrency,
                )
                logger.info("Local save: html=%s images=%d for %s", html_path, len(img_paths), url)
                # Append URL→file mapping.
                if mapping_path:
                    img_str = ",".join(img_paths)
                    with open(mapping_path, "a", encoding="utf-8") as mf:
                        mf.write(f"{url}|{html_path}|{img_str}\n")
            except Exception as exc:
                logger.error("Local save failed for %s: %s", url, exc)
        result["html_path"] = html_path
        result["images"] = img_paths
        images_for_result = [{"original_url": p, "stored_url": p} for p in img_paths]

    result["images"] = images_for_result

    # 3. Extract & filter links ------------------------------------------------
    try:
        raw_links: list[str] = extract_links(
            html, url, allowed_domains=_domains, white_list_patterns=_patterns,
        )
    except Exception as exc:
        logger.warning("Link extraction failed for %s: %s", url, exc)
        raw_links = []

    new_links: list[str] = []
    for link in raw_links:
        try:
            normalized: str = normalize_url(link, url)
        except Exception:
            continue
        if not normalized or not normalized.startswith(("http://", "https://")):
            continue
        if not bloom_filter.contains(normalized):
            new_links.append(normalized)

    result["links"] = new_links
    result["success"] = True
    logger.info(
        "Page processed: %s depth=%d links=%d images=%d",
        url, current_depth, len(new_links), len(images_for_result),
    )
    return result


# ===================================================================
# Internal: local page persistence (local mode)
# ===================================================================


async def _save_page_locally(
    html: str,
    base_url: str,
    output_dir: str,
    concurrency: int = _DEFAULT_IMAGE_CONCURRENCY,
) -> tuple[str | None, list[str]]:
    """Save HTML to disk and download all referenced images in local mode.

    Returns a tuple of ``(html_path, list_of_image_paths)``.  Image paths are
    relative to the project root (e.g. ``sandbox/data/images/abc.jpg``).
    """
    from pathlib import Path
    import hashlib

    html_dir = Path(output_dir) / "html"
    img_dir = Path(output_dir) / "images"
    html_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    # -- Save HTML -----------------------------------------------------------
    url_hash = hashlib.md5(base_url.encode("utf-8")).hexdigest()
    html_file = html_dir / f"{url_hash}.html"
    html_file.write_text(html, encoding="utf-8")
    html_rel = str(html_file.relative_to(html_file.parent.parent.parent))

    # -- Extract image URLs --------------------------------------------------
    soup = BeautifulSoup(html, "html.parser")
    img_urls: list[str] = []
    for img in soup.find_all("img"):
        src: str | None = img.get("src")
        if not src:
            continue
        src = src.strip()
        if not src or src.startswith(("data:", "javascript:")):
            continue
        img_urls.append(urljoin(base_url, src))

    if not img_urls:
        return html_rel, []

    unique_urls = list(dict.fromkeys(img_urls))
    semaphore = asyncio.Semaphore(concurrency)
    dl_timeout = aiohttp.ClientTimeout(total=15)
    img_paths: list[str] = []

    async def _download_image_local(
        img_url: str, referer: str, timeout: aiohttp.ClientTimeout,
        max_retries: int = 2,
    ) -> bytes | None:
        """Download one image with retry, returning bytes or None on failure."""
        headers: dict[str, str] = {"Referer": referer}
        retry_delays: tuple[float, ...] = (1.0, 2.0)
        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(img_url, headers=headers) as resp:
                        if resp.status == 200:
                            return await resp.read()
                        if resp.status in _NO_RETRY_STATUSES:
                            logger.warning("HTTP %d for image %s — skipping.", resp.status, img_url)
                            return None
                        if resp.status >= 500:
                            logger.warning(
                                "HTTP %d for image %s (attempt %d/%d).",
                                resp.status, img_url, attempt + 1, max_retries + 1,
                            )
                        else:
                            logger.warning("Unexpected HTTP %d for image %s — skipping.", resp.status, img_url)
                            return None
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as exc:
                logger.warning("Network error for image %s: %s (attempt %d/%d).",
                               img_url, exc, attempt + 1, max_retries + 1)
            except Exception as exc:
                logger.error("Unexpected error downloading image %s: %s", img_url, exc)
                return None
            if attempt < max_retries:
                await asyncio.sleep(retry_delays[attempt])
        logger.error("All %d attempt(s) exhausted for image %s.", max_retries + 1, img_url)
        return None

    async def _download_one(img_url: str) -> str | None:
        async with semaphore:
            body: bytes | None = await _download_image_local(img_url, base_url, dl_timeout)
            if body is None:
                return None
            img_hash = hashlib.md5(img_url.encode("utf-8")).hexdigest()
            ext = _derive_ext(img_url)
            img_file = img_dir / f"{img_hash}{ext}"
            img_file.write_bytes(body)
            return str(img_file.relative_to(img_file.parent.parent.parent))

    def _derive_ext(img_url: str) -> str:
        """Derive a file extension from an image URL, defaulting to ``.jpg``."""
        from urllib.parse import urlparse

        path = urlparse(img_url).path
        name = Path(path).name if path else ""
        for ext in (".png", ".gif", ".webp", ".svg", ".bmp", ".ico"):
            if ext in name.lower():
                return ext
        return ".jpg"

    tasks = [_download_one(u) for u in unique_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, str):
            img_paths.append(r)
        elif isinstance(r, Exception):
            logger.error("Image download worker crashed: %s", r)

    return html_rel, img_paths


# ===================================================================
# Internal: image extraction, download, upload (API mode)
# ===================================================================


async def _upload_images_for_page(
    html: str,
    base_url: str,
    api_client: APIClient,
    concurrency: int = _DEFAULT_IMAGE_CONCURRENCY,
) -> list[dict[str, str]]:
    """Extract image URLs from HTML, download each as bytes, upload via API.

    Returns a list of ``{"original_url": str, "stored_url": str}`` dicts
    suitable for the ``images`` parameter of ``save_page_snapshot``.

    All lower-level helpers (*_extract_image_urls*, *_download_image_bytes*,
    *_derive_filename*) are defined as inner functions to keep the module's
    top-level function count within the project limit.
    """

    # -- Inner helpers ---------------------------------------------------------

    def _extract_image_urls(html_str: str, base: str) -> list[str]:
        """Return every absolute image URL found in ``<img src>`` attributes."""
        soup: BeautifulSoup = BeautifulSoup(html_str, "html.parser")
        urls: list[str] = []
        for img in soup.find_all("img"):
            src: str | None = img.get("src")
            if not src:
                continue
            src = src.strip()
            if not src or src.startswith(("data:", "javascript:")):
                continue
            urls.append(urljoin(base, src))
        return urls

    async def _download_image_bytes(
        img_url: str,
        referer: str,
        client_timeout: aiohttp.ClientTimeout,
        max_retries: int = 2,
    ) -> bytes | None:
        """Download one image, return raw bytes or ``None`` on failure."""
        headers: dict[str, str] = {"Referer": referer}
        retry_delays: tuple[float, ...] = (1.0, 2.0)
        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=client_timeout) as session:
                    async with session.get(img_url, headers=headers) as resp:
                        if resp.status == 200:
                            return await resp.read()
                        if resp.status in _NO_RETRY_STATUSES:
                            logger.warning("HTTP %d for image %s — skipping.", resp.status, img_url)
                            return None
                        if resp.status >= 500:
                            logger.warning(
                                "HTTP %d for image %s (attempt %d/%d).",
                                resp.status, img_url, attempt + 1, max_retries + 1,
                            )
                        else:
                            logger.warning("Unexpected HTTP %d for image %s — skipping.", resp.status, img_url)
                            return None
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as exc:
                logger.warning("Network error for image %s: %s (attempt %d/%d).",
                               img_url, exc, attempt + 1, max_retries + 1)
            except Exception as exc:
                logger.error("Unexpected error downloading image %s: %s", img_url, exc)
                return None
            if attempt < max_retries:
                await asyncio.sleep(retry_delays[attempt])
        logger.error("All %d attempt(s) exhausted for image %s.", max_retries + 1, img_url)
        return None

    def _derive_filename(img_url: str) -> str:
        """Derive a plausible filename from an image URL."""
        from urllib.parse import urlparse

        path: str = urlparse(img_url).path
        name: str = Path(path).name if path else ""
        if name and "." in name:
            return name.rsplit("?", 1)[0]
        return "image.jpg"

    # -- Main logic ------------------------------------------------------------

    img_urls: list[str] = _extract_image_urls(html, base_url)
    if not img_urls:
        logger.debug("No <img> URLs found in page %s", base_url)
        return []

    unique_urls: list[str] = list(dict.fromkeys(img_urls))
    logger.info("Uploading %d unique image(s) from %s (concurrency=%d)",
                 len(unique_urls), base_url, concurrency)

    semaphore = asyncio.Semaphore(concurrency)
    dl_timeout = aiohttp.ClientTimeout(total=15)

    async def _download_and_upload_one(img_url: str) -> dict[str, str] | None:
        async with semaphore:
            body: bytes | None = await _download_image_bytes(img_url, base_url, dl_timeout)
            if body is None:
                return None
            b64_str: str = base64.b64encode(body).decode("ascii")
            fname: str = _derive_filename(img_url)
            try:
                upload_resp: dict = await api_client.upload_image_base64(b64_str, fname)
            except Exception as exc:
                logger.error("Image upload failed for %s: %s", img_url, exc)
                return None
            stored_url: str | None = upload_resp.get("url")
            if not stored_url:
                logger.warning("Image upload response missing 'url' for %s: %s", img_url, upload_resp)
                return None
            logger.info("Image uploaded: %s → %s", img_url, stored_url)
            return {"original_url": img_url, "stored_url": stored_url}

    tasks = [_download_and_upload_one(u) for u in unique_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    images: list[dict[str, str]] = []
    for r in results:
        if isinstance(r, dict) and r is not None:
            images.append(r)
        elif isinstance(r, Exception):
            logger.error("Image upload worker crashed: %s", r)

    logger.info("Image upload complete: %d succeeded, %d failed for %s",
                 len(images), len(unique_urls) - len(images), base_url)
    return images


# ===================================================================
# Smoke test
# ===================================================================

if __name__ == "__main__":
    async def _test() -> None:
        from link import create_bloom_filter

        bf = create_bloom_filter("memory")
        bf.add("https://httpbin.org/html")

        print("=== Local mode test ===")
        result = await process_page("https://httpbin.org/html", 0, bf)
        print(f"  success: {result['success']}")
        print(f"  links:   {len(result['links'])}")
        print(f"  images:  {len(result['images'])}")
        print(f"  error:   {result['error']}")

        print("handlers.py — smoke test passed.")

    asyncio.run(_test())
