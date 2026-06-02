"""Single-page processing handler.

Fetches HTML, saves it, downloads images, and extracts new outgoing links.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Ensure sandbox/ and project root are on sys.path for all import styles.
_sandbox = str(Path(__file__).resolve().parent.parent)
_project_root = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_sandbox, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fetcher import FetchError, async_fetch
from image_downloader import download_images
from link import extract_links

from .utils import get_logger, normalize_url, url_to_filename

logger = get_logger("standalone_crawler.handlers")


async def process_page(
    url: str,
    current_depth: int,
    output_dirs: dict[str, str],
    bloom_filter: Any,
) -> dict:
    """Process a single page: fetch → save HTML → download images → extract links.

    Args:
        url: Absolute URL of the page to process.
        current_depth: BFS depth of this page (0 = seed).
        output_dirs: ``{"html": "/path/to/html", "images": "/path/to/images"}``.
        bloom_filter: Object with ``add(url)`` and ``contains(url)`` methods.

    Returns:
        A dict with keys ``success``, ``url``, ``depth``, ``html_path``,
        ``images`` (dict), ``links`` (list of new, unvisited URLs), and
        ``error`` (str or None).
    """
    result: dict[str, Any] = {
        "success": False,
        "url": url,
        "depth": current_depth,
        "html_path": None,
        "images": {},
        "links": [],
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

    # 2. Save HTML -------------------------------------------------------------
    try:
        filename: str = url_to_filename(url) + ".html"
        html_path: str = os.path.join(output_dirs["html"], filename)
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html)
        result["html_path"] = html_path
        logger.info("HTML saved: %s → %s", url, html_path)
    except OSError as exc:
        result["error"] = f"Failed to save HTML: {exc}"
        logger.error("Save HTML failed for %s: %s", url, exc)
        return result

    # 3. Download images -------------------------------------------------------
    try:
        result["images"] = await download_images(
            html, url, output_dir=output_dirs["images"]
        )
    except Exception as exc:
        logger.warning("Image download failed for %s: %s — continuing", url, exc)

    # 4. Extract & filter links ------------------------------------------------
    try:
        raw_links: list[str] = extract_links(html, url, allowed_domains=[], white_list_patterns=[])
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
        "Page processed: %s depth=%d html_ok=%s images=%d links=%d",
        url,
        current_depth,
        result["html_path"] is not None,
        len(result["images"]),
        len(new_links),
    )
    return result


if __name__ == "__main__":
    import asyncio

    from link import create_bloom_filter

    from .utils import ensure_dir

    async def _test() -> None:
        test_dir = os.path.join(os.path.dirname(__file__), "_test_handler")
        html_dir = os.path.join(test_dir, "html")
        img_dir = os.path.join(test_dir, "images")
        ensure_dir(html_dir)
        ensure_dir(img_dir)

        bf = create_bloom_filter("memory")
        bf.add("https://httpbin.org/html")

        result = await process_page(
            "https://httpbin.org/html",
            0,
            {"html": html_dir, "images": img_dir},
            bf,
        )
        print("\nResult keys:", list(result.keys()))
        print("success:", result["success"])
        print("html_path:", result["html_path"])
        print("images count:", len(result["images"]))
        print("links count:", len(result["links"]))
        if result["success"]:
            assert result["html_path"] and os.path.isfile(result["html_path"])
            print("handler smoke test passed.")

    asyncio.run(_test())
