"""Async fetch engine — static (aiohttp) and dynamic (playwright) fetching."""

from .core import async_fetch
from .exceptions import FetchError
from .ua_pool import USER_AGENTS, get_random_ua

__all__ = ["async_fetch", "FetchError", "get_random_ua", "USER_AGENTS"]


if __name__ == "__main__":
    print(f"fetcher package — exports: {__all__}")
    print(f"UA pool size: {len(USER_AGENTS)}")
    print("Import OK.")
