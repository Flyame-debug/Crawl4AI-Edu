"""Crawl4AI integration client for HTML-to-Markdown conversion.

Provides :func:`convert_with_crawl4ai` which attempts Crawl4AI conversion first,
then gracefully falls back to :func:`~.markdown_converter.html_to_markdown_simple`
when Crawl4AI is unavailable, errors, or times out (30 s default).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_sandbox = str(Path(__file__).resolve().parent.parent)
_project_root = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_sandbox, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from standalone_crawler.utils import get_logger

logger = get_logger("standalone_crawler.crawl4ai_client")

_DEFAULT_TIMEOUT: float = 30.0


async def convert_with_crawl4ai(html: str, timeout: float = _DEFAULT_TIMEOUT) -> str:
    """Convert an HTML string to Markdown using Crawl4AI.

    The function passes HTML via the ``raw:`` URL scheme supported by
    Crawl4AI's :class:`~crawl4ai.AsyncWebCrawler`.  When Crawl4AI fails
    (import error, timeout, or runtime exception) the call gracefully
    degrades to :func:`~.markdown_converter.html_to_markdown_simple`.

    Args:
        html: The raw HTML content to convert.
        timeout: Maximum wait time in seconds for the Crawl4AI call.

    Returns:
        Markdown text.  Never raises — failures result in fallback output.
    """
    if not html or not html.strip():
        logger.warning("convert_with_crawl4ai: empty input, returning ''")
        return ""

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
    except ImportError:
        logger.warning("crawl4ai not installed — falling back to readability+markdownify")
        from standalone_crawler.markdown_converter import html_to_markdown_simple
        return html_to_markdown_simple(html)

    try:
        markdown: str = await asyncio.wait_for(
            _convert_via_crawl4ai(html),
            timeout=timeout,
        )
        if markdown and markdown.strip():
            logger.debug("Crawl4AI conversion succeeded — %d chars", len(markdown))
            return markdown
        else:
            logger.warning("Crawl4AI returned empty markdown — falling back.")
            from standalone_crawler.markdown_converter import html_to_markdown_simple
            return html_to_markdown_simple(html)
    except asyncio.TimeoutError:
        logger.warning(
            "Crawl4AI timed out after %.1fs — falling back to readability+markdownify",
            timeout,
        )
        from standalone_crawler.markdown_converter import html_to_markdown_simple
        return html_to_markdown_simple(html)
    except Exception as exc:
        logger.warning(
            "Crawl4AI conversion failed (%s) — falling back to readability+markdownify",
            exc,
        )
        from standalone_crawler.markdown_converter import html_to_markdown_simple
        return html_to_markdown_simple(html)


async def _convert_via_crawl4ai(html: str) -> str:
    """Internal helper: invoke Crawl4AI with the ``raw:`` URL scheme."""
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=f"raw:{html}")
        return result.markdown or ""


if __name__ == "__main__":
    async def _test() -> None:
        sample = """<!DOCTYPE html>
<html><head><title>Crawl4AI Test</title></head>
<body>
    <h1>Integration Test</h1>
    <p>This is a <em>crawl4ai</em> client wrapper test.</p>
    <pre><code>print("hello")</code></pre>
</body>
</html>"""

        print("=== crawl4ai_client.py smoke test ===")
        md = await convert_with_crawl4ai(sample)
        print(f"Markdown output ({len(md)} chars):")
        print(md[:300])
        assert len(md) > 0, "Expected non-empty output"
        assert "Integration Test" in md, "Expected heading preserved"
        print("\ncrawl4ai_client.py — smoke test passed.")

    asyncio.run(_test())
