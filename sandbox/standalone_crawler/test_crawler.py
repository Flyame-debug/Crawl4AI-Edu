"""Integration test for the standalone crawler.

Usage:  python -m sandbox.standalone_crawler.test_crawler

Verifies:
- Import of all modules succeeds.
- Crawl with seed https://httpbin.org/html, depth=1, concurrency=2 works.
- At least one page is successfully fetched.
- sandbox/data/html/ contains at least one .html file.
- Statistics report is printed.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


def _setup_path() -> None:
    """Ensure sandbox/ and project root are on sys.path for all import styles."""
    sandbox_dir = str(Path(__file__).resolve().parents[1])
    project_root = str(Path(__file__).resolve().parents[2])
    for _p in (sandbox_dir, project_root):
        if _p not in sys.path:
            sys.path.insert(0, _p)
    os.chdir(project_root)


async def _run_test() -> int:
    """Execute all checks and return 0 on success, 1 on failure."""
    _setup_path()

    from standalone_crawler import crawl
    from standalone_crawler.utils import get_logger

    logger = get_logger("test_crawler")
    errors: list[str] = []

    # -- 1. Verify imports ----------------------------------------------------
    logger.info("Verifying module imports…")
    try:
        from standalone_crawler.utils import ensure_dir, normalize_url, url_to_filename  # noqa: F401
        from standalone_crawler.handlers import process_page  # noqa: F401
        from standalone_crawler.stats import Statistics  # noqa: F401
        from standalone_crawler.crawler import crawl  # noqa: F811
        logger.info("All module imports OK.")
    except Exception as exc:
        errors.append(f"Import failed: {exc}")
        logger.error("Import verification failed: %s", exc)
        return 1

    # -- 2. Run crawl (httpbin first, fallback to example.com) ----------------
    seeds = ["https://httpbin.org/html", "https://example.com"]
    stats = None
    for seed in seeds:
        logger.info("Starting crawl: seed=%s depth=1 concurrency=2", seed)
        try:
            stats = await crawl(
                seed_url=seed,
                max_depth=1,
                max_concurrent=2,
                enable_dead_check=False,
            )
        except Exception as exc:
            errors.append(f"Crawl raised an exception: {exc}")
            logger.exception("Crawl exception")
            return 1
        if stats.success >= 1:
            break
        logger.warning("Seed %s returned 0 successes, trying fallback…", seed)

    # -- 3. Assertions --------------------------------------------------------
    if stats is None:
        errors.append("No crawl was executed.")
        return 1
    report = stats.report()
    print("\n" + report)

    if stats.total < 1:
        errors.append(f"Expected at least 1 page attempt, got {stats.total}")
    if stats.success < 1:
        errors.append(f"Expected at least 1 successful page, got {stats.success}")

    # Check HTML output directory.
    html_dir = Path("sandbox") / "data" / "html"
    html_files = list(html_dir.glob("*.html")) if html_dir.is_dir() else []
    if not html_files:
        errors.append(f"No .html files found in {html_dir.resolve()}")

    if errors:
        print(f"\nFAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  • {e}")
        return 1

    print(f"\nFound {len(html_files)} .html file(s) in {html_dir.resolve()}")
    print("测试通过")
    return 0


def main() -> None:
    """Synchronous entry point for ``python -m``."""
    _setup_path()
    exit_code = asyncio.run(_run_test())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
