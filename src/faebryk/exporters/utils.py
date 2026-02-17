# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Shared utilities for JSON visualization exporters (pinout, power tree, schematic, etc.).
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def strip_root_hex(name: str) -> str:
    """Strip leading hex node ID prefix like '0xF8C9.' from names."""
    stripped = re.sub(r"^0x[0-9A-Fa-f]+\.", "", name)
    return stripped if stripped else name


def natural_sort_key(s: str) -> list:
    """Sort key that handles mixed alpha-numeric strings naturally.

    Example: ["IO2", "IO10", "IO1"] -> sorted as ["IO1", "IO2", "IO10"]
    """
    parts = re.split(r"(\d+)", s)
    result: list = []
    for part in parts:
        if part.isdigit():
            result.append(int(part))
        else:
            result.append(part.lower())
    return result


def write_json(data: dict, path: Path) -> None:
    """Write JSON atomically via temp file.

    Creates parent directories if needed. Uses a .tmp suffix during writing
    and atomically renames on success to avoid partial writes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
