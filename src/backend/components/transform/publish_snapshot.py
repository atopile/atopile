from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .config import TransformConfig
from .validate_snapshot import (
    _write_valid_detail_db,
    _write_valid_fast_db,
    validate_snapshot,
)


def publish_snapshot(
    snapshot_dir: Path,
    *,
    snapshot_root: Path,
    keep_snapshots: int = 2,
    allow_partial: bool = False,
) -> Path:
    if not snapshot_dir.exists():
        raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")
    _assert_snapshot_publishable(snapshot_dir, allow_partial=allow_partial)
    validate_snapshot(snapshot_dir)

    current_link = snapshot_root / "current"
    previous_link = snapshot_root / "previous"

    prior_target: Path | None = None
    if current_link.exists() or current_link.is_symlink():
        resolved = current_link.resolve(strict=False)
        if resolved != snapshot_dir:
            prior_target = resolved

    temp_link = snapshot_root / f".current.tmp.{snapshot_dir.name}"
    if temp_link.exists() or temp_link.is_symlink():
        temp_link.unlink()
    temp_link.symlink_to(snapshot_dir, target_is_directory=True)
    temp_link.replace(current_link)

    if prior_target is not None and prior_target.exists():
        if previous_link.exists() or previous_link.is_symlink():
            previous_link.unlink()
        previous_link.symlink_to(prior_target, target_is_directory=True)

    prune_old_snapshots(snapshot_root=snapshot_root, keep=keep_snapshots)

    return current_link


def prune_old_snapshots(*, snapshot_root: Path, keep: int) -> None:
    if keep < 1:
        raise ValueError("keep must be >= 1")
    current_link = snapshot_root / "current"
    previous_link = snapshot_root / "previous"
    protected_targets = {
        link.resolve(strict=False)
        for link in (current_link, previous_link)
        if link.exists() or link.is_symlink()
    }

    snapshot_dirs = [
        path
        for path in snapshot_root.iterdir()
        if path.is_dir() and path.name not in {"current", "previous"}
    ]
    snapshot_dirs.sort(
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    kept = 0
    for directory in snapshot_dirs:
        if directory.resolve() in protected_targets:
            continue
        kept += 1
        if kept <= keep:
            continue
        shutil.rmtree(directory, ignore_errors=True)


def _assert_snapshot_publishable(snapshot_dir: Path, *, allow_partial: bool) -> None:
    metadata_path = snapshot_dir / "metadata.json"
    if not metadata_path.exists():
        return

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid metadata.json in snapshot: {snapshot_dir}"
        ) from exc

    if metadata.get("is_partial") and not allow_partial:
        raise RuntimeError(
            "Refusing to publish partial snapshot "
            f"{snapshot_dir}. Re-run publish with --allow-partial if intentional."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Atomically promote a built snapshot to snapshots/current."
    )
    parser.add_argument(
        "snapshot_name",
        type=str,
        help="Snapshot name under snapshot root to publish.",
    )
    parser.add_argument(
        "--keep-snapshots",
        type=int,
        default=2,
        help="Number of non-protected old snapshots to retain after publish.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow publishing snapshots built with --max-components.",
    )
    args = parser.parse_args(argv)

    config = TransformConfig.from_env()
    snapshot_dir = config.snapshot_root_dir / args.snapshot_name
    current = publish_snapshot(
        snapshot_dir,
        snapshot_root=config.snapshot_root_dir,
        keep_snapshots=args.keep_snapshots,
        allow_partial=args.allow_partial,
    )
    print(current)
    return 0


def test_publish_snapshot(tmp_path) -> None:
    root = tmp_path / "snapshots"
    snap_a = root / "snap-a"
    snap_b = root / "snap-b"
    _write_valid_snapshot(snap_a)
    _write_valid_snapshot(snap_b)

    current = publish_snapshot(snap_a, snapshot_root=root)
    assert current.is_symlink()
    assert current.resolve() == snap_a.resolve()

    current = publish_snapshot(snap_b, snapshot_root=root)
    assert current.resolve() == snap_b.resolve()
    previous = root / "previous"
    assert previous.is_symlink()
    assert previous.resolve() == snap_a.resolve()


def test_prune_old_snapshots(tmp_path) -> None:
    root = tmp_path / "snapshots"
    root.mkdir(parents=True)

    def mk_snapshot(name: str) -> Path:
        snap = root / name
        _write_valid_snapshot(snap)
        return snap

    mk_snapshot("a")
    snap_b = mk_snapshot("b")
    snap_c = mk_snapshot("c")

    publish_snapshot(snap_c, snapshot_root=root, keep_snapshots=1)
    publish_snapshot(snap_b, snapshot_root=root, keep_snapshots=1)
    assert (root / "a").exists() is False
    assert (root / "b").exists()
    assert (root / "c").exists()
    assert (root / "current").resolve() == snap_b.resolve()


def test_publish_rejects_partial_snapshot_by_default(tmp_path) -> None:
    root = tmp_path / "snapshots"
    snapshot = root / "partial"
    _write_valid_snapshot(snapshot, partial=True)
    try:
        publish_snapshot(snapshot, snapshot_root=root)
    except RuntimeError as exc:
        assert "Refusing to publish partial snapshot" in str(exc)
    else:
        assert False, "Expected RuntimeError for partial snapshot"


def test_publish_allows_partial_with_flag(tmp_path) -> None:
    root = tmp_path / "snapshots"
    snapshot = root / "partial"
    _write_valid_snapshot(snapshot, partial=True)
    current = publish_snapshot(snapshot, snapshot_root=root, allow_partial=True)
    assert current.is_symlink()
    assert current.resolve() == snapshot.resolve()


def _write_valid_snapshot(snapshot_dir: Path, *, partial: bool = False) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    fast_db = snapshot_dir / "fast.sqlite"
    detail_db = snapshot_dir / "detail.sqlite"

    _write_valid_fast_db(fast_db)
    _write_valid_detail_db(detail_db)
    metadata = {
        "snapshot_name": snapshot_dir.name,
        "is_partial": partial,
    }
    (snapshot_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
