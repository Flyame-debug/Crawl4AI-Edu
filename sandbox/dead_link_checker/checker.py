"""Dead link checker — concurrent HEAD-request based dead link detection."""

from __future__ import annotations

import asyncio
import logging
import random
import sys
from typing import Callable

import aiohttp

# ---------------------------------------------------------------------------
# User-Agent strategy
# ---------------------------------------------------------------------------

DEFAULT_UAS: list[str] = [
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
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
        "Gecko/20100101 Firefox/126.0"
    ),
]


def _build_ua_getter() -> Callable[[], str]:
    """Try to reuse the fetcher module's UA pool.

    Falls back to a local list if the import fails.
    """
    for module_path in (
        "sandbox.fetcher.utils",
        "sandbox.fetcher.ua_pool",
    ):
        try:
            mod = __import__(module_path, fromlist=["get_random_ua"])
            getter: Callable[[], str] = getattr(mod, "get_random_ua")
            logging.getLogger(__name__).info(
                "Using get_random_ua from %s", module_path
            )
            return getter
        except ImportError:
            continue

    logging.getLogger(__name__).info(
        "sandbox.fetcher not available, using built-in UA pool (%d entries)",
        len(DEFAULT_UAS),
    )

    def _fallback_ua() -> str:
        return random.choice(DEFAULT_UAS)

    return _fallback_ua


get_random_ua: Callable[[], str] = _build_ua_getter()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


async def _check_single(
    url: str,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    retries: int,
) -> bool:
    """Check a single URL with retries and exponential backoff.

    Parameters
    ----------
    url : str
        The URL to check via HEAD request.
    session : aiohttp.ClientSession
        A shared client session for connection reuse.
    semaphore : asyncio.Semaphore
        Concurrency-limiting semaphore.
    retries : int
        Number of retries after the first attempt.

    Returns
    -------
    bool
        True if the URL responded with status < 400, False otherwise.
    """
    total_attempts: int = 1 + retries
    user_agent: str = get_random_ua()
    headers: dict[str, str] = {"User-Agent": user_agent}

    for attempt in range(1, total_attempts + 1):
        async with semaphore:
            try:
                async with session.head(
                    url,
                    allow_redirects=True,
                    headers=headers,
                ) as response:
                    if response.status < 400:
                        logger.debug(
                            "URL alive: %s (status=%d, attempt=%d)",
                            url,
                            response.status,
                            attempt,
                        )
                        return True
                    logger.warning(
                        "URL returned error status: %s (status=%d, attempt=%d/%d)",
                        url,
                        response.status,
                        attempt,
                        total_attempts,
                    )
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                logger.warning(
                    "URL request failed: %s (attempt=%d/%d, error=%s)",
                    url,
                    attempt,
                    total_attempts,
                    type(exc).__name__,
                )

        if attempt < total_attempts:
            backoff: float = float(2 ** (attempt - 1))
            logger.debug("Backing off %.1fs before retrying %s", backoff, url)
            await asyncio.sleep(backoff)

    logger.info("URL marked as dead after %d attempts: %s", total_attempts, url)
    return False


async def check_dead_links(
    urls: list[str],
    max_concurrent: int = 10,
    retries: int = 3,
) -> list[str]:
    """Concurrently detect dead links from a list of URLs using HEAD requests.

    Each URL is checked with up to ``1 + retries`` attempts (exponential
    backoff).  A URL is considered dead if *every* attempt either returns
    status >= 400 or raises a network / timeout exception.

    Parameters
    ----------
    urls : list[str]
        URLs to check.  Duplicates are removed while preserving first-seen
        order.
    max_concurrent : int
        Maximum number of concurrent requests, enforced via
        :class:`asyncio.Semaphore`.  Defaults to 10.
    retries : int
        Number of retries on failure (total attempts = 1 + retries).
        Defaults to 3.

    Returns
    -------
    list[str]
        Dead-link URLs in the order they first appeared in *urls*.
    """
    unique_urls: list[str] = list(dict.fromkeys(urls))
    if not unique_urls:
        return []

    semaphore = asyncio.Semaphore(max_concurrent)
    timeout = aiohttp.ClientTimeout(total=5)
    connector = aiohttp.TCPConnector(limit=0, limit_per_host=0)

    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
    ) as session:
        tasks = [
            _check_single(url, session, semaphore, retries)
            for url in unique_urls
        ]
        results = await asyncio.gather(*tasks)

    dead_links: list[str] = [
        url for url, alive in zip(unique_urls, results) if not alive
    ]

    logger.info(
        "Dead-link check finished: %d unique, %d alive, %d dead",
        len(unique_urls),
        len(unique_urls) - len(dead_links),
        len(dead_links),
    )
    return dead_links


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    test_urls = [
        "https://httpbin.org/status/200",
        "https://httpbin.org/status/404",
        "https://httpbin.org/status/500",
        "https://httpbin.org/status/302",
        "https://httpbin.org/delay/10",
        "https://nonexistent.domain.xyz",
    ]

    dead = asyncio.run(
        check_dead_links(test_urls, max_concurrent=3, retries=2)
    )
    print("\n死链列表:")
    for url in dead:
        print(f"  {url}")
