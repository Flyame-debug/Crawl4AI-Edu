"""Async fetch engine: static (aiohttp) and dynamic (playwright) fetching."""

import asyncio
import logging

# NEW_DEP: aiohttp
import aiohttp

from .exceptions import FetchError
from .ua_pool import get_random_ua

logger = logging.getLogger(__name__)


async def async_fetch(
    url: str,
    use_render: bool = False,
    delay: float = 1.0,
    domain_semaphore: asyncio.Semaphore | None = None,
    max_retries: int = 2,
) -> str:
    """Fetch a URL and return its HTML body as a string.

    Args:
        url: Target URL.
        use_render: Use Playwright for JS rendering when ``True``.
        delay: Seconds to sleep before the first request.
        domain_semaphore: Optional semaphore to limit per-domain concurrency.
        max_retries: Maximum retries (0 = single attempt, no retry).

    Returns:
        Response body text.

    Raises:
        FetchError: When all fetch attempts have been exhausted.
    """
    await asyncio.sleep(delay)
    headers = {"User-Agent": get_random_ua()}

    async def _attempt() -> str:
        if use_render:
            return await _fetch_rendered(url, headers)
        async with aiohttp.ClientSession() as session:
            return await _fetch_static(session, url, headers)

    last_error: FetchError | None = None
    total_attempts = max_retries + 1
    for attempt in range(total_attempts):
        try:
            if domain_semaphore is not None:
                async with domain_semaphore:
                    return await _attempt()
            return await _attempt()
        except FetchError as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(
                    "Attempt %d/%d failed for %s: %s — retrying in %ds",
                    attempt + 1,
                    total_attempts,
                    url,
                    e,
                    wait,
                )
                await asyncio.sleep(wait)
    raise last_error  # type: ignore[misc]


async def _fetch_static(
    session: aiohttp.ClientSession, url: str, headers: dict[str, str]
) -> str:
    """Fetch content via aiohttp — only HTTP 200 is accepted."""
    timeout = aiohttp.ClientTimeout(total=30)
    try:
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            if resp.status != 200:
                # consume body to release connection
                await resp.text()
                raise FetchError(f"HTTP {resp.status} for {url}")
            return await resp.text()
    except aiohttp.ClientError as e:
        raise FetchError(f"Request failed for {url}: {e}", original=e) from e
    except FetchError:
        raise
    except Exception as e:
        raise FetchError(f"Unexpected error fetching {url}: {e}", original=e) from e


async def _fetch_rendered(url: str, headers: dict[str, str]) -> str:
    """Fetch content via Playwright with ``networkidle`` wait strategy."""
    try:
        from playwright.async_api import async_playwright  # NEW_DEP: playwright
    except ImportError as e:
        raise FetchError(
            "playwright not installed. Run: pip install playwright && playwright install",
            original=e,
        ) from e

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            async with browser:
                user_agent = headers.get("User-Agent", "")
                context = await browser.new_context(user_agent=user_agent)
                async with context:
                    page = await context.new_page()
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    return await page.content()
    except FetchError:
        raise
    except Exception as e:
        raise FetchError(f"Render failed for {url}: {e}", original=e) from e


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    print("fetcher.core loaded — use test_fetch.py for integration tests.")
