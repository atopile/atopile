from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..fetch.config import FetchConfig
from ..fetch.models import ArtifactType, FetchArtifactRecord
from ..fetch.storage.manifest_store import LocalManifestStore
from ..fetch.storage.object_store import LocalObjectStore


@dataclass(frozen=True)
class StepAsset:
    lcsc_id: int
    stored_key: str
    source_url: str
    raw_sha256: str
    source_meta: dict[str, Any]


def _load_step_assets(
    manifest_db: Path, *, limit: int | None = None, only_missing_glb: bool = True
) -> list[StepAsset]:
    sql = """
        select
          s.lcsc_id,
          s.stored_key,
          s.source_url,
          s.raw_sha256,
          s.source_meta_json
        from fetch_manifest s
        where s.artifact_type = 'model_step'
    """
    if only_missing_glb:
        sql += """
          and not exists (
            select 1
            from fetch_manifest g
            where g.lcsc_id = s.lcsc_id
              and g.artifact_type = 'model_glb'
          )
        """
    sql += " order by s.id asc"
    if limit is not None and limit > 0:
        sql += f" limit {int(limit)}"

    out: list[StepAsset] = []
    with sqlite3.connect(manifest_db) as conn:
        rows = conn.execute(sql).fetchall()
    for row in rows:
        source_meta_raw = row[4]
        if isinstance(source_meta_raw, str) and source_meta_raw:
            try:
                source_meta = json.loads(source_meta_raw)
            except Exception:
                source_meta = {}
        else:
            source_meta = {}
        out.append(
            StepAsset(
                lcsc_id=int(row[0]),
                stored_key=str(row[1]),
                source_url=str(row[2]),
                raw_sha256=str(row[3]),
                source_meta=source_meta if isinstance(source_meta, dict) else {},
            )
        )
    return out


def _default_step_to_glb(step_bytes: bytes) -> bytes:
    import cadquery as cq

    with tempfile.TemporaryDirectory(prefix="step2glb-") as td:
        td_path = Path(td)
        step_path = td_path / "in.step"
        glb_path = td_path / "out.glb"
        step_path.write_bytes(step_bytes)
        assy = cq.importers.importStep(str(step_path))
        assy.export(str(glb_path), exportType="GLTF")
        return glb_path.read_bytes()


def _optimize_glb(gltf_cmd: str, glb_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory(prefix="gltf-opt-") as td:
        td_path = Path(td)
        in_path = td_path / "in.glb"
        out_path = td_path / "out.glb"
        in_path.write_bytes(glb_bytes)
        subprocess.run(
            [gltf_cmd, "optimize", str(in_path), str(out_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return out_path.read_bytes()


def convert_step_assets_to_glb(
    *,
    cache_dir: Path,
    assets: list[StepAsset],
    workers: int = 4,
    optimize: bool = False,
    gltf_cmd: str = "gltf-transform",
    step_to_glb_fn: Callable[[bytes], bytes] = _default_step_to_glb,
) -> dict[str, Any]:
    object_store = LocalObjectStore(cache_dir)
    manifest_store = LocalManifestStore(cache_dir)

    success = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    def one(asset: StepAsset) -> tuple[bool, str | None]:
        try:
            step_raw = object_store.get_raw(asset.stored_key)
            glb_raw = step_to_glb_fn(step_raw)
            if optimize:
                glb_raw = _optimize_glb(gltf_cmd, glb_raw)
            glb_blob = object_store.put_raw(ArtifactType.MODEL_GLB, glb_raw)
            manifest_store.append(
                FetchArtifactRecord.now(
                    lcsc_id=asset.lcsc_id,
                    artifact_type=ArtifactType.MODEL_GLB,
                    source_url=asset.source_url,
                    raw_sha256=glb_blob.raw_sha256,
                    raw_size_bytes=glb_blob.raw_size_bytes,
                    stored_key=glb_blob.key,
                    source_meta={
                        "generated_from": "model_step",
                        "model_step_stored_key": asset.stored_key,
                        "model_step_sha256": asset.raw_sha256,
                        "optimize": optimize,
                    },
                    mime="model/gltf-binary",
                )
            )
            return True, None
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    max_workers = max(1, min(workers, len(assets) or 1))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(one, asset): asset for asset in assets}
        for future in as_completed(futures):
            asset = futures[future]
            ok, err = future.result()
            if ok:
                success += 1
            else:
                failed += 1
                errors.append({"lcsc_id": asset.lcsc_id, "error": err})

    return {
        "selected": len(assets),
        "success": success,
        "failed": failed,
        "errors": errors[:50],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage-2 transform: convert stored STEP artifacts to GLB artifacts."
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache root; defaults to ATOPILE_COMPONENTS_CACHE_DIR.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max STEP assets to convert.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel conversion workers.",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Run gltf-transform optimize after conversion.",
    )
    parser.add_argument(
        "--gltf-cmd",
        type=str,
        default="gltf-transform",
        help="Command name/path for gltf-transform.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Convert even if model_glb already exists for the part.",
    )
    args = parser.parse_args(argv)

    cfg = FetchConfig.from_env()
    cache_dir = args.cache_dir or cfg.cache_dir
    manifest_db = cache_dir / "fetch" / "manifest.sqlite3"
    assets = _load_step_assets(
        manifest_db,
        limit=(args.limit if args.limit > 0 else None),
        only_missing_glb=(not args.all),
    )
    result = convert_step_assets_to_glb(
        cache_dir=cache_dir,
        assets=assets,
        workers=args.workers,
        optimize=args.optimize,
        gltf_cmd=args.gltf_cmd,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


def test_load_step_assets_skips_glb_when_requested(tmp_path) -> None:
    db = tmp_path / "manifest.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("""
            create table fetch_manifest (
              id integer primary key autoincrement,
              lcsc_id integer not null,
              artifact_type text not null,
              source_url text not null,
              raw_sha256 text not null,
              stored_key text not null,
              source_meta_json text not null
            )
        """)
        conn.execute(
            """
            insert into fetch_manifest
            (lcsc_id, artifact_type, source_url, raw_sha256, stored_key, source_meta_json)
            values
              (1, 'model_step', 'u', 's1', 'objects/model_step/s1.zst', '{}'),
              (1, 'model_glb', 'u', 'g1', 'objects/model_glb/g1.zst', '{}'),
              (2, 'model_step', 'u', 's2', 'objects/model_step/s2.zst', '{}')
            """
        )
    rows = _load_step_assets(db, only_missing_glb=True)
    assert [row.lcsc_id for row in rows] == [2]


if __name__ == "__main__":
    raise SystemExit(main())
