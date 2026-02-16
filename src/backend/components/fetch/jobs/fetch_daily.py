from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any, Callable

import httpx

from ...shared.telemetry import log_event
from ..config import FetchConfig
from ..models import FetchArtifactRecord
from ..sources.lcsc import LcscFetchSeed
from .fetch_once import run_fetch_once, run_lcsc_asset_roundtrip_once


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class DailyFetchResult:
    jlc_snapshot_dir: Path
    roundtrip_report_path: Path | None


def _coerce_lcsc_id(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    normalized = stripped.removeprefix("C").removeprefix("c")
    if not normalized.isdigit():
        return None
    return int(normalized)


def _normalize_datasheet_url(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped.startswith("//"):
        return f"https:{stripped}"
    if stripped.startswith(("http://", "https://")):
        return stripped
    return None


def _extract_datasheet_url(detail: dict[str, Any]) -> str | None:
    direct_keys = (
        "datasheet",
        "datasheetUrl",
        "datasheetURL",
        "datasheet_url",
        "dataManualUrl",
    )
    for key in direct_keys:
        value = detail.get(key)
        if isinstance(value, str):
            normalized = _normalize_datasheet_url(value)
            if normalized:
                return normalized
    extra = detail.get("extra")
    if isinstance(extra, dict):
        for key in direct_keys:
            value = extra.get(key)
            if isinstance(value, str):
                normalized = _normalize_datasheet_url(value)
                if normalized:
                    return normalized
    return None


def _load_lcsc_seed_map_from_snapshot(snapshot_dir: Path) -> dict[int, LcscFetchSeed]:
    seed_map: dict[int, LcscFetchSeed] = {}
    detail_file = snapshot_dir / "component_details.ndjson"
    if detail_file.exists():
        for line in detail_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            detail = payload.get("detail")
            if not isinstance(detail, dict):
                continue
            lcsc_id = _coerce_lcsc_id(
                payload.get("lcscPart")
                or detail.get("lcscPart")
                or detail.get("componentCode")
            )
            if lcsc_id is None:
                continue
            seed_map[lcsc_id] = LcscFetchSeed(
                lcsc_id=lcsc_id,
                datasheet_url=_extract_datasheet_url(detail),
            )

    components_file = snapshot_dir / "components.ndjson"
    if components_file.exists():
        for line in components_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            lcsc_id = _coerce_lcsc_id(
                payload.get("lcscPart")
                or payload.get("componentCode")
                or payload.get("lcsc")
            )
            if lcsc_id is None:
                continue
            if lcsc_id not in seed_map:
                seed_map[lcsc_id] = LcscFetchSeed(lcsc_id=lcsc_id)
    return seed_map


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


def _is_retryable_roundtrip_error(ex: Exception) -> bool:
    if isinstance(ex, httpx.HTTPStatusError):
        status = ex.response.status_code
        return status == 429 or status >= 500
    return isinstance(
        ex,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
            httpx.TransportError,
        ),
    )


def _retry_delay_seconds(
    ex: Exception, *, attempt: int, default_backoff_s: float
) -> float:
    if isinstance(ex, httpx.HTTPStatusError):
        retry_after = ex.response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), default_backoff_s)
            except ValueError:
                pass
    return default_backoff_s * attempt


def run_fetch_daily(
    config: FetchConfig,
    *,
    max_pages: int | None = None,
    fetch_details: bool = True,
    max_details: int | None = None,
    roundtrip_lcsc_ids: tuple[int, ...] = (),
    run_fetch_once_fn: Callable[..., Path] = run_fetch_once,
    run_roundtrip_fn: Callable[
        ..., list[FetchArtifactRecord]
    ] = run_lcsc_asset_roundtrip_once,
    roundtrip_run_root: Path | None = None,
    roundtrip_from_snapshot: bool = False,
    roundtrip_max_parts: int | None = None,
    roundtrip_retry_attempts: int = 3,
    roundtrip_retry_backoff_s: float = 2.0,
    roundtrip_sleep_s: float = 0.0,
) -> DailyFetchResult:
    log_event(
        service="components-fetch",
        event="fetch.daily.start",
        max_pages=max_pages,
        fetch_details=fetch_details,
        max_details=max_details,
        roundtrip_lcsc_ids=list(roundtrip_lcsc_ids),
        roundtrip_from_snapshot=roundtrip_from_snapshot,
        roundtrip_max_parts=roundtrip_max_parts,
        roundtrip_retry_attempts=roundtrip_retry_attempts,
        roundtrip_retry_backoff_s=roundtrip_retry_backoff_s,
        roundtrip_sleep_s=roundtrip_sleep_s,
    )
    jlc_snapshot_dir = run_fetch_once_fn(
        config,
        max_pages=max_pages,
        fetch_details=fetch_details,
        max_details=max_details,
    )
    report_path: Path | None = None
    if roundtrip_lcsc_ids or roundtrip_from_snapshot:
        base_root = roundtrip_run_root or (config.cache_dir / "fetch" / "daily")
        run_dir = base_root / _utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        seed_map = _load_lcsc_seed_map_from_snapshot(jlc_snapshot_dir)
        if roundtrip_lcsc_ids:
            seeds = [
                seed_map.get(lcsc_id) or LcscFetchSeed(lcsc_id=lcsc_id)
                for lcsc_id in roundtrip_lcsc_ids
            ]
        else:
            seeds = list(seed_map.values())
        if roundtrip_max_parts is not None:
            seeds = seeds[:roundtrip_max_parts]

        records: list[FetchArtifactRecord] = []
        failures: list[dict[str, object]] = []
        for seed in seeds:
            if roundtrip_sleep_s > 0:
                sleep(roundtrip_sleep_s)
            attempt = 0
            while True:
                attempt += 1
                try:
                    records.extend(
                        run_roundtrip_fn(
                            config=config,
                            lcsc_id=seed.lcsc_id,
                            datasheet_url=seed.datasheet_url,
                        )
                    )
                    break
                except Exception as ex:
                    is_retryable = _is_retryable_roundtrip_error(ex)
                    if attempt >= roundtrip_retry_attempts or not is_retryable:
                        failures.append(
                            {
                                "lcsc_id": seed.lcsc_id,
                                "datasheet_url": seed.datasheet_url,
                                "attempts": attempt,
                                "retryable": is_retryable,
                                "error": repr(ex),
                            }
                        )
                        log_event(
                            service="components-fetch",
                            event="fetch.daily.roundtrip_part_failed",
                            lcsc_id=seed.lcsc_id,
                            datasheet_url=seed.datasheet_url,
                            attempts=attempt,
                            error=repr(ex),
                        )
                        break
                    delay_s = _retry_delay_seconds(
                        ex,
                        attempt=attempt,
                        default_backoff_s=roundtrip_retry_backoff_s,
                    )
                    sleep(delay_s)

        summary = {
            "created_at_utc": _utc_stamp(),
            "seed_count": len(seeds),
            "record_count": len(records),
            "lcsc_ids": sorted({record.lcsc_id for record in records}),
            "artifact_types": sorted(
                {record.artifact_type.value for record in records}
            ),
            "failure_count": len(failures),
            "failures": failures,
        }
        report_path = run_dir / "roundtrip_report.json"
        report_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2))
        log_event(
            service="components-fetch",
            event="fetch.daily.roundtrip_summary",
            report_path=report_path,
            seed_count=summary["seed_count"],
            record_count=summary["record_count"],
            failure_count=summary["failure_count"],
            lcsc_ids=summary["lcsc_ids"],
            artifact_types=summary["artifact_types"],
        )
    log_event(
        service="components-fetch",
        event="fetch.daily.complete",
        jlc_snapshot_dir=jlc_snapshot_dir,
        roundtrip_report_path=report_path,
    )
    return DailyFetchResult(
        jlc_snapshot_dir=jlc_snapshot_dir,
        roundtrip_report_path=report_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run daily Stage 1 fetch jobs.")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--no-fetch-details", action="store_true")
    parser.add_argument(
        "--max-details",
        type=int,
        default=None,
        help=(
            "Limit fetched component detail payloads for JLC ingest. "
            "Default is unlimited."
        ),
    )
    parser.add_argument(
        "--roundtrip-from-snapshot",
        action="store_true",
        default=os.getenv("ATOPILE_COMPONENTS_ROUNDTRIP_FROM_SNAPSHOT", "")
        .strip()
        .lower()
        in {"1", "true", "yes"},
        help=(
            "Run stage-1 artifact roundtrip across fetched snapshot entries "
            "(uses component_details.ndjson/component.ndjson)."
        ),
    )
    parser.add_argument(
        "--roundtrip-max-parts",
        type=int,
        default=None,
        help="Limit number of parts processed by --roundtrip-from-snapshot.",
    )
    parser.add_argument(
        "--roundtrip-retry-attempts",
        type=int,
        default=int(os.getenv("ATOPILE_COMPONENTS_ROUNDTRIP_RETRY_ATTEMPTS", "3")),
        help="Retry attempts per part for roundtrip fetch.",
    )
    parser.add_argument(
        "--roundtrip-retry-backoff-s",
        type=float,
        default=float(
            os.getenv("ATOPILE_COMPONENTS_ROUNDTRIP_RETRY_BACKOFF_S", "2.0")
        ),
        help="Linear retry backoff base seconds per failed attempt.",
    )
    parser.add_argument(
        "--roundtrip-sleep-s",
        type=float,
        default=float(os.getenv("ATOPILE_COMPONENTS_ROUNDTRIP_SLEEP_S", "0")),
        help="Sleep interval between part roundtrip attempts (for throttling).",
    )
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
        roundtrip_from_snapshot=args.roundtrip_from_snapshot,
        roundtrip_max_parts=args.roundtrip_max_parts,
        roundtrip_retry_attempts=args.roundtrip_retry_attempts,
        roundtrip_retry_backoff_s=args.roundtrip_retry_backoff_s,
        roundtrip_sleep_s=args.roundtrip_sleep_s,
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


def test_load_lcsc_seed_map_from_snapshot(tmp_path) -> None:
    snapshot = tmp_path / "fetch" / "jlc_api" / "snapshot"
    snapshot.mkdir(parents=True, exist_ok=True)
    (snapshot / "component_details.ndjson").write_text(
        "\n".join(
            (
                json.dumps(
                    {
                        "lcscPart": "C21190",
                        "detail": {"datasheetUrl": "https://example.com/C21190.pdf"},
                    },
                    ensure_ascii=True,
                ),
                json.dumps(
                    {
                        "lcscPart": "C2040",
                        "detail": {"componentCode": "C2040"},
                    },
                    ensure_ascii=True,
                ),
            )
        ),
        encoding="utf-8",
    )
    (snapshot / "components.ndjson").write_text(
        json.dumps({"lcscPart": "C3000"}, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    seed_map = _load_lcsc_seed_map_from_snapshot(snapshot)
    assert set(seed_map) == {2040, 3000, 21190}
    assert seed_map[21190].datasheet_url == "https://example.com/C21190.pdf"
    assert seed_map[2040].datasheet_url is None


def test_is_retryable_roundtrip_error_http_status() -> None:
    request = httpx.Request("GET", "https://example.com")
    retryable = httpx.HTTPStatusError(
        "throttled",
        request=request,
        response=httpx.Response(429, request=request),
    )
    non_retryable = httpx.HTTPStatusError(
        "not found",
        request=request,
        response=httpx.Response(404, request=request),
    )
    assert _is_retryable_roundtrip_error(retryable) is True
    assert _is_retryable_roundtrip_error(non_retryable) is False


if __name__ == "__main__":
    raise SystemExit(main())
