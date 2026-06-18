"""CLI entry point for the standalone crawler — local and API modes.

Usage::

    conda activate crawlai-edu

    # Local mode (backward compatible)
    python sandbox/run_crawler.py <seed_url> [max_depth] [config_path]

    # API worker mode (poll backend for pending seeds)
    python sandbox/run_crawler.py --worker

    # API one-shot mode (crawl a single seed via API)
    python sandbox/run_crawler.py --use-api <seed_url>
    python sandbox/run_crawler.py --use-api --seed <seed_url> [max_depth]

    # Custom backend URL
    python sandbox/run_crawler.py --worker --backend-url http://192.168.1.1:8000

    # Preview mode (limited pages, local-only, no API ingestion)
    python sandbox/run_crawler.py <seed_url> --task-type preview --preview-limit 3

    # Full mode (default — normal API or local persistence)
    python sandbox/run_crawler.py <seed_url> --task-type full

Examples::

    python sandbox/run_crawler.py https://httpbin.org/html
    python sandbox/run_crawler.py https://httpbin.org/html 2
    python sandbox/run_crawler.py --worker --poll-interval 5
    python sandbox/run_crawler.py --use-api --seed https://httpbin.org/html 1
    python sandbox/run_crawler.py https://httpbin.org/html --task-type preview --preview-limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path


def _setup_path() -> None:
    """Add sandbox/ and project root to sys.path, and chdir to project root."""
    sandbox_dir = str(Path(__file__).resolve().parent)
    project_root = str(Path(__file__).resolve().parent.parent)
    for p in (sandbox_dir, project_root):
        if p not in sys.path:
            sys.path.insert(0, p)
    os.chdir(project_root)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser supporting both legacy and new CLI styles."""
    parser = argparse.ArgumentParser(
        description="Crawl4AI standalone crawler — local and API modes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sandbox/run_crawler.py https://example.com           # local mode
  python sandbox/run_crawler.py https://example.com 2         # local, depth 2
  python sandbox/run_crawler.py --worker                      # API worker mode
  python sandbox/run_crawler.py --use-api --seed URL          # API one-shot
  python sandbox/run_crawler.py --worker --backend-url URL    # custom backend
        """.strip(),
    )

    # Positional: seed_url, max_depth, config_path (for backward compat).
    parser.add_argument(
        "seed_url", nargs="?", default=None,
        help="Seed URL (starting page for local or API one-shot mode).",
    )
    parser.add_argument(
        "max_depth", nargs="?", type=int, default=None,
        help="Maximum BFS depth (default: from config or 2).",
    )
    parser.add_argument(
        "config_path", nargs="?", default=None,
        help="Path to JSON config file (local mode only).",
    )

    # New optional flags.
    parser.add_argument(
        "--worker", action="store_true", default=False,
        help="Start in API worker mode (poll backend for pending seeds).",
    )
    parser.add_argument(
        "--use-api", action="store_true", default=False,
        help="Enable API integration (use with --seed or positional seed_url).",
    )
    parser.add_argument(
        "--seed", dest="api_seed", default=None,
        help="Seed URL for API one-shot mode (alternative to positional).",
    )
    parser.add_argument(
        "--backend-url", default=None,
        help="Backend API base URL (overrides CRAWLER_BACKEND_URL env var).",
    )
    parser.add_argument(
        "--poll-interval", type=int, default=10,
        help="Seconds between seed-poll cycles in worker mode (default: 10).",
    )
    parser.add_argument(
        "--no-graceful", action="store_true", default=False,
        help="Disable graceful shutdown on SIGINT/SIGTERM (default: enabled).",
    )
    parser.add_argument(
        "--seed-list", default=None,
        help="Path to a text file with one seed URL per line (local mode).",
    )
    parser.add_argument(
        "--output-dir", default="sandbox/data",
        help="Directory for HTML and image output (default: sandbox/data).",
    )
    parser.add_argument(
        "--depth", dest="depth_override", type=int, default=None,
        help="Maximum BFS depth (overrides positional max_depth).",
    )
    parser.add_argument(
        "--resume", default=None,
        help="Path to crawled-urls tracking file for checkpoint/resume (local mode).",
    )
    parser.add_argument(
        "--task-type", dest="task_type", default="full",
        choices=["preview", "full"],
        help="Task mode: 'preview' (limited pages, local-only, no API) or "
             "'full' (normal crawling with API/local persistence). Default: full.",
    )
    parser.add_argument(
        "--preview-limit", dest="preview_limit", type=int, default=10,
        help="Maximum pages to crawl in preview mode (default: 10).",
    )
    return parser


async def _main() -> None:
    _setup_path()

    parser = _build_parser()
    args = parser.parse_args()

    # Determine effective seed URL.
    effective_seed: str | None = args.api_seed or args.seed_url

    # Resolve API client when needed.
    api_client = None
    use_api: bool = args.worker or args.use_api or os.getenv("USE_API", "").lower() == "true"

    if use_api:
        from standalone_crawler import APIClient

        backend_url: str | None = args.backend_url or os.getenv("CRAWLER_BACKEND_URL")
        api_client = APIClient(base_url=backend_url)

    from standalone_crawler import crawl

    if args.worker:
        # API worker mode — continuous polling.
        print(f"Starting API worker mode (backend={api_client._base_url}, poll={args.poll_interval}s)")
        await crawl(
            api_client=api_client,
            poll_interval=args.poll_interval,
            max_depth=args.max_depth,
            no_graceful=args.no_graceful,
        )
        return

    if use_api and effective_seed:
        # API one-shot mode.
        print(f"Starting API one-shot crawl: seed={effective_seed} max_depth={args.max_depth or 'auto'}")
        seed_list = [{"url": effective_seed}]
        stats = await crawl(
            seed_url=effective_seed,
            max_depth=args.max_depth,
            config_path=args.config_path,
            api_client=api_client,
            seed_list=seed_list,
        )
        if stats:
            print(stats.report())
        return

    # Local mode (backward compatible).
    # Read seed list file if provided.
    seed_urls: list[str] | None = None
    if args.seed_list:
        seed_path = Path(args.seed_list)
        if not seed_path.is_file():
            print(f"Error: seed-list file not found: {args.seed_list}")
            sys.exit(1)
        seed_urls = [line.strip() for line in seed_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        print(f"Loaded {len(seed_urls)} seed URLs from {args.seed_list}")
        effective_seed = seed_urls[0] if seed_urls else None

    if not effective_seed:
        if use_api:
            print("Error: --use-api requires a seed URL (via --seed or positional argument).")
        else:
            print("Usage: python sandbox/run_crawler.py <seed_url> [max_depth] [config_path]")
            print("       python sandbox/run_crawler.py --seed-list <file> [--output-dir <dir>]")
            print("       python sandbox/run_crawler.py --worker")
            print("       python sandbox/run_crawler.py --use-api --seed <url>")
        sys.exit(1)

    depth = args.depth_override if args.depth_override is not None else args.max_depth
    resume_path: str | None = args.resume

    # Preview mode: force local output and show banner.
    task_type: str = args.task_type
    preview_limit: int = args.preview_limit
    if task_type == "preview":
        output_dir = args.output_dir if args.output_dir != "sandbox/data" else "sandbox/preview_data"
        print("=" * 60)
        print("  预览模式 (Preview Mode)")
        print(f"  最多抓取: {preview_limit} 个页面")
        print(f"  输出目录: {output_dir}")
        print(f"  数据不会写入后端数据库")
        print("=" * 60)
    else:
        output_dir = args.output_dir

    print(f"Starting local crawl: seed={effective_seed} max_depth={depth or 'auto'}" + (f" resume={resume_path}" if resume_path else ""))
    stats = await crawl(
        seed_url=effective_seed,
        max_depth=depth,
        config_path=args.config_path,
        seed_urls=seed_urls,
        output_dir=output_dir,
        resume_path=resume_path,
        task_type=task_type,
        preview_limit=preview_limit,
    )
    print(stats.report())


if __name__ == "__main__":
    asyncio.run(_main())
