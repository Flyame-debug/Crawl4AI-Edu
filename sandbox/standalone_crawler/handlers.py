"""Single-page processing handler.

Fetches HTML, extracts links, and sends data directly to backend API.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure sandbox/ and project root are on sys.path for all import styles.
_sandbox = str(Path(__file__).resolve().parent.parent)
_project_root = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_sandbox, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fetcher import FetchError, async_fetch
from link import extract_links

from .utils import get_logger, normalize_url

logger = get_logger("standalone_crawler.handlers")

# 导入 requests 用于回调后端 API
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests 库未安装，无法回调后端 API")


async def send_to_backend(url: str, html: str, backend_url: str = None) -> dict:
    """将抓取的页面数据直接发送到 Django 后端 API"""
    if not REQUESTS_AVAILABLE:
        return {"success": False, "error": "requests not available"}
    
    if backend_url is None:
        backend_url = "http://127.0.0.1:8000"
    
    api_endpoint = f"{backend_url}/api/pagesnapshot/"
    
    data = {
        "url": url,
        "markdown": html,  # 暂时用 HTML，后续可由成员B转换为 Markdown
        "category": None,  # 后端会自动分类
    }
    
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(api_endpoint, json=data, timeout=10)
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info("数据已入库: %s (action=%s)", url, result.get('action', 'unknown'))
            return {"success": True, "data": result}
        else:
            logger.warning("入库失败: %s, status=%s", url, response.status_code)
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error("回调后端 API 异常: %s - %s", url, str(e))
        return {"success": False, "error": str(e)}


async def process_page(
    url: str,
    current_depth: int,
    bloom_filter: Any,
    allowed_domains: list[str] | None = None,
    white_list_patterns: list[str] | None = None,
    backend_url: str = None,
) -> dict:
    """Process a single page: fetch → send to backend → extract links.

    Args:
        url: Absolute URL of the page to process.
        current_depth: BFS depth of this page (0 = seed).
        bloom_filter: Object with ``add(url)`` and ``contains(url)`` methods.
        allowed_domains: Optional domain whitelist for link extraction.
        white_list_patterns: Optional URL-path regex whitelist.
        backend_url: Backend API URL for storing data.

    Returns:
        A dict with keys ``success``, ``url``, ``depth``, ``links``, and ``error``.
    """
    _domains = allowed_domains if allowed_domains is not None else []
    _patterns = white_list_patterns if white_list_patterns is not None else []
    
    result: dict[str, Any] = {
        "success": False,
        "url": url,
        "depth": current_depth,
        "links": [],
        "error": None,
    }

    # 1. Fetch HTML ------------------------------------------------------------
    try:
        html: str = await async_fetch(url)
    except FetchError as exc:
        result["error"] = str(exc)
        logger.warning("Fetch failed for %s: %s", url, exc)
        return result
    except Exception as exc:
        result["error"] = f"Unexpected fetch error: {exc}"
        logger.error("Unexpected error fetching %s: %s", url, exc)
        return result

    # 2. 直接发送到后端 API（不保存本地文件）------------------------------------
    callback_result = await send_to_backend(url, html, backend_url)
    if not callback_result.get("success"):
        logger.warning("数据未入库: %s, %s", url, callback_result.get("error"))
        # 注意：即使入库失败，仍然继续提取链接

    # 3. Extract & filter links ------------------------------------------------
    try:
        raw_links: list[str] = extract_links(html, url, allowed_domains=_domains, white_list_patterns=_patterns)
    except Exception as exc:
        logger.warning("Link extraction failed for %s: %s", url, exc)
        raw_links = []

    new_links: list[str] = []
    for link in raw_links:
        try:
            normalized: str = normalize_url(link, url)
        except Exception:
            continue
        if not normalized or not normalized.startswith(("http://", "https://")):
            continue
        if not bloom_filter.contains(normalized):
            new_links.append(normalized)

    result["links"] = new_links
    result["success"] = True
    logger.info(
        "Page processed: %s depth=%d links=%d",
        url,
        current_depth,
        len(new_links),
    )
    return result


if __name__ == "__main__":
    import asyncio
    from link import create_bloom_filter

    async def _test() -> None:
        bf = create_bloom_filter("memory")
        bf.add("https://httpbin.org/html")

        result = await process_page(
            "https://httpbin.org/html",
            0,
            bf,
            backend_url="http://127.0.0.1:8000",
        )
        print("\nResult:")
        print(f"  success: {result['success']}")
        print(f"  url: {result['url']}")
        print(f"  links count: {len(result['links'])}")
        print(f"  error: {result['error']}")

    asyncio.run(_test())