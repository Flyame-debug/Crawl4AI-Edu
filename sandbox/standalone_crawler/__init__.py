"""Standalone crawler — assembles A1–A4 modules into a runnable BFS crawler."""

from .api_client import APIClient, APIClientError
from .crawler import crawl, load_config

__all__ = ["crawl", "load_config", "APIClient", "APIClientError"]


if __name__ == "__main__":
    print(f"standalone_crawler package — exports: {__all__}")
    print("Import OK.")
