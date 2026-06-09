"""Core BFS crawler — breadth-first, depth-controlled, concurrent page processing.

Orchestrates fetcher (A1), link (A2), image_downloader (A3), and optionally
dead_link_checker (A4) into a single runnable crawl.

Two operating modes
--------------------
- **Local mode** (default, ``USE_API`` unset or ``false``): reads config from
  a local JSON file and runs a one-shot BFS crawl for a given seed URL.  No
  backend API is called.
- **API worker mode** (``USE_API=true``, ``--worker``): polls the backend for
  pending seeds, fetches config from ``/api/crawler/config/db/``, and reports
  results through the API.  The BFS crawl logic is shared between both modes.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from typing import Any, TYPE_CHECKING

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

if TYPE_CHECKING:
    from .api_client import APIClient

logger = get_logger("standalone_crawler.crawler")

# Optional dead-link checker — imported once at module level.
try:
    from dead_link_checker import check_dead_links as _check_dead_links
except ImportError:
    _check_dead_links = None

# Default config path (relative to project root).
_DEFAULT_CONFIG_PATH: str = "sandbox/crawler_config.json"
_DEFAULT_POLL_INTERVAL: int = 10


# ===================================================================
# Config loading (local mode)
# ===================================================================


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load crawler configuration from a JSON file.

    Args:
        config_path: Path to a JSON config file.  If ``None``, the default
            ``sandbox/crawler_config.json`` is used.

    Returns:
        A dict with keys matching the config schema.  Returns an empty dict
        if the file does not exist or cannot be parsed.
    """
    path = Path(config_path or _DEFAULT_CONFIG_PATH)
    if not path.is_file():
        logger.info("Config file not found at %s — using built-in defaults.", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg: dict[str, Any] = json.load(fh)
        logger.info("Loaded config from %s", path)
        return cfg
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to parse config %s: %s — using built-in defaults.", path, exc)
        return {}


def _setup_signal_handlers(shutdown_event: asyncio.Event) -> None:
    """Register OS signal handlers that set *shutdown_event* on SIGINT/SIGTERM.

    Uses :func:`signal.signal` (thread-safe, compatible with Windows where
    ``loop.add_signal_handler`` is unavailable).
    """

    def _handler(signum: int, frame: Any) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s — initiating graceful shutdown.", sig_name)
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError) as exc:
            logger.warning("Cannot register handler for %s: %s", sig, exc)


# ===================================================================
# Main entry point
# ===================================================================


async def crawl(
    seed_url: str | None = None,
    max_depth: int | None = None,
    max_concurrent: int | None = None,
    enable_dead_check: bool = False,
    allowed_domains: list[str] | None = None,
    white_list_patterns: list[str] | None = None,
    request_delay: float | None = None,
    config_path: str | None = _DEFAULT_CONFIG_PATH,
    api_client: APIClient | None = None,
    poll_interval: int = _DEFAULT_POLL_INTERVAL,
    seed_list: list[dict[str, Any]] | None = None,
    no_graceful: bool = False,
) -> Statistics | None:
    """Run a breadth-first crawl.

    **Local mode** (``api_client`` is ``None``):
        ``seed_url`` is required.  Config is read from *config_path* (JSON).
        Returns a :class:`Statistics` object.

    **API worker mode** (``api_client`` is provided and ``seed_url`` is
    ``None``):
        Enters an infinite polling loop: fetch config from API → poll pending
        seeds → crawl each seed → report results.  This function never returns
        under normal operation.  Set *seed_list* to crawl specific seeds via
        API without polling (used by ``--use-api --seed …``).

    Args:
        seed_url: Starting URL (required in local mode).
        max_depth: Maximum BFS depth (seed = 0).
        max_concurrent: Max pages processed simultaneously.
        enable_dead_check: Filter new links through dead_link_checker.
        allowed_domains: Domain whitelist for link extraction.
        white_list_patterns: URL-path regex whitelist.
        request_delay: Seconds to wait before each HTTP request.
        config_path: Path to JSON config file (local mode only).
        api_client: :class:`APIClient` instance for backend integration.
        poll_interval: Seconds between seed-poll cycles (API worker mode).
        seed_list: Explicit seed dicts for one-shot API crawl (optional).

    Returns:
        :class:`Statistics` in local mode; ``None`` in continuous API worker
        mode (function loops indefinitely).
    """
    use_api: bool = api_client is not None

    # --- API worker & one-shot helper (nested to keep top-level fn count ≤3) ---
    async def _run_api_worker(
        client: APIClient,
        poll_sec: int,
        seeds: list[dict[str, Any]] | None,
        md: int | None,
        mc: int | None,
        edc: bool,
        ad: list[str] | None,
        wp: list[str] | None,
        rd: float | None,
        sd_event: asyncio.Event,
        sd_enabled: bool,
    ) -> None:
        """API worker loop — continuous polling or one-shot seed list.

        When *sd_enabled* is True, the loop checks *sd_event* before each
        poll cycle and stops pulling new seeds once the event is set.
        In-progress seeds are allowed to finish before returning.
        """

        # Track aggregate statistics across the worker session.
        worker_total_pages: int = 0
        worker_success_pages: int = 0
        worker_failed_pages: int = 0
        worker_total_images: int = 0
        worker_seeds_done: int = 0
        worker_seeds_failed: int = 0

        async def _process_single_seed(seed: dict[str, Any]) -> None:
            """Full lifecycle for one seed: mark crawling → BFS → report."""
            nonlocal worker_total_pages, worker_success_pages
            nonlocal worker_failed_pages, worker_total_images
            nonlocal worker_seeds_done, worker_seeds_failed

            s_url: str = seed.get("url", "")
            if not s_url:
                logger.error("Seed missing 'url' field — skipping: %s", seed)
                return

            tid: str = ""
            try:
                await client.update_seed_status(s_url, "crawling")
                start_resp: dict = await client.start_crawl_task(
                    seed_url=s_url, max_depth=md,
                    config={"max_concurrent": mc, "request_delay": rd} if mc or rd else None,
                )
                tid = start_resp.get("task_id", "")
                if not tid:
                    logger.error("start_crawl_task returned no task_id for %s", s_url)
                    await client.update_seed_status(s_url, "failed")
                    worker_seeds_failed += 1
                    return

                logger.info("Task started: %s for seed %s", tid, s_url)
                st: Statistics = await _run_bfs_crawl(
                    seed_url=s_url, max_depth=md, max_concurrent=mc,
                    enable_dead_check=edc, allowed_domains=ad,
                    white_list_patterns=wp, request_delay=rd,
                    config_path=None, api_client=client,
                    task_id=tid, seed_meta=seed,
                )
                await client.report_task_result(
                    task_id=tid, status="completed",
                    total_pages=st.total, success_pages=st.success,
                    failed_pages=st.failed, report=st.report(),
                )
                final: str = "success" if st.success > 0 else "failed"
                await client.update_seed_status(s_url, final)
                worker_total_pages += st.total
                worker_success_pages += st.success
                worker_failed_pages += st.failed
                worker_total_images += st.total_images
                if final == "success":
                    worker_seeds_done += 1
                else:
                    worker_seeds_failed += 1
                logger.info("Seed complete: %s → %s (pages=%d ok=%d fail=%d)",
                             s_url, final, st.total, st.success, st.failed)
            except Exception as exc:
                logger.error("Seed %s failed: %s", s_url, exc)
                worker_seeds_failed += 1
                try:
                    await client.update_seed_status(s_url, "failed")
                    if tid:
                        await client.report_task_result(task_id=tid, status="failed", error_message=str(exc))
                except Exception as ex2:
                    logger.error("Failed to report error for seed %s: %s", s_url, ex2)

        # --- Worker body ---
        if seeds:
            for s in seeds:
                await _process_single_seed(s)
            return

        config_refresh: int = 10
        cycle_n: int = 0
        api_cfg: dict[str, Any] = {}

        while not (sd_enabled and sd_event.is_set()):
            cycle_n += 1
            if cycle_n == 1 or cycle_n % config_refresh == 0:
                try:
                    api_cfg = await client.get_config()
                    logger.info("Refreshed config from API: %s", api_cfg)
                except Exception as exc:
                    logger.warning("Failed to fetch config from API: %s — using previous.", exc)

            _md = md if md is not None else api_cfg.get("max_depth", 2)
            _mc = mc if mc is not None else api_cfg.get("concurrency", 5)
            _rd = rd if rd is not None else api_cfg.get("request_delay", 1.0)
            _ad = ad if ad is not None else api_cfg.get("default_allowed_domains", [])
            _wp = wp if wp is not None else api_cfg.get("white_list_patterns", [])
            _edc = edc or api_cfg.get("enable_dead_check", False)

            try:
                seeds_data = await client.get_pending_seeds(limit=5)
            except Exception as exc:
                logger.error("Failed to fetch pending seeds: %s — retrying in %ds.", exc, poll_sec)
                await asyncio.sleep(poll_sec)
                continue

            pending = seeds_data.get("seeds", [])
            if not pending:
                logger.info("No pending seeds — sleeping %ds.", poll_sec)
                await asyncio.sleep(poll_sec)
                continue

            logger.info("Fetched %d pending seed(s).", len(pending))
            for seed in pending:
                if sd_enabled and sd_event.is_set():
                    logger.info("Shutdown requested — skipping remaining seeds in batch.")
                    break
                await _process_single_seed(seed)

        # --- Graceful shutdown summary ---
        if sd_enabled and sd_event.is_set():
            logger.info(
                "Graceful shutdown complete. "
                "Seeds: %d done / %d failed | "
                "Pages: %d total / %d ok / %d fail | "
                "Images: %d",
                worker_seeds_done, worker_seeds_failed,
                worker_total_pages, worker_success_pages,
                worker_failed_pages, worker_total_images,
            )
    # --- end _run_api_worker --------------------------------------------------

    if use_api and seed_url is None:
        logger.info("Starting API worker mode (poll_interval=%ds)", poll_interval)
        graceful_enabled = not no_graceful and os.getenv("ENABLE_GRACEFUL_EXIT", "1") != "0"
        shutdown_event = asyncio.Event()
        if graceful_enabled:
            _setup_signal_handlers(shutdown_event)
            logger.info("Graceful exit enabled — send SIGINT/SIGTERM to stop.")
        await _run_api_worker(
            api_client, poll_interval, seed_list,
            max_depth, max_concurrent, enable_dead_check,
            allowed_domains, white_list_patterns, request_delay,
            shutdown_event, graceful_enabled,
        )
        return None

    if use_api and seed_url is not None:
        logger.info("Starting API one-shot crawl for seed: %s", seed_url)
        seed_meta: dict[str, Any] = seed_list[0] if seed_list else {}
        task_resp: dict = await api_client.start_crawl_task(
            seed_url=seed_url, max_depth=max_depth,
            config={"max_concurrent": max_concurrent, "request_delay": request_delay} if max_concurrent or request_delay else None,
        )
        task_id: str = task_resp.get("task_id", "")
        await api_client.update_seed_status(seed_url, "crawling")
        stats: Statistics = await _run_bfs_crawl(
            seed_url=seed_url, max_depth=max_depth, max_concurrent=max_concurrent,
            enable_dead_check=enable_dead_check, allowed_domains=allowed_domains,
            white_list_patterns=white_list_patterns, request_delay=request_delay,
            config_path=config_path, api_client=api_client,
            task_id=task_id, seed_meta=seed_meta,
        )
        await api_client.report_task_result(
            task_id=task_id, status="completed",
            total_pages=stats.total, success_pages=stats.success,
            failed_pages=stats.failed, report=stats.report(),
        )
        await api_client.update_seed_status(seed_url, "success" if stats.failed == 0 else "failed")
        return stats

    if seed_url is None:
        raise ValueError("seed_url is required in local mode (or pass api_client for API mode)")

    return await _run_bfs_crawl(
        seed_url=seed_url, max_depth=max_depth, max_concurrent=max_concurrent,
        enable_dead_check=enable_dead_check, allowed_domains=allowed_domains,
        white_list_patterns=white_list_patterns, request_delay=request_delay,
        config_path=config_path,
    )


# ===================================================================
# BFS crawl engine (shared by local and API modes)
# ===================================================================


async def _run_bfs_crawl(
    seed_url: str,
    max_depth: int | None = None,
    max_concurrent: int | None = None,
    enable_dead_check: bool = False,
    allowed_domains: list[str] | None = None,
    white_list_patterns: list[str] | None = None,
    request_delay: float | None = None,
    config_path: str | None = _DEFAULT_CONFIG_PATH,
    api_client: APIClient | None = None,
    task_id: str | None = None,
    seed_meta: dict[str, Any] | None = None,
) -> Statistics:
    """Core BFS crawl engine — processes one seed URL breadth-first.

    All parameters mirror those of :func:`crawl`.
    """
    # --- Resolve config -------------------------------------------------------
    cfg: dict[str, Any] = {}
    if config_path is not None:
        cfg = load_config(config_path)

    _max_depth = max_depth if max_depth is not None else cfg.get("max_depth", 2)
    _max_concurrent = max_concurrent if max_concurrent is not None else cfg.get("concurrency", 5)
    _req_delay = request_delay if request_delay is not None else cfg.get("request_delay", 1.0)
    _allowed_domains = allowed_domains if allowed_domains is not None else cfg.get("default_allowed_domains", [])
    _white_patterns = white_list_patterns if white_list_patterns is not None else cfg.get("white_list_patterns", [])

    dead_checker = _check_dead_links
    if enable_dead_check and dead_checker is None:
        logger.warning("enable_dead_check=True but dead_link_checker is not available; skipped.")

    stats = Statistics()
    stats.start()

    bloom = create_bloom_filter("memory")
    seed_norm = normalize_url(seed_url)
    bloom.add(seed_norm)

    output_dirs = {"html": "sandbox/data/html", "images": "sandbox/data/images"}
    ensure_dir(output_dirs["html"])
    ensure_dir(output_dirs["images"])

    semaphore = asyncio.Semaphore(_max_concurrent)
    current_level: list[str] = [seed_norm]

    for depth in range(_max_depth + 1):
        if not current_level:
            logger.info("No more URLs at depth %d — crawl finished.", depth)
            break

        logger.info("Depth %d: processing %d URL(s) (max_concurrent=%d)…",
                     depth, len(current_level), _max_concurrent)

        async def _worker(url: str) -> dict[str, Any]:
            async with semaphore:
                return await process_page(
                    url, depth, bloom,
                    allowed_domains=_allowed_domains,
                    white_list_patterns=_white_patterns,
                    api_client=api_client,
                    task_id=task_id,
                    seed_meta=seed_meta,
                    image_concurrency=_max_concurrent,
                )

        results = await asyncio.gather(
            *[_worker(u) for u in current_level], return_exceptions=True,
        )

        next_level: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Worker crashed: %s", result)
                stats.add_result({
                    "success": False,
                    "url": "(worker crash)",
                    "depth": depth,
                    "html_path": None,
                    "images": [],
                    "links": [],
                    "error": str(result),
                })
                continue

            stats.add_result(result)

            if not result.get("success"):
                continue

            new_links: list[str] = result.get("links", [])

            # Optional dead-link filtering ----------------------------------
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

            for link in new_links:
                if not bloom.contains(link):
                    bloom.add(link)
                    next_level.append(link)

        current_level = next_level

    stats.stop()
    logger.info("Crawl complete.  %d pages processed.", stats.total)
    return stats


# ===================================================================
# Smoke test
# ===================================================================

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
        assert st is not None
        assert st.total >= 1, "Expected at least 1 page attempted"
        assert st.success >= 1, "Expected at least 1 page succeeded"
        print("crawler.py — smoke test passed.")

    asyncio.run(_main())
