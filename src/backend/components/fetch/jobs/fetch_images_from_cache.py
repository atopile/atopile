from __future__ import annotations

import argparse
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ..config import FetchConfig
from ..models import ArtifactType, FetchArtifactRecord
from ..storage.manifest_store import LocalManifestStore
from ..storage.object_store import LocalObjectStore


@dataclass(frozen=True)
class ImageSeed:
    lcsc_id: int
    image_url: str
    source_meta: dict[str, Any]


def _choose_image_url(extra_json: str | None) -> tuple[str | None, dict[str, Any]]:
    if not extra_json:
        return None, {}
    try:
        payload = json.loads(extra_json)
    except Exception:
        return None, {}
    images = payload.get("images")
    if not isinstance(images, list) or not images:
        return None, {}
    first = images[0]
    if isinstance(first, str) and first.startswith("http"):
        return first, {"image_variant": "raw"}
    if not isinstance(first, dict):
        return None, {}

    candidates: list[tuple[int, str, str]] = []
    for key, value in first.items():
        if not isinstance(value, str) or not value.startswith("http"):
            continue
        area = 0
        key_str = str(key)
        if "x" in key_str:
            try:
                w, h = key_str.lower().split("x", 1)
                area = int(w) * int(h)
            except Exception:
                area = 0
        candidates.append((area, key_str, value))
    if not candidates:
        return None, {}
    candidates.sort(reverse=True)
    _, variant, url = candidates[0]
    return url, {"image_variant": variant}


def _iter_seeds(source_sqlite: Path, where: str) -> list[ImageSeed]:
    query = f"select lcsc, extra from components where {where} order by lcsc"
    out: list[ImageSeed] = []
    with sqlite3.connect(source_sqlite) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        for lcsc_id, extra_json in cursor:
            image_url, meta = _choose_image_url(extra_json)
            if not image_url:
                continue
            out.append(
                ImageSeed(
                    lcsc_id=int(lcsc_id),
                    image_url=image_url,
                    source_meta=meta,
                )
            )
    return out


def _existing_part_image_ids(manifest_db: Path) -> set[int]:
    if not manifest_db.exists():
        return set()
    with sqlite3.connect(manifest_db) as conn:
        rows = conn.execute(
            "select distinct lcsc_id from fetch_manifest where artifact_type = 'part_image'"
        ).fetchall()
    return {int(row[0]) for row in rows}


def _fetch_image(client: httpx.Client, url: str, timeout_s: float) -> tuple[bytes, str]:
    response = client.get(url, timeout=timeout_s)
    response.raise_for_status()
    content_type = str(response.headers.get("content-type", ""))
    mime = content_type.split(";", 1)[0].strip().lower()
    if not mime.startswith("image/"):
        raise RuntimeError(f"unexpected image content-type: {content_type}")
    return response.content, mime


def run_fetch_images(
    *,
    source_sqlite: Path,
    cache_dir: Path,
    where: str,
    workers: int,
    timeout_s: float,
    retries: int,
    retry_backoff_s: float,
) -> dict[str, Any]:
    seeds = _iter_seeds(source_sqlite, where)
    manifest_db = cache_dir / "fetch" / "manifest.sqlite3"
    existing = _existing_part_image_ids(manifest_db)
    pending = [seed for seed in seeds if seed.lcsc_id not in existing]

    object_store = LocalObjectStore(cache_dir)
    manifest_store = LocalManifestStore(cache_dir)
    success = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    def one(seed: ImageSeed) -> tuple[bool, str | None]:
        with httpx.Client(follow_redirects=True) as client:
            for attempt in range(retries + 1):
                try:
                    payload, mime = _fetch_image(client, seed.image_url, timeout_s)
                    blob = object_store.put_raw(ArtifactType.PART_IMAGE, payload)
                    manifest_store.append(
                        FetchArtifactRecord.now(
                            lcsc_id=seed.lcsc_id,
                            artifact_type=ArtifactType.PART_IMAGE,
                            source_url=seed.image_url,
                            raw_sha256=blob.raw_sha256,
                            raw_size_bytes=blob.raw_size_bytes,
                            stored_key=blob.key,
                            source_meta={
                                **seed.source_meta,
                                "attempt": attempt + 1,
                            },
                            mime=mime,
                        )
                    )
                    return True, None
                except Exception as exc:
                    if attempt >= retries:
                        return False, f"{type(exc).__name__}: {exc}"
                    time.sleep(retry_backoff_s * (attempt + 1))
        return False, "unexpected"

    max_workers = max(1, min(workers, len(pending) or 1))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(one, seed): seed for seed in pending}
        for future in as_completed(futures):
            seed = futures[future]
            ok, err = future.result()
            if ok:
                success += 1
            else:
                failed += 1
                errors.append({"lcsc_id": seed.lcsc_id, "error": err})

    return {
        "seed_count": len(seeds),
        "pending_count": len(pending),
        "success": success,
        "failed": failed,
        "errors": errors[:50],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage-1 helper: scrape/store part images from cache.sqlite components.extra."
    )
    parser.add_argument(
        "--source-sqlite",
        type=Path,
        default=Path("/home/jlc/cache.sqlite3"),
        help="Source cache.sqlite path.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache root; defaults to ATOPILE_COMPONENTS_CACHE_DIR.",
    )
    parser.add_argument(
        "--where",
        type=str,
        default="stock > 0",
        help="Source filter SQL clause.",
    )
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--timeout-s", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-backoff-s", type=float, default=1.0)
    args = parser.parse_args(argv)

    cfg = FetchConfig.from_env()
    cache_dir = args.cache_dir or cfg.cache_dir
    result = run_fetch_images(
        source_sqlite=args.source_sqlite,
        cache_dir=cache_dir,
        where=args.where,
        workers=args.workers,
        timeout_s=args.timeout_s,
        retries=args.retries,
        retry_backoff_s=args.retry_backoff_s,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


def test_choose_image_url_prefers_largest_variant() -> None:
    url, meta = _choose_image_url(
        json.dumps(
            {
                "images": [
                    {
                        "96x96": "https://example.com/a-96.jpg",
                        "224x224": "https://example.com/a-224.jpg",
                    }
                ]
            }
        )
    )
    assert url == "https://example.com/a-224.jpg"
    assert meta["image_variant"] == "224x224"


if __name__ == "__main__":
    raise SystemExit(main())
