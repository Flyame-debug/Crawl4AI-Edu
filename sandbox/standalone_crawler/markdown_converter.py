"""Fallback HTML-to-Markdown converter using readability-lxml + markdownify.

Used as a graceful degradation path when Crawl4AI is unavailable or errors out.
"""

from __future__ import annotations

import sys
from pathlib import Path

_sandbox = str(Path(__file__).resolve().parent.parent)
_project_root = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_sandbox, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from standalone_crawler.utils import get_logger

logger = get_logger("standalone_crawler.markdown_converter")


def html_to_markdown_simple(html: str) -> str:
    """Convert an HTML string to Markdown using readability-lxml + markdownify.

    This function:
    1. Extracts the main content area using ``readability-lxml``.
    2. Converts the extracted (or original) HTML to Markdown via ``markdownify``.

    Args:
        html: Raw HTML string.

    Returns:
        Markdown text.  Returns an empty string when the input is empty or
        both extraction steps fail.
    """
    if not html or not html.strip():
        logger.warning("html_to_markdown_simple: empty input, returning ''")
        return ""

    # Step 1: Extract readable content with readability-lxml.
    cleaned_html: str = ""
    try:
        from readability import Document

        doc = Document(html)
        cleaned_html = doc.summary(html_partial=True)
        logger.debug("readability extraction succeeded — %d → %d chars",
                     len(html), len(cleaned_html))
    except ImportError:
        logger.warning(
            "readability-lxml is not installed; converting full HTML directly. "
            "Install with: pip install readability-lxml"
        )
        cleaned_html = html
    except Exception as exc:
        logger.warning("readability extraction failed: %s — falling back to raw HTML", exc)
        cleaned_html = html

    if not cleaned_html or not cleaned_html.strip():
        logger.warning("Cleaned HTML is empty after readability; using raw HTML.")
        cleaned_html = html

    # Step 2: Convert to Markdown.
    try:
        from markdownify import markdownify as md

        markdown: str = md(cleaned_html, heading_style="ATX", strip=["script", "style"])
        logger.debug("markdownify conversion succeeded — %d chars", len(markdown))
        return markdown.strip()
    except ImportError:
        logger.warning(
            "markdownify is not installed; returning cleaned HTML. "
            "Install with: pip install markdownify"
        )
        return cleaned_html.strip()
    except Exception as exc:
        logger.error("markdownify conversion failed: %s — returning raw HTML", exc)
        return html.strip()


if __name__ == "__main__":
    sample = """<!DOCTYPE html>
<html><head><title>Test</title></head>
<body>
    <article>
        <h1>Hello World</h1>
        <p>This is a <strong>bold</strong> statement and a <a href="https://example.com">link</a>.</p>
        <ul><li>one</li><li>two</li></ul>
    </article>
</body>
</html>"""

    md = html_to_markdown_simple(sample)
    print("=== markdown_converter.py smoke test ===")
    print(f"Markdown output ({len(md)} chars):")
    print(md[:300])
    assert len(md) > 0, "Expected non-empty output"
    print("\nmarkdown_converter.py — smoke test passed.")
