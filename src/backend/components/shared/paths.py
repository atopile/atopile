from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ComponentsPaths:
    cache_dir: Path

    @property
    def fetch_dir(self) -> Path:
        return self.cache_dir / "fetch"

    @property
    def objects_dir(self) -> Path:
        return self.cache_dir / "objects"

    @property
    def manifest_db_path(self) -> Path:
        return self.fetch_dir / "manifest.sqlite3"

    @property
    def snapshots_dir(self) -> Path:
        return self.cache_dir / "snapshots"

    @property
    def current_symlink(self) -> Path:
        return self.cache_dir / "current"

    @property
    def previous_symlink(self) -> Path:
        return self.cache_dir / "previous"

    def ensure_dirs(self) -> None:
        self.fetch_dir.mkdir(parents=True, exist_ok=True)
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)


def test_components_paths_layout(tmp_path) -> None:
    paths = ComponentsPaths(tmp_path)
    paths.ensure_dirs()
    assert paths.fetch_dir.exists()
    assert paths.objects_dir.exists()
    assert paths.snapshots_dir.exists()
    assert paths.manifest_db_path.parent == paths.fetch_dir
