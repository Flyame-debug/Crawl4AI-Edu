"""Image downloader — extract & download ``<img>`` assets from HTML."""

from sandbox.image_downloader.core import download_images

__all__ = ["download_images"]


if __name__ == "__main__":
    print(f"image_downloader package — exports: {__all__}")
    print("Import OK.")
