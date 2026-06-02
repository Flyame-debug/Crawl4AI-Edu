"""Standalone crawler — assembles A1–A4 modules into a runnable BFS crawler."""

from .crawler import crawl

__all__ = ["crawl"]


if __name__ == "__main__":
    print(f"standalone_crawler package — exports: {__all__}")
    print("Import OK.")
