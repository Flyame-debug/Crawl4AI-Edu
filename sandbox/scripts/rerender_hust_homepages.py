"""Re-render HUST teacher homepages using Playwright to decrypt contact fields.

Several fields on HUST teacher pages (e.g. "其他联系方式") are encrypted
by client-side JavaScript and only rendered as plaintext after JS execution.
This script uses Playwright Chromium to fetch each depth-0 teacher homepage,
producing a fully-rendered HTML file that contains the decrypted content.

Usage::

    conda activate crawlai-edu
    python sandbox/scripts/rerender_hust_homepages.py

Features:
    - Reads depth==0 URLs from sandbox/data/metadata.json
    - Renders each page with Playwright (headless Chromium)
    - Saves rendered HTML to sandbox/data/html/ (overwrites old file)
    - Supports resume: tracks completed URLs in a progress file
    - Logs to sandbox/logs/rerender.log
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Ensure sandbox/ and project root are on sys.path.
_sandbox = str(Path(__file__).resolve().parent.parent)
_project_root = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_sandbox, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

logger = logging.getLogger("rerender_hust")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

METADATA_PATH: str = "sandbox/data/metadata.json"
HTML_DIR: str = "sandbox/data/html"
PROGRESS_FILE: str = "sandbox/data/rerender_progress.txt"
LOG_FILE: str = "sandbox/logs/rerender.log"

# Render settings — pulled from config when available, otherwise defaults.
RENDER_WAIT_TIME: float = 2.0
REQUEST_DELAY: float = 2.0
CONCURRENCY: int = 2  # Playwright is heavy; keep low


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_config() -> dict[str, Any]:
    """Load HUST school config to read render settings."""
    config_path = Path("sandbox/config/schools/hust_faculty.json")
    if config_path.is_file():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_depth0_urls() -> list[str]:
    """Load all depth==0 URLs from metadata.json."""
    mp = Path(METADATA_PATH)
    if not mp.is_file():
        logger.error("Metadata file not found: %s", METADATA_PATH)
        return []
    with open(mp, "r", encoding="utf-8") as f:
        meta: dict[str, dict] = json.load(f)
    urls = [url for url, entry in meta.items() if entry.get("depth") == 0]
    logger.info("Loaded %d depth-0 URLs from metadata.json", len(urls))
    return urls


def _load_progress() -> set[str]:
    """Load the set of already-completed URLs from the progress file."""
    pp = Path(PROGRESS_FILE)
    if not pp.is_file():
        return set()
    done = set(line.strip() for line in pp.read_text(encoding="utf-8").splitlines() if line.strip())
    logger.info("Resume: %d URL(s) already rendered", len(done))
    return done


def _save_progress(url: str) -> None:
    """Append a completed URL to the progress file."""
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def rerender_homepages() -> dict[str, int]:
    """Run the Playwright re-render loop over all depth-0 teacher pages.

    Returns:
        A dict with keys ``total``, ``success``, ``failed``, ``skipped``.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("playwright not installed. Run: pip install playwright && playwright install chromium")
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    cfg = _load_config()
    wait_time: float = float(cfg.get("render_wait_time", RENDER_WAIT_TIME))
    delay: float = float(cfg.get("request_delay", REQUEST_DELAY))

    urls = _load_depth0_urls()
    if not urls:
        logger.warning("No depth-0 URLs found — nothing to render.")
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    done = _load_progress()
    todo = [u for u in urls if u not in done]

    stats = {"total": len(todo), "success": 0, "failed": 0, "skipped": len(done)}

    if not todo:
        logger.info("All %d depth-0 URLs already rendered — nothing to do.", len(urls))
        return stats

    logger.info("Starting re-render: %d URL(s) to process (wait=%.1fs, delay=%.1fs)",
                 len(todo), wait_time, delay)

    html_dir = Path(HTML_DIR)
    html_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for idx, url in enumerate(todo, 1):
                try:
                    await _render_one(browser, url, html_dir, wait_time)
                    _save_progress(url)
                    stats["success"] += 1
                    logger.info("[%d/%d] OK: %s", idx, len(todo), url)
                except Exception as exc:
                    stats["failed"] += 1
                    logger.error("[%d/%d] FAIL: %s — %s", idx, len(todo), url, exc)
                # Respect request delay between pages.
                if idx < len(todo):
                    await _sleep_async(delay)
        finally:
            await browser.close()

    logger.info(
        "Re-render complete: %d total, %d success, %d failed, %d skipped (already done)",
        stats["total"] + stats["skipped"], stats["success"], stats["failed"], stats["skipped"],
    )
    return stats


async def _render_one(
    browser, url: str, html_dir: Path, wait_time: float,
) -> None:
    """Render a single URL with Playwright and save the HTML."""
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    )
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        # Extra wait for any deferred JS decryption.
        await page.wait_for_timeout(int(wait_time * 1000))
        html = await page.content()

        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        html_file = html_dir / f"{url_hash}.html"
        html_file.write_text(html, encoding="utf-8")
    finally:
        await context.close()


async def _sleep_async(seconds: float) -> None:
    """Async sleep helper."""
    import asyncio
    await asyncio.sleep(seconds)


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    # Set up dual logging: console + file.
    log_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_datefmt = "%H:%M:%S"

    # File handler.
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter(log_fmt, datefmt=log_datefmt))

    # Console handler.
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(log_fmt, datefmt=log_datefmt))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(fh)
    root.addHandler(ch)

    result = asyncio.run(rerender_homepages())
    print(f"\nDone. success={result['success']} failed={result['failed']} skipped={result['skipped']}")
