"""Dead link checker — concurrent HEAD-request based dead link detection."""

from .checker import check_dead_links

__all__ = ["check_dead_links"]
