"""Core BFS crawler — breadth-first, depth-controlled, concurrent page processing.

Orchestrates fetcher (A1), link (A2), image_downloader (A3), and optionally
dead_link_checker (A4) into a single runnable crawl.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

# Ensure sandbox/ and project root are on sys.path for all import styles.
_sandbox = str(Path(__file__).resolve().parent.parent)
_project_root = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_sandbox, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from link import create_bloom_filter

from .handlers import process_page
from .stats import Statistics
from .utils import ensure_dir, get_logger, normalize_url

logger = get_logger("standalone_crawler.crawler")

# Optional dead-link checker — imported once at module level.
try:
    from dead_link_checker import check_dead_links as _check_dead_links
except ImportError:
    _check_dead_links = None


async def crawl(
    seed_url: str,
    max_depth: int = 2,
    max_concurrent: int = 5,
    enable_dead_check: bool = False,
) -> Statistics:
    """Run a breadth-first crawl starting from *seed_url*.

    Args:
        seed_url: Starting URL (depth 0).
        max_depth: Maximum BFS depth (seed = 0).
        max_concurrent: Max pages processed simultaneously.
        enable_dead_check: If ``True``, filter new links through
            ``dead_link_checker.check_dead_links`` before enqueuing.

    Returns:
        :class:`Statistics` object whose ``.report()`` method produces a
        human-readable summary.
    """
    # Warn early if dead-link check was requested but is unavailable.
    dead_checker = _check_dead_links
    if enable_dead_check and dead_checker is None:
        logger.warning(
            "enable_dead_check=True but dead_link_checker is not available; "
            "dead-link filtering will be skipped."
        )

    stats = Statistics()
    stats.start()

    # Bloom filter for URL dedup (memory backend).
    bloom = create_bloom_filter("memory")
    seed_norm = normalize_url(seed_url)
    bloom.add(seed_norm)

    # Output directories (relative to project root).
    output_dirs = {"html": "sandbox/data/html", "images": "sandbox/data/images"}
    ensure_dir(output_dirs["html"])
    ensure_dir(output_dirs["images"])

    semaphore = asyncio.Semaphore(max_concurrent)
    current_level: list[str] = [seed_norm]

    for depth in range(max_depth + 1):
        if not current_level:
            logger.info("No more URLs at depth %d — crawl finished.", depth)
            break

        logger.info(
            "Depth %d: processing %d URL(s) (max_concurrent=%d)…",
            depth,
            len(current_level),
            max_concurrent,
        )

        # Process all URLs at this depth concurrently.
        async def _worker(url: str) -> dict[str, Any]:
            async with semaphore:
                return await process_page(url, depth, output_dirs, bloom)

        results = await asyncio.gather(
            *[_worker(u) for u in current_level], return_exceptions=True
        )

        # Collect next-level URLs.
        next_level: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Worker crashed: %s", result)
                # Synthesize a failure entry so stats stay accurate.
                stats.add_result({
                    "success": False,
                    "url": "(worker crash)",
                    "depth": depth,
                    "html_path": None,
                    "images": {},
                    "links": [],
                    "error": str(result),
                })
                continue

            stats.add_result(result)

            if not result.get("success"):
                continue

            new_links: list[str] = result.get("links", [])

            # Optional dead-link filtering --------------------------------------
            if enable_dead_check and dead_checker is not None and new_links:
                try:
                    dead_list: list[str] = await dead_checker(new_links)
                    dead_set: set[str] = set(dead_list)
                    before = len(new_links)
                    new_links = [l for l in new_links if l not in dead_set]
                    skipped = before - len(new_links)
                    if skipped:
                        logger.info("Dead-link filter: %d removed, %d kept.", skipped, len(new_links))
                except Exception as exc:
                    logger.warning("Dead-link check raised an error: %s — continuing.", exc)

            # Enqueue new, unseen URLs for the next depth level.
            for link in new_links:
                if not bloom.contains(link):
                    bloom.add(link)
                    next_level.append(link)

        current_level = next_level

    stats.stop()
    logger.info("Crawl complete.  %d pages processed.", stats.total)
    return stats


if __name__ == "__main__":
    async def _main() -> None:
        print("crawler.py — smoke test with depth=1, concurrency=2")
        st = await crawl(
            seed_url="https://httpbin.org/html",
            max_depth=1,
            max_concurrent=2,
            enable_dead_check=False,
        )
        print(st.report())
        assert st.total >= 1, "Expected at least 1 page attempted"
        assert st.success >= 1, "Expected at least 1 page succeeded"
        print("crawler.py — smoke test passed.")

    asyncio.run(_main())
