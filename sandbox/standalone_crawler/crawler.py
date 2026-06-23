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

from crawler.quality_report import generate_quality_report

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
    seed_urls: list[str] | None = None,
    output_dir: str | None = None,
    no_graceful: bool = False,
    resume_path: str | None = None,
    task_type: str = "full",
    preview_limit: int = 10,
    user_prompt: str | None = None,
    task_id: str = None, 
    
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

    **Preview mode** (``task_type="preview"``):
        Crawls at most *preview_limit* pages, saves locally to
        ``sandbox/preview_data/``, and does NOT call any backend API.
        Intended for quick validation before a full crawl.

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
        task_type: ``"preview"`` or ``"full"`` (default).  Preview mode limits
            pages and skips backend API calls.
        preview_limit: Max pages in preview mode (default 10).

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
                    task_type="formal",
                    user_prompt=seed.get("user_prompt"),
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
                    task_type=task_type, preview_limit=10,
                    user_prompt=seed.get("user_prompt"),
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
        # Health check before entering the polling loop.
        healthy: bool = await api_client.check_health()
        if not healthy:
            logger.warning(
                "Backend health check failed — worker will continue but API calls may fail."
            )
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
            task_type="formal",
            user_prompt=seed_meta.get("user_prompt") if seed_meta else None,
        )
        task_id: str = task_resp.get("task_id", "")
        await api_client.update_seed_status(seed_url, "crawling")
        stats: Statistics = await _run_bfs_crawl(
            seed_url=seed_url, max_depth=max_depth, max_concurrent=max_concurrent,
            enable_dead_check=enable_dead_check, allowed_domains=allowed_domains,
            white_list_patterns=white_list_patterns, request_delay=request_delay,
            config_path=config_path, api_client=api_client,
            task_id=task_id, seed_meta=seed_meta,
            task_type="full", preview_limit=10,
            user_prompt=seed_meta.get("user_prompt") if seed_meta else None,
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
        config_path=config_path, seed_urls=seed_urls, output_dir=output_dir,
        resume_path=resume_path, task_type=task_type, preview_limit=preview_limit,
        user_prompt=user_prompt,
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
    seed_urls: list[str] | None = None,
    output_dir: str | None = None,
    resume_path: str | None = None,
    task_type: str = "full",
    preview_limit: int = 10,
    user_prompt: str | None = None,
) -> Statistics:
    """Core BFS crawl engine — processes one seed URL breadth-first.

    In preview mode (*task_type* ``"preview"``) the engine stops after
    *preview_limit* successful pages regardless of depth, and all output
    goes to the local filesystem (no API calls).
    """
    _is_preview = task_type == "preview"
    # Map legacy "full" → V2 "formal" for API calls.
    _api_task_type: str = "formal" if task_type == "full" else task_type

    # ============================================================
    # ✅ 新增：停止信号检查函数
    # ============================================================
    def _should_stop() -> bool:
        """检查任务是否应该停止"""
        if task_id is None:
            return False
        try:
            # 尝试从 views 导入信号
            from apps.api.views import TASK_CONTROL_SIGNALS, TASK_CONTROL_LOCK
            with TASK_CONTROL_LOCK:
                signal = TASK_CONTROL_SIGNALS.get(task_id, {})
                return signal.get('is_stop', False)
        except ImportError:
            # 如果在独立环境中运行，无法导入 Django 信号
            return False
        except Exception:
            return False

    # --- Resolve config -------------------------------------------------------
    cfg: dict[str, Any] = {}
    if config_path is not None:
        cfg = load_config(config_path)

    _max_depth = max_depth if max_depth is not None else cfg.get("max_depth", 2)
    _max_concurrent = max_concurrent if max_concurrent is not None else cfg.get("concurrency", 5)
    _req_delay = request_delay if request_delay is not None else cfg.get("request_delay", 1.0)
    _allowed_domains = allowed_domains if allowed_domains is not None else cfg.get("default_allowed_domains", [])
    _white_patterns = white_list_patterns if white_list_patterns is not None else cfg.get("white_list_patterns", [])

    if _is_preview:
        logger.info("预览模式 (Preview Mode): 最多抓取 %d 个页面", preview_limit)

    dead_checker = _check_dead_links
    if enable_dead_check and dead_checker is None:
        logger.warning("enable_dead_check=True but dead_link_checker is not available; skipped.")

    # --- Resume / checkpoint support ------------------------------------------
    _crawled_set: set[str] = set()
    _resume_queue: asyncio.Queue[str | None] = asyncio.Queue()
    _resume_lock = asyncio.Lock()

    if resume_path and api_client is None:
        _rp = Path(resume_path)
        if _rp.is_file():
            _crawled_set = set(
                line.strip() for line in _rp.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
            logger.info("Resume: loaded %d already-crawled URL(s) from %s", len(_crawled_set), resume_path)

        async def _resume_writer() -> None:
            """Background task that drains the queue and appends to resume file."""
            _rp.parent.mkdir(parents=True, exist_ok=True)
            with open(_rp, "a", encoding="utf-8") as f:
                while True:
                    u = await _resume_queue.get()
                    if u is None:  # Sentinel to stop.
                        break
                    f.write(u + "\n")
                    f.flush()
            logger.info("Resume writer stopped — file saved to %s", resume_path)

        _writer_task = asyncio.create_task(_resume_writer())
    else:
        _writer_task = None

    stats = Statistics()
    stats.start()

    bloom = create_bloom_filter("memory")

    # Resolve output directory and mapping file.
    _output_dir = output_dir or "sandbox/data"
    _mapping_path: str | None = None
    if api_client is None:
        _mapping_path = f"{_output_dir}/mapping.txt"
    ensure_dir(f"{_output_dir}/html")
    ensure_dir(f"{_output_dir}/md")
    ensure_dir(f"{_output_dir}/images")

    # Build initial seed list: either from seed_urls or single seed_url.
    skipped_resume: int = 0
    if seed_urls:
        initial_urls: list[str] = []
        for u in seed_urls:
            nu = normalize_url(u)
            if nu in _crawled_set:
                skipped_resume += 1
                continue
            if not bloom.contains(nu):
                bloom.add(nu)
                initial_urls.append(nu)
        logger.info("Loaded %d unique seed URLs (from %d input), skipped %d already-crawled",
                     len(initial_urls), len(seed_urls), skipped_resume)
    else:
        seed_norm = normalize_url(seed_url)
        if seed_norm in _crawled_set:
            logger.info("Seed URL already crawled in previous session — nothing to do.")
            if _writer_task:
                await _resume_queue.put(None)
                await _writer_task
            stats.stop()
            return stats
        bloom.add(seed_norm)
        initial_urls = [seed_norm]

    semaphore = asyncio.Semaphore(_max_concurrent)
    current_level: list[str] = initial_urls
    _preview_pages_done: int = 0  # Counter for preview mode page limit.
    _all_page_results: list[dict[str, Any]] = []  # Accumulate for quality report.

    for depth in range(_max_depth + 1):
        # ✅ 每次循环开始前检查停止信号
        if _should_stop():
            logger.warning(f"⏹️ 任务 {task_id} 被用户停止，终止爬取 (depth={depth})")
            break

        if not current_level:
            logger.info("No more URLs at depth %d — crawl finished.", depth)
            break

        # Preview mode: enforce page limit before processing this level.
        if _is_preview and _preview_pages_done >= preview_limit:
            logger.info(
                "预览模式: 已达到上限 %d 页, 停止抓取 (depth=%d).",
                preview_limit, depth,
            )
            break

        logger.info("Depth %d: processing %d URL(s) (max_concurrent=%d)…",
                     depth, len(current_level), _max_concurrent)

        async def _worker(url: str) -> dict[str, Any]:
            # ✅ 在 worker 中也检查停止信号
            if _should_stop():
                return {
                    "success": False, "url": url, "depth": depth,
                    "links": [], "images": [], "error": "Task stopped by user",
                    "stopped": True,
                }
            # Skip already-crawled URLs (resume mode).
            if url in _crawled_set:
                return {
                    "success": True, "url": url, "depth": depth,
                    "links": [], "images": [], "error": None, "skipped": True,
                }
            async with semaphore:
                result = await process_page(
                    url, depth, bloom,
                    allowed_domains=_allowed_domains,
                    white_list_patterns=_white_patterns,
                    api_client=api_client,
                    task_id=task_id,
                    seed_meta=seed_meta,
                    image_concurrency=_max_concurrent,
                    output_dir=_output_dir,
                    mapping_path=_mapping_path,
                    task_type=_api_task_type,
                    user_prompt=user_prompt,
                )
                # On success, record URL for checkpoint/resume.
                if result.get("success") and _writer_task is not None:
                    await _resume_queue.put(url)
                return result

        results = await asyncio.gather(
            *[_worker(u) for u in current_level], return_exceptions=True,
        )

        # ✅ 收集完结果后再次检查停止信号
        if _should_stop():
            logger.warning(f"⏹️ 任务 {task_id} 被用户停止，停止处理当前层级结果")
            break

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

            # ✅ 如果是停止信号导致的失败，不继续处理
            if result.get("stopped", False):
                logger.info("⏹️ 任务被停止，跳过后续结果")
                break

            stats.add_result(result)
            _all_page_results.append(result)

            if not result.get("success"):
                continue

            # Preview mode: increment completed page counter.
            if _is_preview:
                _preview_pages_done += 1
                if _preview_pages_done >= preview_limit:
                    # Do not queue more links for the next level.
                    logger.info(
                        "预览模式: %d/%d 页面已完成, 不再收集新链接.",
                        _preview_pages_done, preview_limit,
                    )

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

            # Preview mode: stop collecting links once limit is reached.
            if _is_preview and _preview_pages_done >= preview_limit:
                continue

            # ✅ 收集链接前检查停止信号
            if _should_stop():
                logger.warning(f"⏹️ 任务 {task_id} 被用户停止，停止收集新链接")
                break

            for link in new_links:
                if not bloom.contains(link):
                    bloom.add(link)
                    next_level.append(link)

        # ✅ 如果因停止信号跳出，不再继续下一层
        if _should_stop():
            logger.warning(f"⏹️ 任务 {task_id} 被用户停止，终止爬取")
            break

        # Preview mode: stop descending if limit already reached.
        if _is_preview and _preview_pages_done >= preview_limit:
            logger.info("预览模式: 已收集 %d 页, 停止继续抓取.", _preview_pages_done)
            current_level = []
        else:
            current_level = next_level

    # --- Stop resume writer and clean up ---------------------------------------
    if _writer_task is not None:
        await _resume_queue.put(None)   # Sentinel to stop writer.
        await _writer_task

    stats.stop()
    logger.info("Crawl complete.  %d pages processed.", stats.total)

    # --- Generate quality report ---------------------------------------------
    _report_dir: str = f"{_output_dir}/reports"
    try:
        _report_path: str = generate_quality_report(
            stats, _all_page_results, _report_dir,
            task_label=task_type,
        )
        logger.info("Quality report saved: %s", _report_path)
    except Exception as exc:
        logger.warning("Failed to generate quality report: %s", exc)

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
