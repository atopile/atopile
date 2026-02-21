from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_CACHE_DIR = Path("/var/cache/atopile/components")


def _snapshot_name() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


@dataclass(frozen=True)
class TransformConfig:
    source_sqlite_path: Path
    fetch_manifest_path: Path
    snapshot_root_dir: Path
    snapshot_name: str
    batch_size: int

    @property
    def snapshot_dir(self) -> Path:
        return self.snapshot_root_dir / self.snapshot_name

    @property
    def fast_db_path(self) -> Path:
        return self.snapshot_dir / "fast.sqlite"

    @property
    def detail_db_path(self) -> Path:
        return self.snapshot_dir / "detail.sqlite"

    @classmethod
    def from_env(cls) -> TransformConfig:
        cache_root = Path(
            os.getenv("ATOPILE_COMPONENTS_CACHE_DIR", str(DEFAULT_CACHE_DIR))
        )
        default_source = cache_root / "raw" / "cache.sqlite3"
        default_manifest = cache_root / "fetch" / "manifest.sqlite3"
        source_sqlite_path = Path(
            os.getenv("ATOPILE_COMPONENTS_SOURCE_SQLITE", str(default_source))
        )
        snapshot_root = cache_root / "snapshots"
        return cls(
            source_sqlite_path=source_sqlite_path,
            fetch_manifest_path=Path(
                os.getenv("ATOPILE_COMPONENTS_FETCH_MANIFEST", str(default_manifest))
            ),
            snapshot_root_dir=Path(
                os.getenv("ATOPILE_COMPONENTS_SNAPSHOT_ROOT", str(snapshot_root))
            ),
            snapshot_name=os.getenv(
                "ATOPILE_COMPONENTS_SNAPSHOT_NAME",
                _snapshot_name(),
            ),
            batch_size=int(
                os.getenv("ATOPILE_COMPONENTS_TRANSFORM_BATCH_SIZE", "5000")
            ),
        )


def test_transform_config_defaults(monkeypatch) -> None:
    for key in (
        "ATOPILE_COMPONENTS_CACHE_DIR",
        "ATOPILE_COMPONENTS_SOURCE_SQLITE",
        "ATOPILE_COMPONENTS_FETCH_MANIFEST",
        "ATOPILE_COMPONENTS_SNAPSHOT_ROOT",
        "ATOPILE_COMPONENTS_SNAPSHOT_NAME",
        "ATOPILE_COMPONENTS_TRANSFORM_BATCH_SIZE",
    ):
        monkeypatch.delenv(key, raising=False)

    config = TransformConfig.from_env()
    assert config.source_sqlite_path == DEFAULT_CACHE_DIR / "raw" / "cache.sqlite3"
    expected_manifest = DEFAULT_CACHE_DIR / "fetch" / "manifest.sqlite3"
    assert config.fetch_manifest_path == expected_manifest
    assert config.snapshot_root_dir == DEFAULT_CACHE_DIR / "snapshots"
    assert config.batch_size == 5000
    assert config.snapshot_name


def test_transform_config_from_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ATOPILE_COMPONENTS_SOURCE_SQLITE", str(tmp_path / "in.sqlite3"))
    monkeypatch.setenv(
        "ATOPILE_COMPONENTS_FETCH_MANIFEST", str(tmp_path / "fetch-manifest.sqlite3")
    )
    monkeypatch.setenv("ATOPILE_COMPONENTS_SNAPSHOT_ROOT", str(tmp_path / "snapshots"))
    monkeypatch.setenv("ATOPILE_COMPONENTS_SNAPSHOT_NAME", "test-snapshot")
    monkeypatch.setenv("ATOPILE_COMPONENTS_TRANSFORM_BATCH_SIZE", "123")

    config = TransformConfig.from_env()
    assert config.source_sqlite_path == tmp_path / "in.sqlite3"
    assert config.fetch_manifest_path == tmp_path / "fetch-manifest.sqlite3"
    assert config.snapshot_root_dir == tmp_path / "snapshots"
    assert config.snapshot_name == "test-snapshot"
    assert config.batch_size == 123
    assert (
        config.fast_db_path == tmp_path / "snapshots" / "test-snapshot" / "fast.sqlite"
    )
