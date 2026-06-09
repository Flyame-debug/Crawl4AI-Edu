"""Async API client for Crawl4AI backend integration.

Implements all 7 endpoints defined in sandbox/interface_doc.md using aiohttp
with automatic retry (exponential backoff, max 3 attempts) and timeout control.

Base URL is read from the ``CRAWLER_BACKEND_URL`` environment variable
(default ``http://127.0.0.1:8000``).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import aiohttp

from .utils import get_logger

logger = get_logger("standalone_crawler.api_client")

_DEFAULT_BASE_URL: str = "http://127.0.0.1:8000"
_DEFAULT_TIMEOUT: int = 30
_MAX_RETRIES: int = 3
_RETRY_BACKOFF_BASE: float = 1.0


class APIClientError(Exception):
    """Raised when an API call exhausts all retry attempts."""


class APIClient:
    """Async HTTP client for the Crawl4AI backend REST API.

    Public methods (7):
        get_config, get_pending_seeds, update_seed_status, start_crawl_task,
        upload_image_base64, save_page_snapshot, report_task_result.
    """

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(
        self,
        base_url: str | None = None,
        max_retries: int = _MAX_RETRIES,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url: str = (base_url or os.getenv("CRAWLER_BACKEND_URL", _DEFAULT_BASE_URL)).rstrip("/")
        self._max_retries: int = max_retries
        self._timeout: int = timeout
        logger.info("APIClient initialised — base_url=%s max_retries=%d timeout=%ds",
                     self._base_url, self._max_retries, self._timeout)

    # ------------------------------------------------------------------
    # Endpoint 1: GET /api/crawler/config/db/
    # ------------------------------------------------------------------

    async def get_config(self) -> dict[str, Any]:
        """Fetch crawler configuration from the backend.

        Returns:
            Dict with keys: concurrency, request_delay, max_depth,
            allowed_domains, white_list_patterns, enable_dead_check.
        """
        url = f"{self._base_url}/api/crawler/config/db/"
        return await self._request("GET", url)

    # ------------------------------------------------------------------
    # Endpoint 2: GET /api/seeds/pending/?limit=N
    # ------------------------------------------------------------------

    async def get_pending_seeds(self, limit: int = 10) -> dict[str, Any]:
        """Fetch pending crawl seeds.

        Args:
            limit: Maximum number of seeds to return.

        Returns:
            Dict with keys ``count`` and ``seeds`` (list of seed objects).
        """
        url = f"{self._base_url}/api/seeds/pending/?limit={limit}"
        return await self._request("GET", url)

    # ------------------------------------------------------------------
    # Endpoint 3: POST /api/seeds/status/
    # ------------------------------------------------------------------

    async def update_seed_status(self, url: str, status: str) -> dict[str, Any]:
        """Update the status of a seed URL.

        Args:
            url: The seed URL to update.
            status: One of pending / crawling / success / failed / blocked.

        Returns:
            Response dict, typically {"status": "ok", "url": ..., "new_status": ...}.
        """
        endpoint = f"{self._base_url}/api/seeds/status/"
        payload: dict[str, str] = {"url": url, "status": status}
        return await self._request("POST", endpoint, json=payload)

    # ------------------------------------------------------------------
    # Endpoint 6: POST /api/crawl/start/
    # ------------------------------------------------------------------

    async def start_crawl_task(
        self,
        seed_url: str,
        max_depth: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Start a crawl task and obtain a task_id.

        Args:
            seed_url: The seed URL for the crawl.
            max_depth: Maximum crawl depth (optional).
            config: Additional configuration dict (optional).

        Returns:
            Dict with ``task_id``, ``message``, ``status_url``, ``created_at``.
        """
        endpoint = f"{self._base_url}/api/crawl/start/"
        payload: dict[str, Any] = {"seed_url": seed_url}
        if max_depth is not None:
            payload["max_depth"] = max_depth
        if config is not None:
            payload["config"] = config
        return await self._request("POST", endpoint, json=payload)

    # ------------------------------------------------------------------
    # Endpoint 4: POST /api/images/upload/  (base64)
    # ------------------------------------------------------------------

    async def upload_image_base64(
        self,
        image_base64_str: str,
        filename: str,
    ) -> dict[str, Any]:
        """Upload an image as a base64-encoded string.

        Args:
            image_base64_str: Base64-encoded image data (without data URI prefix).
            filename: Suggested filename for the uploaded image.

        Returns:
            Dict with ``success``, ``url``, ``image_id``, ``filename``.
        """
        endpoint = f"{self._base_url}/api/images/upload/"
        payload: dict[str, str] = {
            "image_base64": image_base64_str,
            "filename": filename,
        }
        return await self._request("POST", endpoint, json=payload)

    # ------------------------------------------------------------------
    # Endpoint 5: POST /api/pagesnapshot/
    # ------------------------------------------------------------------

    async def save_page_snapshot(
        self,
        url: str,
        markdown: str,
        category: str | None = None,
        images: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Save a crawled page snapshot to the backend.

        Args:
            url: Page URL (required).
            markdown: Page content / HTML (required).
            category: Optional category hint.
            images: Optional list of {"original_url": str, "stored_url": str}.

        Returns:
            Dict with ``action`` (created/updated/skipped) and ``data``.
        """
        endpoint = f"{self._base_url}/api/pagesnapshot/"
        payload: dict[str, Any] = {"url": url, "markdown": markdown}
        if category is not None:
            payload["category"] = category
        if images is not None:
            payload["images"] = images
        return await self._request("POST", endpoint, json=payload)

    # ------------------------------------------------------------------
    # Endpoint 7: POST /api/tasks/{task_id}/result/
    # ------------------------------------------------------------------

    async def report_task_result(
        self,
        task_id: str,
        status: str,
        total_pages: int | None = None,
        success_pages: int | None = None,
        failed_pages: int | None = None,
        report: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        """Report the final result of a crawl task.

        Args:
            task_id: Task ID from start_crawl_task.
            status: ``completed`` or ``failed``.
            total_pages: Total pages crawled.
            success_pages: Successfully crawled pages.
            failed_pages: Failed pages.
            report: Human-readable summary.
            error_message: Error description (when status=failed).

        Returns:
            Dict with ``success``, ``task_id``, ``status``.
        """
        endpoint = f"{self._base_url}/api/tasks/{task_id}/result/"
        payload: dict[str, Any] = {"status": status}
        if total_pages is not None:
            payload["total_pages"] = total_pages
        if success_pages is not None:
            payload["success_pages"] = success_pages
        if failed_pages is not None:
            payload["failed_pages"] = failed_pages
        if report is not None:
            payload["report"] = report
        if error_message is not None:
            payload["error_message"] = error_message
        return await self._request("POST", endpoint, json=payload)

    # ------------------------------------------------------------------
    # Internal: retry-aware HTTP request
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Issue an async HTTP request with exponential-backoff retry.

        Args:
            method: HTTP method (GET, POST, …).
            url: Full endpoint URL.
            json: Optional JSON body for POST requests.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            APIClientError: When all retry attempts are exhausted.
        """
        last_error: str = ""
        for attempt in range(1, self._max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as session:
                    async with session.request(method, url, json=json) as resp:
                        # Read body once.
                        text: str = await resp.text()
                        if resp.status < 500:
                            # Client errors (4xx) and success (2xx) — do not retry.
                            try:
                                return _parse_json(text)
                            except ValueError:
                                logger.error("Invalid JSON from %s %s: %s", method, url, text[:200])
                                raise APIClientError(f"Invalid JSON response: {text[:200]}")
                        # 5xx — server error, retry.
                        last_error = f"HTTP {resp.status}: {text[:200]}"
                        logger.warning(
                            "Server error on %s %s (attempt %d/%d): %s",
                            method, url, attempt, self._max_retries, last_error,
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = str(exc)
                logger.warning(
                    "Network error on %s %s (attempt %d/%d): %s",
                    method, url, attempt, self._max_retries, exc,
                )
            except APIClientError:
                raise
            except Exception as exc:
                last_error = str(exc)
                logger.error(
                    "Unexpected error on %s %s (attempt %d/%d): %s",
                    method, url, attempt, self._max_retries, exc,
                )

            # Exponential backoff before next retry.
            if attempt < self._max_retries:
                wait: float = _RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.info("Retrying %s %s in %.1fs …", method, url, wait)
                await asyncio.sleep(wait)

        raise APIClientError(
            f"All {self._max_retries} attempts exhausted for {method} {url}: {last_error}"
        )


def _parse_json(text: str) -> dict[str, Any]:
    """Parse *text* as JSON, raising ``ValueError`` on failure."""
    import json as _json

    data: Any = _json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")
    return data


# ------------------------------------------------------------------
# Smoke test
# ------------------------------------------------------------------

if __name__ == "__main__":
    async def _main() -> None:
        print("api_client.py — smoke test (no backend required)")

        client = APIClient(base_url="http://127.0.0.1:8000", max_retries=1, timeout=5)

        # Verify all methods exist.
        for attr in (
            "get_config", "get_pending_seeds", "update_seed_status",
            "start_crawl_task", "upload_image_base64",
            "save_page_snapshot", "report_task_result",
        ):
            assert hasattr(client, attr), f"Missing method: {attr}"
        print("All 7 API methods present.")

        # Verify _parse_json helper.
        assert _parse_json('{"a":1}') == {"a": 1}
        try:
            _parse_json("not json")
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError for invalid JSON")
        print("JSON parsing helper works.")

        print("api_client.py — smoke test passed.")

    asyncio.run(_main())
