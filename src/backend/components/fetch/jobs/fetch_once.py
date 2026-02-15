from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterator
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from ..config import FetchConfig
from ..sources.jlc_api import JlcApiClient


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def run_fetch_once(
    config: FetchConfig,
    *,
    max_pages: int | None = None,
    api_factory: Callable[[FetchConfig], JlcApiClient] = JlcApiClient,
) -> Path:
    out_dir = config.cache_dir / "fetch" / "jlc_api" / _utc_stamp()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "components.ndjson"
    count = 0
    last_trace_id: str | None = None

    with api_factory(config) as api, out_file.open("w", encoding="utf-8") as handle:
        for component in api.iter_target_component_infos(max_pages=max_pages):
            payload = json.dumps(
                component,
                ensure_ascii=True,
                separators=(",", ":"),
            )
            handle.write(payload)
            handle.write("\n")
            count += 1
        last_trace_id = api.last_trace_id

    config_payload: dict[str, object] = {}
    for key, value in asdict(config).items():
        if key in {"jlc_app_key", "jlc_app_secret"}:
            continue
        if isinstance(value, Path):
            config_payload[key] = str(value)
        elif isinstance(value, tuple):
            config_payload[key] = list(value)
        else:
            config_payload[key] = value

    metadata = {
        "fetched_at_utc": _utc_stamp(),
        "source": "jlc_api",
        "target_categories": list(config.target_categories),
        "record_count": count,
        "max_pages": max_pages,
        "last_trace_id": last_trace_id,
        "config": config_payload,
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8"
    )
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch a single JLC API raw snapshot.")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit number of pages for local/dev runs.",
    )
    args = parser.parse_args(argv)
    config = FetchConfig.from_env()
    out_dir = run_fetch_once(config, max_pages=args.max_pages)
    print(out_dir)
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

    config = FetchConfig(
        cache_dir=tmp_path,
        jlc_api_base_url="https://jlcpcb.com",
        jlc_app_key="key",
        jlc_app_secret="secret",
        jlc_token_path="/external/genToken",
        jlc_component_infos_path="/external/component/getComponentInfos",
        jlc_component_detail_path="/external/component/getComponentDetail",
        request_timeout_s=10.0,
        target_categories=("Resistors", "Capacitors"),
    )

    out_dir = run_fetch_once(config, api_factory=lambda _cfg: FakeApi())
    lines = (out_dir / "components.ndjson").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["source"] == "jlc_api"
    assert metadata["record_count"] == 2
    assert metadata["last_trace_id"] == "trace-123"


if __name__ == "__main__":
    raise SystemExit(main())
