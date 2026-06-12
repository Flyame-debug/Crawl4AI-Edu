"""Build a metadata.json index from crawled data and the mapping file.

Reads the URL→file mapping from ``sandbox/data/mapping.txt`` (produced by the
crawler during local-mode operation) and generates ``sandbox/data/metadata.json``
in the format required by downstream consumers (members B and D).

Usage::

    conda activate crawlai-edu
    python sandbox/scripts/build_metadata.py [--mapping sandbox/data/mapping.txt]
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("build_metadata")

DEFAULT_MAPPING: str = "sandbox/data/mapping.txt"
DEFAULT_OUTPUT: str = "sandbox/data/metadata.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_mapping_line(line: str) -> tuple[str, dict[str, Any]] | None:
    """Parse a single mapping line into (url, entry) tuple.

    Format: ``url|html_path|img1,img2,...``
    """
    parts = line.strip().split("|")
    if len(parts) < 2:
        return None

    url = parts[0]
    html_path = parts[1]
    images: list[str] = []
    if len(parts) > 2 and parts[2]:
        images = [img for img in parts[2].split(",") if img]

    # Determine depth from URL (0 = teacher homepage, 1+ = sub-page).
    # Depth 0 URLs match pattern: /{username}/zh_CN/index.htm or /{username}/en/index.htm
    depth = 0 if "/index.htm" in url and url.count("/") <= 7 else 1

    return url, {
        "html": html_path,
        "images": images,
        "depth": depth,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_metadata(mapping_path: str = DEFAULT_MAPPING, output_path: str = DEFAULT_OUTPUT) -> int:
    """Read the mapping file and produce metadata.json.

    Returns:
        Number of entries written to the output file.
    """
    mp = Path(mapping_path)
    if not mp.is_file():
        logger.error("Mapping file not found: %s", mapping_path)
        return 0

    metadata: dict[str, dict[str, Any]] = {}
    errors: int = 0

    with open(mp, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            parsed = _parse_mapping_line(line)
            if parsed is None:
                errors += 1
                logger.warning("Line %d: could not parse: %s", line_num, line.strip()[:100])
                continue
            url, entry = parsed
            metadata[url] = entry

    # Write output.
    op = Path(output_path)
    op.parent.mkdir(parents=True, exist_ok=True)
    with open(op, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    entries_with_images = sum(1 for e in metadata.values() if e["images"])
    logger.info(
        "metadata.json written: %d entries (%d with images), %d parse errors",
        len(metadata), entries_with_images, errors,
    )
    return len(metadata)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    mp_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MAPPING
    count = build_metadata(mp_arg)
    print(f"build_metadata.py — wrote {count} entries.")
