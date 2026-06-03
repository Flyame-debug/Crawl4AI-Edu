"""Statistics collection and reporting for the standalone crawler."""

from __future__ import annotations

import time


class Statistics:
    """Collects per-page results and produces a summary report.

    Public methods:
        start() / stop() — record wall-clock boundaries.
        add_result(result) — ingest a ``process_page`` return dict.
        report() — return a formatted multi-line summary string.
    """

    def __init__(self) -> None:
        self.total: int = 0
        self.success: int = 0
        self.failed: int = 0
        self.total_images: int = 0
        self.start_time: float | None = None
        self.end_time: float | None = None

    def start(self) -> None:
        """Record the crawl start time."""
        self.start_time = time.monotonic()

    def stop(self) -> None:
        """Record the crawl end time."""
        self.end_time = time.monotonic()

    def add_result(self, result: dict) -> None:
        """Update counters from a ``process_page`` result dictionary.

        Args:
            result: Dict with keys ``success``, ``images`` (dict), and
                optionally ``error``.
        """
        self.total += 1
        if result.get("success"):
            self.success += 1
            imgs: dict = result.get("images", {})
            self.total_images += len(imgs)
        else:
            self.failed += 1

    def report(self) -> str:
        """Return a human-readable statistics summary.

        Returns:
            Multi-line string suitable for direct printing.
        """
        elapsed: float = 0.0
        if self.start_time is not None and self.end_time is not None:
            elapsed = self.end_time - self.start_time

        lines = [
            "=" * 50,
            "           Crawl Statistics",
            "=" * 50,
            f"  Pages attempted : {self.total}",
            f"  Pages succeeded : {self.success}",
            f"  Pages failed    : {self.failed}",
            f"  Images downloaded: {self.total_images}",
            f"  Time elapsed    : {elapsed:.2f} s",
            "=" * 50,
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    stats = Statistics()
    stats.start()
    stats.add_result({"success": True, "url": "http://a.com", "depth": 0,
                      "html_path": "/tmp/a.html", "images": {"a.png": "/tmp/a.png"},
                      "links": [], "error": None})
    stats.add_result({"success": False, "url": "http://b.com", "depth": 0,
                      "html_path": None, "images": {}, "links": [],
                      "error": "timeout"})
    stats.stop()
    print(stats.report())
    assert stats.total == 2
    assert stats.success == 1
    assert stats.failed == 1
    assert stats.total_images == 1
    print("stats.py — all assertions passed.")
