"""Generate HUST faculty seed URLs by querying the teacher search AJAX API.

Calls the advancesearch.jsp endpoint page by page, extracts teacher detail
page URLs, deduplicates, and writes them to sandbox/seeds/faculty_seeds.txt.

Usage::

    conda activate crawlai-edu
    python sandbox/seed_generators/generate_faculty_seeds.py
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

# Ensure sandbox/ is on sys.path.
_sandbox = str(Path(__file__).resolve().parent.parent)
if _sandbox not in sys.path:
    sys.path.insert(0, _sandbox)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE: str = "http://faculty.hust.edu.cn"
API_PATH: str = "/system/resource/tsites/advancesearch.jsp"
PAGE_SIZE: int = 10
REQUEST_DELAY: float = 0.6  # seconds between requests (>=0.5)
OUTPUT_FILE: str = "sandbox/seeds/faculty_seeds.txt"

HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": f"{API_BASE}/jscx_new.jsp?urltype=tree.TreeTempUrl&wbtreeid=1035",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

logger = logging.getLogger("generate_faculty_seeds")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_params(page_index: int, page_size: int = PAGE_SIZE) -> dict[str, str | int]:
    """Build query parameters for the teacher search AJAX endpoint."""
    return {
        "pageindex": page_index,
        "pagesize": page_size,
        "collegeid": 0,
        "disciplineid": 0,
        "enrollid": 0,
        "rankid": 0,
        "degreeid": 0,
        "honorid": 0,
        "pinyin": "",
        "profilelen": 100,
        "teacherName": "",
        "searchDirection": "",
        "viewmode": 8,
        "viewid": 0,
        "siteOwner": 0,
        "viewUniqueId": 0,
        "showlang": "",
        "ispreview": "false",
        "basenum": 0,
        "ellipsis": "",
        "alignright": "false",
        "productType": 99,
        "tutorType": "",
    }


def _fetch_page(session: requests.Session, page_index: int) -> dict | None:
    """Fetch a single page of teacher data from the AJAX API.

    Returns:
        Parsed JSON dict or None on failure.
    """
    params = _build_params(page_index)
    url = f"{API_BASE}{API_PATH}"
    try:
        resp = session.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data: dict = resp.json()
        return data
    except requests.RequestException as exc:
        logger.error("Page %d request failed: %s", page_index, exc)
        return None
    except json.JSONDecodeError as exc:
        logger.error("Page %d JSON parse failed: %s", page_index, exc)
        return None


def _extract_urls(data: dict) -> list[str]:
    """Extract teacher homepage URLs from API response data."""
    teachers = data.get("teacherData", [])
    urls: list[str] = []
    for t in teachers:
        url = t.get("url", "")
        if url:
            urls.append(url)
    return urls


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_seeds() -> int:
    """Run the seed generation process.

    Returns:
        Total number of unique seed URLs generated.
    """
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    all_urls: list[str] = []
    total_pages: int | None = None

    logger.info("Starting seed generation from %s%s", API_BASE, API_PATH)
    page = 1

    while True:
        logger.info("Fetching page %d...", page)
        data = _fetch_page(session, page)

        if data is None:
            logger.warning("Retrying page %d after 2s delay...", page)
            time.sleep(2.0)
            data = _fetch_page(session, page)
            if data is None:
                logger.error("Page %d failed twice — stopping.", page)
                break

        # Read pagination metadata on first successful page.
        if total_pages is None:
            total_pages = int(data.get("totalpage", 0))
            total_num = int(data.get("totalnum", 0))
            logger.info(
                "Total teachers: %d across %d pages (pageSize=%d)",
                total_num, total_pages, PAGE_SIZE,
            )

        urls = _extract_urls(data)
        if not urls:
            logger.info("No more teacher data on page %d — finished.", page)
            break

        all_urls.extend(urls)
        logger.info("Page %d: collected %d URLs (cumulative: %d)", page, len(urls), len(all_urls))

        if total_pages and page >= total_pages:
            break

        page += 1
        time.sleep(REQUEST_DELAY)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique_urls: list[str] = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    # Write to file.
    with open(output_path, "w", encoding="utf-8") as f:
        for u in unique_urls:
            f.write(u + "\n")

    logger.info(
        "Seed generation complete: %d unique URLs written to %s",
        len(unique_urls), OUTPUT_FILE,
    )
    return len(unique_urls)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    count = generate_seeds()
    print(f"Generated {count} seed URLs.")
    assert count >= 3300, f"Expected at least 3300 seeds, got {count}"
    print("generate_faculty_seeds.py — smoke test passed.")
