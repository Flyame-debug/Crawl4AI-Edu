"""Unit tests for the image downloader module (pytest + pytest-asyncio).

Usage::

    pytest sandbox/image_downloader/test_image_downloader.py -v
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import pytest_asyncio
from aiohttp import web

from sandbox.image_downloader.core import (
    _download_single,
    _extract_image_urls,
    download_images,
)
from sandbox.image_downloader.utils import (
    _extract_filename_from_cd,
    infer_extension,
)

# ---------------------------------------------------------------------------
# Quiet down the module logger during tests.
# ---------------------------------------------------------------------------
logging.getLogger("image_downloader").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Stateful counter for the /flaky endpoint (retry tests).
# ---------------------------------------------------------------------------
_flaky_call_count: int = 0


# ===================================================================
# aiohttp test-application factory
# ===================================================================


def _build_test_app() -> web.Application:
    """Create an aiohttp *Application* with endpoints simulating various
    real-world server behaviours."""
    app = web.Application()

    # -- Normal images --------------------------------------------------------
    async def _ok_png(_req: web.Request) -> web.Response:
        return web.Response(body=b"\x89PNG\r\n\x1a\nfake-png", content_type="image/png")

    async def _ok_jpg(_req: web.Request) -> web.Response:
        return web.Response(body=b"\xff\xd8\xff\xe0fake-jpg", content_type="image/jpeg")

    async def _ok_ico(_req: web.Request) -> web.Response:
        return web.Response(body=b"\x00\x00\x01\x00fake-ico", content_type="image/x-icon")

    # -- Content-Disposition --------------------------------------------------
    async def _with_cd(_req: web.Request) -> web.Response:
        return web.Response(
            body=b"fake-gif-data",
            content_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="banner.gif"'},
        )

    # -- Client errors (no retry) ---------------------------------------------
    async def _not_found(_req: web.Request) -> web.Response:
        return web.Response(status=404, body=b"Not Found")

    # -- Server error → success (retry test) ----------------------------------
    async def _flaky(_req: web.Request) -> web.Response:
        global _flaky_call_count
        _flaky_call_count += 1
        if _flaky_call_count == 1:
            return web.Response(status=500, body=b"Internal Server Error")
        return web.Response(body=b"flaky-png-data", content_type="image/png")

    # -- Slow endpoint (timeout test) -----------------------------------------
    async def _slow(_req: web.Request) -> web.Response:
        await asyncio.sleep(5)
        return web.Response(body=b"too-late")

    app.router.add_get("/ok.png", _ok_png)
    app.router.add_get("/ok.jpg", _ok_jpg)
    app.router.add_get("/ok.ico", _ok_ico)
    app.router.add_get("/with-cd", _with_cd)
    app.router.add_get("/not-found", _not_found)
    app.router.add_get("/flaky", _flaky)
    app.router.add_get("/slow", _slow)

    return app


# ===================================================================
# Async fixture — aiohttp test server on a random port
# ===================================================================


@pytest_asyncio.fixture
async def test_server() -> str:
    """Start a local aiohttp test server and return its base URL."""
    global _flaky_call_count
    _flaky_call_count = 0  # reset before each test

    app = _build_test_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()

    # Extract the dynamically assigned port.
    _sockets = site._server.sockets  # type: ignore[union-attr]
    port: int = _sockets[0].getsockname()[1]
    base_url: str = f"http://127.0.0.1:{port}"

    yield base_url

    await runner.cleanup()


# ===================================================================
# Test cases
# ===================================================================


class TestImageDownloader:
    """Grouped tests covering extension inference, URL extraction, download,
    retry logic, and error handling."""

    # ------------------------------------------------------------------
    # 1. infer_extension & Content-Disposition
    # ------------------------------------------------------------------

    def test_infer_extension_and_cd(self) -> None:
        """All extension-inference paths including new MIME types and CD."""
        # URL path takes priority
        assert infer_extension("https://x.com/a.png") == ".png"
        assert infer_extension("https://x.com/a.jpeg") == ".jpg"
        assert infer_extension("https://x.com/a", "image/webp") == ".webp"

        # New MIME types
        assert infer_extension("https://x.com/f", "image/x-icon") == ".ico"
        assert infer_extension("https://x.com/f", "image/tiff") == ".tiff"
        assert (
            infer_extension("https://x.com/f", "image/vnd.microsoft.icon") == ".ico"
        )

        # Content-Disposition fallback (only consulted when URL + CT fail)
        assert (
            infer_extension(
                "https://x.com/img",
                content_disposition='attachment; filename="photo.png"',
            )
            == ".png"
        )
        assert (
            infer_extension(
                "https://x.com/img",
                content_disposition="attachment; filename=icon.ico",
            )
            == ".ico"
        )

        # Priority chain: URL > Content-Type > Content-Disposition > .jpg
        assert (
            infer_extension(
                "https://x.com/img.gif",
                "image/jpeg",
                content_disposition='attachment; filename="x.png"',
            )
            == ".gif"
        )  # URL wins
        assert (
            infer_extension(
                "https://x.com/img",
                "image/png",
                content_disposition='attachment; filename="x.gif"',
            )
            == ".png"
        )  # CT wins over CD
        assert infer_extension("https://x.com/img") == ".jpg"  # default

        # Content-Disposition parser edge cases
        assert _extract_filename_from_cd(None) is None
        assert _extract_filename_from_cd("") is None
        assert _extract_filename_from_cd("inline") is None
        assert (
            _extract_filename_from_cd('attachment; filename="pic.jpg"') == "pic.jpg"
        )
        assert _extract_filename_from_cd("attachment; filename=pic.jpg") == "pic.jpg"

    # ------------------------------------------------------------------
    # 2. URL extraction
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_extract_image_urls(self) -> None:
        """Extraction and filtering of <img src> attributes."""
        html = """<html><body>
            <img src="/a.png">
            <img src="">
            <img>
            <img src="data:image/png;base64,xxx">
            <img src="javascript:void(0)">
            <img src="https://cdn.example.com/b.jpg">
        </body></html>"""

        urls = _extract_image_urls(html, "https://example.com/page/")
        assert len(urls) == 2
        assert urls[0] == "https://example.com/a.png"
        assert urls[1] == "https://cdn.example.com/b.jpg"

    # ------------------------------------------------------------------
    # 3. Normal download + dedup (integration)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_download_normal_and_dedup(
        self, test_server: str, tmp_path: Path
    ) -> None:
        """Download valid images; verify dedup maps duplicate URLs to the
        same local file."""
        html = f"""<html><body>
            <img src="{test_server}/ok.png">
            <img src="{test_server}/ok.jpg">
            <img src="{test_server}/ok.png">  <!-- duplicate -->
            <img src="data:image/png;base64,xxx">   <!-- filtered -->
        </body></html>"""

        result = await download_images(
            html=html,
            base_url=test_server,
            output_dir=str(tmp_path),
            concurrency=3,
        )

        # 3 src entries in HTML (ok.png ×2, ok.jpg ×1), but the return
        # dict has unique keys → 2 entries (one per unique absolute URL).
        assert len(result) == 2
        assert len(set(result.values())) == 2  # 2 unique local paths

        for local_path in result.values():
            assert os.path.isfile(local_path)
            assert os.path.getsize(local_path) > 0

        # ok.png appears once as a dict key (dedup is by absolute URL).
        assert f"{test_server}/ok.png" in result
        assert f"{test_server}/ok.jpg" in result

    # ------------------------------------------------------------------
    # 4. Retry behaviour
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_download_retry(self, test_server: str, tmp_path: Path) -> None:
        """Server error (500) triggers retry; client error (404) does not."""
        global _flaky_call_count
        _flaky_call_count = 0

        html = f"""<html><body>
            <img src="{test_server}/flaky">
            <img src="{test_server}/not-found">
        </body></html>"""

        result = await download_images(
            html=html,
            base_url=test_server,
            output_dir=str(tmp_path),
            concurrency=3,
        )

        # /flaky succeeds after retry (500 → 200); /not-found is skipped
        flaky_url = f"{test_server}/flaky"
        not_found_url = f"{test_server}/not-found"

        assert flaky_url in result
        assert os.path.isfile(result[flaky_url])
        assert not_found_url not in result
        assert _flaky_call_count == 2  # first call 500, second 200

    # ------------------------------------------------------------------
    # 5. Error handling — timeout & unexpected exceptions
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_error_handling(
        self, test_server: str, tmp_path: Path
    ) -> None:
        """Download against a slow endpoint times out; no exception
        propagates to the caller."""

        # Use _download_single directly with a 0.1 s timeout to force a
        # timeout on the /slow endpoint (which sleeps 5 s).
        output_path = tmp_path
        sem = asyncio.Semaphore(5)
        timeout = aiohttp.ClientTimeout(total=0.1)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            result = await _download_single(
                session,
                sem,
                f"{test_server}/slow",
                output_path,
                {"User-Agent": "pytest", "Referer": test_server},
            )

        # Should be None (all retries exhausted on timeout)
        assert result is None

        # Verify that a truly unreachable URL is handled gracefully.
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=1)
        ) as session:
            result2 = await _download_single(
                session,
                sem,
                "http://127.0.0.1:1/nothing",  # nothing listening
                output_path,
                {"User-Agent": "pytest"},
            )
        assert result2 is None


# ===================================================================
# Runner
# ===================================================================

if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"] + sys.argv[1:]))
