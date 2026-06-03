"""Minimal CLI entry point for the standalone crawler.

Usage::

    conda activate crawlai-edu
    python sandbox/run_crawler.py <seed_url> [max_depth]

Examples::

    python sandbox/run_crawler.py https://httpbin.org/html
    python sandbox/run_crawler.py https://httpbin.org/html 2
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


def _setup_path() -> None:
    """Add sandbox/ and project root to sys.path, and chdir to project root."""
    sandbox_dir = str(Path(__file__).resolve().parent)
    project_root = str(Path(__file__).resolve().parent.parent)
    for _p in (sandbox_dir, project_root):
        if _p not in sys.path:
            sys.path.insert(0, _p)
    os.chdir(project_root)


def _parse_args() -> tuple[str, int, str | None]:
    """Extract seed URL, max depth, and optional config path from CLI.

    Usage: python sandbox/run_crawler.py <seed_url> [max_depth] [config_path]

    Returns:
        (seed_url, max_depth, config_path) tuple.  config_path is None when
        not provided; the crawler then falls back to its built-in default.
    """
    if len(sys.argv) < 2:
        print("Usage: python sandbox/run_crawler.py <seed_url> [max_depth] [config_path]")
        print("Example: python sandbox/run_crawler.py https://example.com 2 sandbox/crawler_config.json")
        sys.exit(1)

    seed_url: str = sys.argv[1]

    max_depth: int = 2
    if len(sys.argv) >= 3:
        try:
            max_depth = int(sys.argv[2])
        except ValueError:
            print(f"Invalid max_depth '{sys.argv[2]}' — using default 2.")
        if max_depth < 1:
            print("max_depth must be ≥ 1 — using 1.")
            max_depth = 1

    config_path: str | None = None
    if len(sys.argv) >= 4:
        config_path = sys.argv[3]
    return seed_url, max_depth, config_path


async def _main() -> None:
    _setup_path()
    seed_url, max_depth, config_path = _parse_args()

    from standalone_crawler import crawl

    print(f"Starting crawl: seed={seed_url} max_depth={max_depth}")
    if config_path:
        print(f"Config: {config_path}")
    stats = await crawl(
        seed_url=seed_url,
        max_depth=max_depth,
        config_path=config_path,
    )
    print(stats.report())


if __name__ == "__main__":
    asyncio.run(_main())
