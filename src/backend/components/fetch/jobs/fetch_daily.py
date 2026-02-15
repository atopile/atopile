from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from ..config import FetchConfig
from ..models import FetchArtifactRecord
from .fetch_once import run_fetch_once, run_lcsc_asset_roundtrip_once


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class DailyFetchResult:
    jlc_snapshot_dir: Path
    roundtrip_report_path: Path | None


def _parse_roundtrip_lcsc_ids(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    out: list[int] = []
    for raw in value.split(","):
        stripped = raw.strip()
        if not stripped:
            continue
        out.append(int(stripped.removeprefix("C")))
    return tuple(out)


def run_fetch_daily(
    config: FetchConfig,
    *,
    max_pages: int | None = None,
    fetch_details: bool = True,
    max_details: int | None = 500,
    roundtrip_lcsc_ids: tuple[int, ...] = (),
    run_fetch_once_fn: Callable[..., Path] = run_fetch_once,
    run_roundtrip_fn: Callable[
        ..., list[FetchArtifactRecord]
    ] = run_lcsc_asset_roundtrip_once,
    roundtrip_run_root: Path | None = None,
) -> DailyFetchResult:
    jlc_snapshot_dir = run_fetch_once_fn(
        config,
        max_pages=max_pages,
        fetch_details=fetch_details,
        max_details=max_details,
    )
    report_path: Path | None = None
    if roundtrip_lcsc_ids:
        base_root = roundtrip_run_root or (config.cache_dir / "fetch" / "daily")
        run_dir = base_root / _utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        records: list[FetchArtifactRecord] = []
        for lcsc_id in roundtrip_lcsc_ids:
            records.extend(
                run_roundtrip_fn(
                    config=config,
                    lcsc_id=lcsc_id,
                )
            )
        summary = {
            "created_at_utc": _utc_stamp(),
            "record_count": len(records),
            "lcsc_ids": sorted({record.lcsc_id for record in records}),
            "artifact_types": sorted(
                {record.artifact_type.value for record in records}
            ),
        }
        report_path = run_dir / "roundtrip_report.json"
        report_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2))
    return DailyFetchResult(
        jlc_snapshot_dir=jlc_snapshot_dir,
        roundtrip_report_path=report_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run daily Stage 1 fetch jobs.")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--no-fetch-details", action="store_true")
    parser.add_argument("--max-details", type=int, default=500)
    parser.add_argument(
        "--roundtrip-lcsc-ids",
        type=str,
        default=os.getenv("ATOPILE_COMPONENTS_ROUNDTRIP_LCSC_IDS", ""),
        help=(
            "Comma-separated numeric IDs or C-prefixed IDs for asset roundtrip checks."
        ),
    )
    args = parser.parse_args(argv)

    config = FetchConfig.from_env()
    result = run_fetch_daily(
        config,
        max_pages=args.max_pages,
        fetch_details=not args.no_fetch_details,
        max_details=args.max_details,
        roundtrip_lcsc_ids=_parse_roundtrip_lcsc_ids(args.roundtrip_lcsc_ids),
    )
    print(result.jlc_snapshot_dir)
    if result.roundtrip_report_path is not None:
        print(result.roundtrip_report_path)
    return 0


def test_parse_roundtrip_lcsc_ids() -> None:
    assert _parse_roundtrip_lcsc_ids(None) == ()
    assert _parse_roundtrip_lcsc_ids("C21190, 2289") == (21190, 2289)


def test_run_fetch_daily_without_roundtrip(tmp_path) -> None:
    snapshot_dir = tmp_path / "fetch" / "jlc_api" / "snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    def fake_run_fetch_once(*args, **kwargs) -> Path:
        del args, kwargs
        return snapshot_dir

    config = FetchConfig.from_env()
    result = run_fetch_daily(
        config,
        max_pages=1,
        fetch_details=False,
        max_details=0,
        roundtrip_lcsc_ids=(),
        run_fetch_once_fn=fake_run_fetch_once,
    )
    assert result.jlc_snapshot_dir == snapshot_dir
    assert result.roundtrip_report_path is None


def test_run_fetch_daily_with_roundtrip(tmp_path) -> None:
    snapshot_dir = tmp_path / "fetch" / "jlc_api" / "snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    def fake_run_fetch_once(*args, **kwargs) -> Path:
        del args, kwargs
        return snapshot_dir

    def _real_roundtrip(*args, **kwargs) -> list[FetchArtifactRecord]:
        del args, kwargs
        from ..models import ArtifactType

        return [
            FetchArtifactRecord.now(
                lcsc_id=2040,
                artifact_type=ArtifactType.KICAD_FOOTPRINT_MOD,
                source_url="https://example.com",
                raw_sha256="abc",
                raw_size_bytes=3,
                stored_key="objects/kicad_footprint_mod/abc.zst",
            )
        ]

    config = FetchConfig.from_env()
    result = run_fetch_daily(
        config,
        max_pages=1,
        fetch_details=False,
        max_details=0,
        roundtrip_lcsc_ids=(2040,),
        run_fetch_once_fn=fake_run_fetch_once,
        run_roundtrip_fn=_real_roundtrip,
        roundtrip_run_root=tmp_path / "daily",
    )
    assert result.jlc_snapshot_dir == snapshot_dir
    assert result.roundtrip_report_path is not None
    assert result.roundtrip_report_path.exists()


if __name__ == "__main__":
    raise SystemExit(main())
