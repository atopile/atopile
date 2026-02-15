"""
Legacy adapter point for prebuilt jlcparts/cache.sqlite3 style inputs.

Stage 1 now treats authenticated JLC API ingest as canonical.
This module remains only as a compatibility hook for local bootstrapping.
"""

from __future__ import annotations

from pathlib import Path


def legacy_cache_sqlite_path(cache_root: Path) -> Path:
    """Return the conventional path for a local legacy cache.sqlite3 fixture."""
    return cache_root / "legacy" / "cache.sqlite3"
