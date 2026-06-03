"""Integration tests for the async fetch engine.

Usage::

    python -m fetcher.test_fetch
"""

import asyncio
import logging
import time

from fetcher.core import async_fetch
from fetcher.exceptions import FetchError

logger = logging.getLogger(__name__)


async def _test_static() -> None:
    """Test static fetch via aiohttp using httpbin."""
    url = "https://httpbin.org/html"
    logger.info("=== Test 1: Static fetch (aiohttp) ===")
    try:
        html = await async_fetch(url, delay=0.3)
        logger.info("OK — received %d chars", len(html))
        preview = html[:200].replace("\n", "\\n")
        logger.info("Preview: %s...", preview)
    except FetchError as e:
        logger.error("FAILED: %s", e)


async def _test_rendered() -> None:
    """Test dynamic-render fetch via Playwright."""
    url = "https://www.baidu.com"
    logger.info("=== Test 2: Rendered fetch (Playwright) ===")
    try:
        html = await async_fetch(url, use_render=True, delay=0.5)
        logger.info("OK — received %d chars", len(html))
    except FetchError as e:
        logger.error("FAILED (is playwright installed?): %s", e)


async def _test_semaphore() -> None:
    """Verify semaphore throttles concurrent requests to the same domain."""
    url = "https://httpbin.org/delay/1"
    sem = asyncio.Semaphore(2)
    logger.info("=== Test 3: Semaphore limit=2, 4 concurrent requests ===")

    async def _fetch_one(idx: int) -> float:
        t0 = time.monotonic()
        try:
            html = await async_fetch(url, delay=0.1, domain_semaphore=sem, max_retries=0)
            elapsed = time.monotonic() - t0
            logger.info("  [%d] done in %.1fs, length=%d", idx, elapsed, len(html))
            return elapsed
        except FetchError as e:
            elapsed = time.monotonic() - t0
            logger.error("  [%d] failed in %.1fs: %s", idx, elapsed, e)
            return elapsed

    t_start = time.monotonic()
    results = await asyncio.gather(*[_fetch_one(i) for i in range(4)])
    total = time.monotonic() - t_start
    logger.info(
        "Semaphore test finished in %.1fs (individual: %s). "
        "With limit=2 the 4 requests should batch into ~2 waves.",
        total,
        ", ".join(f"{r:.1f}s" for r in results),
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    for _name, _coro in [
        ("static", _test_static()),
        ("rendered", _test_rendered()),
        ("semaphore", _test_semaphore()),
    ]:
        print(f"\n{'='*60}")
        asyncio.run(_coro)

    print(f"\n{'='*60}")
    logger.info("All fetch engine tests completed.")
