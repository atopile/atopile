from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ...shared.telemetry import log_event
from ..config import FetchConfig
from ..models import FetchArtifactRecord
from ..sources.jlc_api import JlcApiClient
from ..sources.lcsc import LcscFetchSeed, fetch_lcsc_artifacts_with_roundtrip
from ..storage.manifest_store import LocalManifestStore
from ..storage.object_store import LocalObjectStore


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _config_payload_without_secrets(config: FetchConfig) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in asdict(config).items():
        if key in {"jlc_app_id", "jlc_access_key", "jlc_secret_key"}:
            continue
        if isinstance(value, Path):
            out[key] = str(value)
        elif isinstance(value, tuple):
            out[key] = list(value)
        else:
            out[key] = value
    return out


def _extract_lcsc_part(component: dict[str, Any]) -> str | None:
    for key in ("lcscPart", "componentCode", "lcscPartNumber"):
        value = component.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raw_lcsc = component.get("lcsc")
    if isinstance(raw_lcsc, int):
        return f"C{raw_lcsc}"
    if isinstance(raw_lcsc, str) and raw_lcsc.strip():
        stripped = raw_lcsc.strip()
        return stripped if stripped.startswith("C") else f"C{stripped}"
    return None


def _load_previous_snapshot_metadata(
    cache_dir: Path, *, current_run_name: str
) -> dict[str, Any] | None:
    history_root = cache_dir / "fetch" / "jlc_api"
    if not history_root.exists():
        return None
    candidates = sorted(
        path
        for path in history_root.iterdir()
        if path.is_dir() and path.name < current_run_name
    )
    for candidate in reversed(candidates):
        metadata_path = candidate / "metadata.json"
        if not metadata_path.exists():
            continue
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def run_fetch_once(
    config: FetchConfig,
    *,
    max_pages: int | None = None,
    fetch_details: bool = False,
    max_details: int | None = None,
    api_factory: Callable[[FetchConfig], JlcApiClient] = JlcApiClient,
) -> Path:
    run_name = _utc_stamp()
    out_dir = config.cache_dir / "fetch" / "jlc_api" / run_name
    log_event(
        service="components-fetch",
        event="fetch.once.start",
        out_dir=out_dir,
        max_pages=max_pages,
        fetch_details=fetch_details,
        max_details=max_details,
        target_categories=list(config.target_categories),
    )
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as ex:
        raise PermissionError(
            "Cannot create fetch cache directory at "
            f"{out_dir}. Set ATOPILE_COMPONENTS_CACHE_DIR to a writable path."
        ) from ex

    component_file = out_dir / "components.ndjson"
    detail_file = out_dir / "component_details.ndjson"
    component_count = 0
    detail_count = 0
    last_trace_id: str | None = None
    category_counts: Counter[str] = Counter()
    started_at = datetime.now(UTC)

    with ExitStack() as stack:
        api = stack.enter_context(api_factory(config))
        components_handle = stack.enter_context(
            component_file.open("w", encoding="utf-8")
        )
        details_handle = stack.enter_context(
            detail_file.open("w", encoding="utf-8") if fetch_details else _null_writer()
        )
        for component in api.iter_target_component_infos(max_pages=max_pages):
            components_handle.write(
                json.dumps(component, ensure_ascii=True, separators=(",", ":"))
            )
            components_handle.write("\n")
            component_count += 1
            category = component.get("firstCategory")
            if isinstance(category, str) and category.strip():
                category_counts[category.strip()] += 1
            else:
                category_counts["<unknown>"] += 1

            if not fetch_details:
                continue
            if max_details is not None and detail_count >= max_details:
                continue
            lcsc_part = _extract_lcsc_part(component)
            if not lcsc_part:
                continue
            detail = api.get_component_detail(lcsc_part)
            detail_record = {"lcscPart": lcsc_part, "detail": detail}
            details_handle.write(
                json.dumps(detail_record, ensure_ascii=True, separators=(",", ":"))
            )
            details_handle.write("\n")
            detail_count += 1

        last_trace_id = api.last_trace_id

    previous_snapshot = _load_previous_snapshot_metadata(
        config.cache_dir,
        current_run_name=run_name,
    )
    previous_record_count: int | None = None
    if previous_snapshot is not None:
        try:
            previous_record_count = int(previous_snapshot.get("record_count"))
        except Exception:
            previous_record_count = None
    record_count_delta = (
        component_count - previous_record_count
        if previous_record_count is not None
        else None
    )
    duration_seconds = round((datetime.now(UTC) - started_at).total_seconds(), 3)

    metadata = {
        "fetched_at_utc": run_name,
        "source": "jlc_api",
        "target_categories": list(config.target_categories),
        "record_count": component_count,
        "record_count_delta": record_count_delta,
        "previous_record_count": previous_record_count,
        "category_counts": dict(sorted(category_counts.items())),
        "detail_record_count": detail_count,
        "fetch_details": fetch_details,
        "max_pages": max_pages,
        "max_details": max_details,
        "last_trace_id": last_trace_id,
        "duration_seconds": duration_seconds,
        "config": _config_payload_without_secrets(config),
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    if not fetch_details and detail_file.exists():
        detail_file.unlink()
    log_event(
        service="components-fetch",
        event="fetch.once.complete",
        out_dir=out_dir,
        record_count=component_count,
        detail_record_count=detail_count,
        record_count_delta=record_count_delta,
        category_counts=dict(sorted(category_counts.items())),
        duration_seconds=duration_seconds,
        last_trace_id=last_trace_id,
    )
    return out_dir


class _null_writer:
    def __enter__(self) -> _null_writer:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def write(self, text: str) -> int:
        del text
        return 0


def run_lcsc_asset_roundtrip_once(
    *,
    config: FetchConfig,
    lcsc_id: int,
    datasheet_url: str | None = None,
    client: httpx.Client | None = None,
    easyeda_footprint_converter: Callable[[dict[str, Any]], bytes] | None = None,
) -> list[FetchArtifactRecord]:
    started_at = datetime.now(UTC)
    log_event(
        service="components-fetch",
        event="fetch.roundtrip.start",
        lcsc_id=lcsc_id,
        has_datasheet_url=bool(datasheet_url),
    )
    object_store = LocalObjectStore(config.cache_dir)
    manifest_store = LocalManifestStore(config.cache_dir)
    seed = LcscFetchSeed(lcsc_id=lcsc_id, datasheet_url=datasheet_url)
    records = fetch_lcsc_artifacts_with_roundtrip(
        seed=seed,
        config=config,
        object_store=object_store,
        manifest_store=manifest_store,
        client=client,
        easyeda_footprint_converter=easyeda_footprint_converter,
    )
    artifact_counts = Counter(record.artifact_type.value for record in records)
    duration_seconds = round((datetime.now(UTC) - started_at).total_seconds(), 3)
    log_event(
        service="components-fetch",
        event="fetch.roundtrip.complete",
        lcsc_id=lcsc_id,
        record_count=len(records),
        artifact_counts=dict(sorted(artifact_counts.items())),
        compare_ok=all(record.compare_ok for record in records),
        duration_seconds=duration_seconds,
    )
    return records


def write_roundtrip_report(
    *,
    config: FetchConfig,
    lcsc_id: int,
    records: list[FetchArtifactRecord],
) -> Path:
    report_dir = config.cache_dir / "fetch" / "roundtrip" / _utc_stamp()
    report_dir.mkdir(parents=True, exist_ok=True)
    artifact_counts = Counter(record.artifact_type.value for record in records)
    compare_ok = all(record.compare_ok for record in records)
    payload = {
        "created_at_utc": _utc_stamp(),
        "lcsc_id": lcsc_id,
        "record_count": len(records),
        "compare_ok": compare_ok,
        "artifact_counts": dict(sorted(artifact_counts.items())),
        "records": [
            {
                "artifact_type": record.artifact_type.value,
                "stored_key": record.stored_key,
                "raw_sha256": record.raw_sha256,
                "raw_size_bytes": record.raw_size_bytes,
                "compare_ok": record.compare_ok,
            }
            for record in records
        ],
    }
    report_path = report_dir / f"C{lcsc_id}.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2))
    log_event(
        service="components-fetch",
        event="fetch.roundtrip.report_written",
        lcsc_id=lcsc_id,
        report_path=report_path,
        record_count=len(records),
        compare_ok=compare_ok,
    )
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage 1 fetch once.")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit number of pages for local/dev runs.",
    )
    parser.add_argument(
        "--fetch-details",
        action="store_true",
        help="Fetch per-component detail payloads during JLC list ingest.",
    )
    parser.add_argument(
        "--max-details",
        type=int,
        default=None,
        help="Limit number of component detail fetches when --fetch-details is used.",
    )
    parser.add_argument(
        "--skip-jlc-list",
        action="store_true",
        help="Skip JLC list fetch and only run optional roundtrip checks.",
    )
    parser.add_argument(
        "--roundtrip-lcsc-id",
        type=int,
        default=None,
        help="Optional LCSC numeric ID to run artifact fetch+roundtrip validation.",
    )
    parser.add_argument(
        "--roundtrip-datasheet-url",
        type=str,
        default=None,
        help="Optional datasheet URL for --roundtrip-lcsc-id.",
    )
    args = parser.parse_args(argv)
    config = FetchConfig.from_env()

    if not args.skip_jlc_list:
        out_dir = run_fetch_once(
            config,
            max_pages=args.max_pages,
            fetch_details=args.fetch_details,
            max_details=args.max_details,
        )
        print(out_dir)

    if args.roundtrip_lcsc_id is not None:
        roundtrip_records = run_lcsc_asset_roundtrip_once(
            config=config,
            lcsc_id=args.roundtrip_lcsc_id,
            datasheet_url=args.roundtrip_datasheet_url,
        )
        report_path = write_roundtrip_report(
            config=config,
            lcsc_id=args.roundtrip_lcsc_id,
            records=roundtrip_records,
        )
        print(
            f"roundtrip records: {len(roundtrip_records)} for C{args.roundtrip_lcsc_id}"
        )
        print(report_path)
    return 0


def test_run_fetch_once_writes_snapshot(tmp_path) -> None:
    class FakeApi:
        last_trace_id = "trace-123"

        def __enter__(self) -> FakeApi:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def iter_target_component_infos(
            self, *, max_pages: int | None = None
        ) -> Iterator[dict]:
            del max_pages
            yield {"lcscPart": "C1", "firstCategory": "Resistors"}
            yield {"lcscPart": "C2", "firstCategory": "Capacitors"}

        def get_component_detail(self, lcsc_part: str | int) -> dict[str, object]:
            return {"lcscPart": str(lcsc_part)}

    config = FetchConfig(
        cache_dir=tmp_path,
        jlc_api_base_url="https://open.jlcpcb.com",
        jlc_app_id="app-id",
        jlc_access_key="access-key",
        jlc_secret_key="secret-key",
        jlc_component_infos_path="/overseas/openapi/component/getComponentInfos",
        jlc_component_detail_path="/overseas/openapi/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )

    out_dir = run_fetch_once(config, api_factory=lambda _cfg: FakeApi())
    lines = (out_dir / "components.ndjson").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert not (out_dir / "component_details.ndjson").exists()
    metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["source"] == "jlc_api"
    assert metadata["record_count"] == 2
    assert metadata["detail_record_count"] == 0
    assert metadata["last_trace_id"] == "trace-123"
    assert "jlc_app_id" not in metadata["config"]
    assert "jlc_access_key" not in metadata["config"]
    assert "jlc_secret_key" not in metadata["config"]


def test_run_fetch_once_with_details(tmp_path) -> None:
    class FakeApi:
        last_trace_id = "trace-details"

        def __enter__(self) -> FakeApi:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def iter_target_component_infos(
            self, *, max_pages: int | None = None
        ) -> Iterator[dict]:
            del max_pages
            yield {"lcscPart": "C1", "firstCategory": "Resistors"}
            yield {"lcscPart": "C2", "firstCategory": "Capacitors"}

        def get_component_detail(self, lcsc_part: str | int) -> dict[str, object]:
            return {"componentCode": str(lcsc_part), "stock": 42}

    config = FetchConfig(
        cache_dir=tmp_path,
        jlc_api_base_url="https://open.jlcpcb.com",
        jlc_app_id="app-id",
        jlc_access_key="access-key",
        jlc_secret_key="secret-key",
        jlc_component_infos_path="/overseas/openapi/component/getComponentInfos",
        jlc_component_detail_path="/overseas/openapi/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )

    out_dir = run_fetch_once(
        config,
        fetch_details=True,
        max_details=1,
        api_factory=lambda _cfg: FakeApi(),
    )
    detail_lines = (
        (out_dir / "component_details.ndjson").read_text(encoding="utf-8").splitlines()
    )
    assert len(detail_lines) == 1
    detail_record = json.loads(detail_lines[0])
    assert detail_record["lcscPart"] == "C1"
    metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["detail_record_count"] == 1
    assert metadata["fetch_details"] is True


def test_run_lcsc_asset_roundtrip_once_with_easyeda_only(tmp_path) -> None:
    cad_data = {"packageDetail": {"dataStr": {"shape": []}}}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "easyeda.com":
            return httpx.Response(
                200,
                json={"code": 200, "success": True, "result": cad_data},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    config = FetchConfig(
        cache_dir=tmp_path,
        jlc_api_base_url="https://open.jlcpcb.com",
        jlc_app_id="app-id",
        jlc_access_key="access-key",
        jlc_secret_key="secret-key",
        jlc_component_infos_path="/overseas/openapi/component/getComponentInfos",
        jlc_component_detail_path="/overseas/openapi/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )

    mock_footprint = b'(footprint "easyeda2kicad:R0603")\n'

    def mock_converter(cad: dict[str, Any]) -> bytes:
        assert cad == cad_data
        return mock_footprint

    records = run_lcsc_asset_roundtrip_once(
        config=config,
        lcsc_id=2040,
        client=client,
        easyeda_footprint_converter=mock_converter,
    )
    report_path = write_roundtrip_report(config=config, lcsc_id=2040, records=records)
    client.close()

    assert records
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["compare_ok"] is True


if __name__ == "__main__":
    raise SystemExit(main())
