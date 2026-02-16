from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..config import FetchConfig


@dataclass(frozen=True)
class MaterializeResult:
    component_count: int
    artifact_count: int
    output_root: Path


def _link_or_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        dst.hardlink_to(src)
    except OSError:
        shutil.copy2(src, dst)


def materialize_component_store(
    *,
    cache_dir: Path,
    output_root: Path | None = None,
) -> MaterializeResult:
    manifest_db = cache_dir / "fetch" / "manifest.sqlite3"
    if not manifest_db.exists():
        raise FileNotFoundError(f"Manifest DB not found: {manifest_db}")

    out_root = output_root or (cache_dir / "components")
    out_root.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(manifest_db) as conn:
        rows = conn.execute(
            """
            select
                lcsc_id,
                artifact_type,
                stored_key,
                mime,
                raw_sha256,
                raw_size_bytes,
                source_url,
                source_meta_json,
                fetched_at_utc,
                encoding
            from fetch_manifest
            where compare_ok = 1
            order by lcsc_id asc, id asc
            """
        ).fetchall()

    artifacts_by_part: dict[int, list[dict[str, object]]] = defaultdict(list)
    artifact_count = 0
    for row in rows:
        lcsc_id = int(row[0])
        stored_key = str(row[2])
        src_blob = cache_dir / stored_key
        if not src_blob.exists():
            continue

        component_dir = out_root / f"C{lcsc_id}"
        blob_dir = component_dir / "blobs"
        dst_blob = blob_dir / src_blob.name
        _link_or_copy(src_blob, dst_blob)

        artifacts_by_part[lcsc_id].append(
            {
                "artifact_type": str(row[1]),
                "blob_relpath": str(Path("blobs") / src_blob.name),
                "mime": None if row[3] is None else str(row[3]),
                "raw_sha256": str(row[4]),
                "raw_size_bytes": int(row[5]),
                "source_url": str(row[6]),
                "source_meta": json.loads(str(row[7])),
                "fetched_at_utc": str(row[8]),
                "encoding": str(row[9]),
                "stored_key": stored_key,
            }
        )
        artifact_count += 1

    for lcsc_id, artifacts in artifacts_by_part.items():
        component_dir = out_root / f"C{lcsc_id}"
        manifest_path = component_dir / "manifest.json"
        payload = {
            "lcsc_id": lcsc_id,
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
        }
        manifest_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    return MaterializeResult(
        component_count=len(artifacts_by_part),
        artifact_count=artifact_count,
        output_root=out_root,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Materialize per-component compressed blob folders from fetch manifest."
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache dir root (defaults to ATOPILE_COMPONENTS_CACHE_DIR).",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Output root for component folders (default: <cache-dir>/components).",
    )
    args = parser.parse_args(argv)

    cfg = FetchConfig.from_env()
    cache_dir = args.cache_dir or cfg.cache_dir
    result = materialize_component_store(
        cache_dir=cache_dir,
        output_root=args.output_root,
    )
    print(result.output_root)
    print(f"components={result.component_count}")
    print(f"artifacts={result.artifact_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def test_materialize_component_store(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    (cache_dir / "objects" / "model_step").mkdir(parents=True, exist_ok=True)
    blob_path = cache_dir / "objects" / "model_step" / "abc.zst"
    blob_path.write_bytes(b"zstd-bytes")

    manifest_db = cache_dir / "fetch" / "manifest.sqlite3"
    manifest_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(manifest_db) as conn:
        conn.execute(
            """
            create table fetch_manifest (
                id integer primary key autoincrement,
                lcsc_id integer not null,
                artifact_type text not null,
                source_url text not null,
                raw_sha256 text not null,
                raw_size_bytes integer not null,
                mime text,
                encoding text not null,
                stored_key text not null,
                fetched_at_utc text not null,
                source_meta_json text not null,
                compare_ok integer not null
            )
            """
        )
        conn.execute(
            """
            insert into fetch_manifest (
                lcsc_id,
                artifact_type,
                source_url,
                raw_sha256,
                raw_size_bytes,
                mime,
                encoding,
                stored_key,
                fetched_at_utc,
                source_meta_json,
                compare_ok
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                21190,
                "model_step",
                "https://example.com/step",
                "abc",
                10,
                "model/step",
                "zstd",
                "objects/model_step/abc.zst",
                "2026-01-01T00:00:00+00:00",
                "{}",
                1,
            ),
        )

    result = materialize_component_store(cache_dir=cache_dir)
    assert result.component_count == 1
    assert result.artifact_count == 1
    assert (result.output_root / "C21190" / "blobs" / "abc.zst").exists()
    manifest_payload = json.loads(
        (result.output_root / "C21190" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest_payload["artifact_count"] == 1
