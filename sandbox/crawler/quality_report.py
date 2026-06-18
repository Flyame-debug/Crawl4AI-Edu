"""Quality report generator — aggregates crawl results into a structured JSON report.

Provides ``generate_quality_report(stats, page_results, output_dir)`` —
computes success rate, average content length, image coverage, and failed-
URL diagnostics from per-page results, then writes a timestamped JSON file.

Usage::

    from crawler.quality_report import generate_quality_report

    report_path = generate_quality_report(stats, page_results, "sandbox/data/reports")
    logger.info("Report saved to %s", report_path)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Error categorization keywords → labels
# ---------------------------------------------------------------------------

_ERROR_CATEGORIES: list[tuple[list[str], str]] = [
    # (keyword list, category label)
    (["timeout", "Timeout", "timed out"], "Timeout"),
    (["HTTP 403", "HTTP 429", "HTTP 503"], "Anti-Crawl / Rate-Limit"),
    (["HTTP 4"], "Client Error (4xx)"),
    (["HTTP 5"], "Server Error (5xx)"),
    (["DNS", "NameResolutionError", "getaddrinfo"], "DNS Resolution Failure"),
    (["ConnectionError", "Connection refused", "connect"], "Connection Error"),
    (["SSLError", "SSL", "certificate"], "SSL / Certificate Error"),
    (["Parse", "parsing", "BeautifulSoup", "lxml"], "HTML Parse Error"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_quality_report(
    task_stats: Any,
    page_results: list[dict[str, Any]],
    output_dir: str,
    *,
    task_label: str | None = None,
) -> str:
    """Build a quality report from crawl statistics and per-page results.

    Args:
        task_stats: A :class:`Statistics`-like object with attributes
            ``total``, ``success``, ``failed``, ``total_images``,
            ``start_time``, ``end_time``.
        page_results: List of per-page result dicts (the return value of
            ``process_page`` or the worker wrapper in ``_run_bfs_crawl``).
        output_dir: Directory where the report JSON will be written
            (created if missing).
        task_label: Optional human-readable label for the crawl task
            (e.g. ``"preview-20260615"``).

    Returns:
        Absolute path to the generated report file.
    """
    # 1. Ensure the output directory exists -----------------------------------
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 2. Compute aggregate metrics --------------------------------------------
    total: int = getattr(task_stats, "total", 0)
    success: int = getattr(task_stats, "success", 0)
    failed: int = getattr(task_stats, "failed", 0)
    total_images: int = getattr(task_stats, "total_images", 0)

    success_rate: float = round(success / total, 4) if total > 0 else 0.0

    # Per-page metrics.
    body_lengths: list[int] = []
    pages_with_images: int = 0
    pages_without_images: int = 0
    failed_pages: list[dict[str, Any]] = []

    for page in page_results:
        if page.get("success"):
            # Content length from HTML.
            html_content: str | None = page.get("html")
            if html_content:
                body_lengths.append(len(html_content))
            # Image presence.
            imgs: list | dict = page.get("images", [])
            img_count: int = len(imgs) if isinstance(imgs, (list, dict)) else 0
            if img_count > 0:
                pages_with_images += 1
            else:
                pages_without_images += 1
        else:
            reason: str = _categorize_error(page.get("error", "Unknown error"))
            failed_pages.append({
                "url": page.get("url", ""),
                "error": page.get("error", ""),
                "category": reason,
                "depth": page.get("depth", 0),
            })

    avg_body_length: float = (
        round(sum(body_lengths) / len(body_lengths), 1) if body_lengths else 0.0
    )
    pages_with_body: int = len(body_lengths)
    image_missing_rate: float = (
        round(pages_without_images / (pages_with_images + pages_without_images), 4)
        if (pages_with_images + pages_without_images) > 0
        else 0.0
    )

    # 3. Build failure category summary ---------------------------------------
    category_counts: dict[str, int] = {}
    for fp in failed_pages:
        cat: str = fp["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # 4. Compute elapsed time -------------------------------------------------
    elapsed: float = 0.0
    start_ts: float | None = getattr(task_stats, "start_time", None)
    end_ts: float | None = getattr(task_stats, "end_time", None)
    if start_ts is not None and end_ts is not None:
        elapsed = round(end_ts - start_ts, 2)

    # 5. Assemble report ------------------------------------------------------
    now_iso: str = datetime.now(timezone.utc).isoformat()
    date_str: str = datetime.now(timezone.utc).strftime("%Y%m%d")

    report: dict[str, Any] = {
        "report_meta": {
            "generated_at": now_iso,
            "task_label": task_label or f"crawl-{date_str}",
        },
        "summary": {
            "total_pages": total,
            "success_pages": success,
            "failed_pages": failed,
            "success_rate": success_rate,
            "total_images": total_images,
            "elapsed_seconds": elapsed,
        },
        "content_metrics": {
            "pages_with_body_measured": pages_with_body,
            "average_body_length_chars": avg_body_length,
            "pages_with_images": pages_with_images,
            "pages_without_images": pages_without_images,
            "image_missing_rate": image_missing_rate,
        },
        "failure_breakdown": {
            "by_category": category_counts,
            "failed_urls": failed_pages,
        },
    }

    # 6. Write JSON -----------------------------------------------------------
    filename: str = f"report_{date_str}.json"
    filepath: Path = out_path / filename
    filepath.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    # 7. Optional console summary ---------------------------------------------
    logger.info("质量报告已生成: %s", filepath)
    _print_console_summary(report)

    return str(filepath.resolve())


# ---------------------------------------------------------------------------
# Internal: error categorization
# ---------------------------------------------------------------------------


def _categorize_error(error_msg: str) -> str:
    """Classify *error_msg* into a high-level category label.

    Args:
        error_msg: The error string from the per-page result.

    Returns:
        One of ``"Timeout"``, ``"Anti-Crawl / Rate-Limit"``, ``"Client Error (4xx)"``,
        ``"Server Error (5xx)"``, ``"DNS Resolution Failure"``, ``"Connection Error"``,
        ``"SSL / Certificate Error"``, ``"HTML Parse Error"``, or ``"Unknown"``.
    """
    if not error_msg:
        return "Unknown"
    for keywords, label in _ERROR_CATEGORIES:
        for kw in keywords:
            if kw in error_msg:
                return label
    return "Unknown"


# ---------------------------------------------------------------------------
# Internal: console summary printer
# ---------------------------------------------------------------------------


def _print_console_summary(report: dict[str, Any]) -> None:
    """Print a compact quality summary to the console."""
    s: dict = report["summary"]
    c: dict = report["content_metrics"]
    f: dict = report["failure_breakdown"]

    lines: list[str] = [
        "",
        "=" * 50,
        "          Quality Report Summary",
        "=" * 50,
        f"  Pages         : {s['total_pages']} total / {s['success_pages']} ok / {s['failed_pages']} fail",
        f"  Success rate  : {s['success_rate']:.1%}",
        f"  Avg body len  : {c['average_body_length_chars']:.0f} chars",
        f"  Image coverage: {c['pages_with_images']} with / {c['pages_without_images']} without",
        f"  Image miss %  : {c['image_missing_rate']:.1%}",
        f"  Time elapsed  : {s['elapsed_seconds']:.1f} s",
        "",
    ]
    if f["by_category"]:
        lines.append("  Failure breakdown:")
        for cat, count in sorted(f["by_category"].items(), key=lambda x: -x[1]):
            lines.append(f"    {cat}: {count}")
    lines.append("=" * 50)
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Fake Statistics-like object.
    class _FakeStats:
        total = 5
        success = 3
        failed = 2
        total_images = 4
        start_time = 1000.0
        end_time = 1025.5

    fake_results: list[dict[str, Any]] = [
        {
            "success": True, "url": "https://example.com/page1",
            "depth": 0, "html": "<html>" + "x" * 5000 + "</html>",
            "images": ["a.png", "b.png"],
            "error": None,
        },
        {
            "success": True, "url": "https://example.com/page2",
            "depth": 0, "html": "<html>" + "y" * 3000 + "</html>",
            "images": [],
            "error": None,
        },
        {
            "success": True, "url": "https://example.com/page3",
            "depth": 1, "html": "<html>" + "z" * 8000 + "</html>",
            "images": ["c.png", "d.png"],
            "error": None,
        },
        {
            "success": False, "url": "https://example.com/blocked",
            "depth": 1, "html": None,
            "images": [],
            "error": "HTTP 403 for https://example.com/blocked",
        },
        {
            "success": False, "url": "https://example.com/slow",
            "depth": 1, "html": None,
            "images": [],
            "error": "Request failed: timeout after 30s",
        },
    ]

    test_dir: str = "data/reports"
    report_path: str = generate_quality_report(
        _FakeStats(), fake_results, test_dir, task_label="smoke-test",
    )
    print(f"\nReport written to: {report_path}")

    # Verify file exists and is valid JSON.
    with open(report_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["summary"]["total_pages"] == 5
    assert loaded["summary"]["success_rate"] == 0.6
    assert abs(loaded["content_metrics"]["image_missing_rate"] - 1 / 3) < 0.01
    assert len(loaded["failure_breakdown"]["failed_urls"]) == 2
    print("quality_report.py — smoke test passed.")
