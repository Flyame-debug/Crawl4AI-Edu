"""School-specific configuration loader for the standalone crawler.

Provides ``load_school_config(domain)`` which looks up a JSON configuration
file under ``sandbox/config/schools/`` based on the domain of a seed URL.

Usage::

    from standalone_crawler.config_loader import load_school_config
    cfg = load_school_config("faculty.hust.edu.cn")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("standalone_crawler.config_loader")

# Directory containing per-school JSON config files.
_CONFIG_DIR: Path = Path(__file__).resolve().parent.parent / "config" / "schools"

# Mapping from domain keyword to config filename stem.
_DOMAIN_MAP: dict[str, str] = {
    "hust": "hust_faculty",
    "faculty.hust.edu.cn": "hust_faculty",
}


def load_school_config(domain: str) -> dict[str, Any]:
    """Load crawler configuration for a given school domain.

    Searches for a matching JSON file in ``sandbox/config/schools/``.
    Falls back to built-in defaults when no config file is found.

    Args:
        domain: A domain string extracted from a seed URL (e.g.
            ``"faculty.hust.edu.cn"``).

    Returns:
        A configuration dict with keys matching the crawler config schema.
    """
    # Try exact match first, then keyword lookup.
    stem: str | None = _DOMAIN_MAP.get(domain)
    if stem is None:
        for key, val in _DOMAIN_MAP.items():
            if key in domain:
                stem = val
                break

    config_path = _CONFIG_DIR / f"{stem}.json" if stem else None

    if config_path is None or not config_path.is_file():
        logger.info("No school config found for domain '%s' — using defaults.", domain)
        return _default_config()

    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            cfg: dict[str, Any] = json.load(fh)
        logger.info("Loaded school config for domain '%s' from %s", domain, config_path)
        return cfg
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to parse config %s: %s — using defaults.", config_path, exc)
        return _default_config()


def _default_config() -> dict[str, Any]:
    """Return sensible built-in defaults."""
    return {
        "allowed_domains": [],
        "white_list_patterns": [".*"],
        "need_render": False,
        "request_delay": 1.0,
        "concurrency": 5,
        "max_depth": 2,
        "timeout": 30,
        "max_retries": 2,
        "use_render": False,
        "render_for_depth": [],
        "render_wait_time": 2,
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    cfg1 = load_school_config("faculty.hust.edu.cn")
    print("HUST config:", json.dumps(cfg1, indent=2, ensure_ascii=False))
    assert cfg1.get("concurrency") == 2

    cfg2 = load_school_config("unknown.example.com")
    print("Unknown domain config:", json.dumps(cfg2, indent=2, ensure_ascii=False))
    assert cfg2.get("concurrency") == 5

    print("config_loader.py — all assertions passed.")
