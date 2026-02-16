#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from math import ceil
from datetime import UTC, datetime
from pathlib import Path

from backend.components.fetch.config import FetchConfig
from backend.components.fetch.jobs.fetch_daily import run_fetch_daily


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _write_chunk_snapshot(
    *,
    cache_dir: Path,
    chunk_index: int,
    rows: list[tuple[int, str]],
) -> Path:
    stamp = _utc_stamp()
    snapshot = cache_dir / "fetch" / "jlc_api" / f"seed-cache-{stamp}-chunk-{chunk_index:06d}"
    snapshot.mkdir(parents=True, exist_ok=True)
    components_path = snapshot / "components.ndjson"
    details_path = snapshot / "component_details.ndjson"

    with components_path.open("w", encoding="utf-8") as cfh, details_path.open(
        "w", encoding="utf-8"
    ) as dfh:
        for lcsc_id, datasheet in rows:
            cfh.write(json.dumps({"lcscPart": f"C{int(lcsc_id)}"}, ensure_ascii=True))
            cfh.write("\n")
            dfh.write(
                json.dumps(
                    {
                        "lcscPart": f"C{int(lcsc_id)}",
                        "detail": {
                            "componentCode": f"C{int(lcsc_id)}",
                            "datasheetUrl": datasheet or "",
                        },
                    },
                    ensure_ascii=True,
                    separators=(",", ":"),
                )
            )
            dfh.write("\n")

    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run stage-1 fetch for all rows from cache.sqlite3 in chunks."
    )
    parser.add_argument(
        "--source-sqlite",
        type=Path,
        default=Path("/home/jlc/cache.sqlite3"),
        help="Path to source cache.sqlite3.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("/home/jlc/stage1_fetch"),
        help="Stage-1 cache dir root.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=50000,
        help="Number of source rows per fetch chunk.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Parallel workers for per-part artifact fetch.",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=3,
        help="Retry attempts per part.",
    )
    parser.add_argument(
        "--retry-backoff-s",
        type=float,
        default=2.0,
        help="Retry backoff base seconds.",
    )
    parser.add_argument(
        "--sleep-s",
        type=float,
        default=0.0,
        help="Optional sleep between part attempts.",
    )
    parser.add_argument(
        "--where",
        type=str,
        default="stock > 0",
        help="SQL WHERE clause over components table.",
    )
    args = parser.parse_args(argv)

    cfg = FetchConfig.from_env()
    cfg = FetchConfig(
        cache_dir=args.cache_dir,
        jlc_api_base_url=cfg.jlc_api_base_url,
        jlc_app_id=cfg.jlc_app_id,
        jlc_access_key=cfg.jlc_access_key,
        jlc_secret_key=cfg.jlc_secret_key,
        jlc_component_infos_path=cfg.jlc_component_infos_path,
        jlc_component_detail_path=cfg.jlc_component_detail_path,
        request_timeout_s=cfg.request_timeout_s,
        target_categories=cfg.target_categories,
    )

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    query = (
        "select lcsc, datasheet from components "
        f"where {args.where} "
        "order by lcsc"
    )

    with sqlite3.connect(args.source_sqlite) as conn:
        total_rows = int(
            conn.execute(
                f"select count(*) from components where {args.where}"
            ).fetchone()[0]
        )

    total_source = 0
    total_success = 0
    total_failures = 0
    chunk_index = 0
    total_chunks = max(1, ceil(total_rows / args.chunk_size))
    print(
        json.dumps(
            {
                "start": True,
                "source_rows_total": total_rows,
                "chunks_total": total_chunks,
                "chunk_size": args.chunk_size,
                "workers": args.workers,
                "where": args.where,
            },
            ensure_ascii=True,
        )
    )

    with sqlite3.connect(args.source_sqlite) as conn:
        cur = conn.cursor()
        cur.execute(query)
        while True:
            rows = cur.fetchmany(args.chunk_size)
            if not rows:
                break
            chunk_index += 1
            total_source += len(rows)
            print(
                json.dumps(
                    {
                        "chunk_start": True,
                        "chunk": chunk_index,
                        "chunks_total": total_chunks,
                        "chunks_progress": f"{chunk_index}/{total_chunks}",
                        "source_rows_progress": f"{min(total_source, total_rows)}/{total_rows}",
                    },
                    ensure_ascii=True,
                )
            )
            snapshot = _write_chunk_snapshot(
                cache_dir=args.cache_dir,
                chunk_index=chunk_index,
                rows=[(int(r[0]), str(r[1])) for r in rows],
            )
            result = run_fetch_daily(
                cfg,
                max_pages=0,
                fetch_details=False,
                max_details=0,
                roundtrip_from_snapshot=True,
                roundtrip_workers=args.workers,
                roundtrip_retry_attempts=args.retry_attempts,
                roundtrip_retry_backoff_s=args.retry_backoff_s,
                roundtrip_sleep_s=args.sleep_s,
                skip_jlc_list=True,
                snapshot_dir=snapshot,
            )
            report = json.loads(result.roundtrip_report_path.read_text(encoding="utf-8"))
            chunk_success = len(report.get("lcsc_ids", []))
            chunk_failures = int(report.get("failure_count", 0))
            total_success += chunk_success
            total_failures += chunk_failures
            pct = (100.0 * total_source / total_rows) if total_rows else 100.0
            print(
                json.dumps(
                    {
                        "chunk": chunk_index,
                        "chunks_total": total_chunks,
                        "chunks_progress": f"{chunk_index}/{total_chunks}",
                        "source_rows": len(rows),
                        "source_rows_total": total_rows,
                        "source_rows_progress": f"{total_source}/{total_rows}",
                        "source_rows_progress_pct": round(pct, 3),
                        "success_parts": chunk_success,
                        "failures": chunk_failures,
                        "skipped_already_success": report.get(
                            "skipped_already_success", 0
                        ),
                        "report": str(result.roundtrip_report_path),
                    },
                    ensure_ascii=True,
                )
            )

    print(
        json.dumps(
            {
                "done": True,
                "chunks": chunk_index,
                "chunks_total": total_chunks,
                "source_rows_seen": total_source,
                "source_rows_total": total_rows,
                "total_success_parts_in_runs": total_success,
                "total_failures_in_runs": total_failures,
                "state_db": str(args.cache_dir / "fetch" / "roundtrip_state.sqlite3"),
                "manifest_db": str(args.cache_dir / "fetch" / "manifest.sqlite3"),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
