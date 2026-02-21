from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .lookup_bench import BenchmarkSummary, run_lookup_benchmark, typical_query_cases


@dataclass(frozen=True)
class EngineSummary:
    name: str
    rows_resistors: int
    rows_capacitors: int
    iterations: int
    warmup_iterations: int
    total_time_s: float
    qps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    raw: dict[str, Any]


@dataclass(frozen=True)
class CompareSummary:
    db_path: str
    benchmark_db_path: str
    rows_resistors: int
    rows_capacitors: int
    iterations: int
    warmup_iterations: int
    sample_rows_per_table: int | None
    sqlite: EngineSummary
    zig: EngineSummary
    speedup_qps: float
    speedup_p50: float
    speedup_p95: float
    speedup_p99: float


def _format_tsv_field(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return format(value, ".17g")
    out = str(value)
    return out.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _export_fast_tables_to_tsv(
    *,
    db_path: Path,
    out_dir: Path,
) -> tuple[Path, Path, int, int]:
    resistor_tsv = out_dir / "resistor_pick.tsv"
    capacitor_tsv = out_dir / "capacitor_pick.tsv"

    resistor_query = """
        SELECT
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            resistance_min_ohm,
            resistance_max_ohm,
            tolerance_pct,
            max_power_w,
            max_voltage_v
        FROM resistor_pick
    """
    capacitor_query = """
        SELECT
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            capacitance_min_f,
            capacitance_max_f,
            tolerance_pct,
            max_voltage_v,
            tempco_code
        FROM capacitor_pick
    """

    with sqlite3.connect(db_path) as conn:
        resistor_rows = _write_query_tsv(
            conn=conn,
            query=resistor_query,
            out_path=resistor_tsv,
        )
        capacitor_rows = _write_query_tsv(
            conn=conn,
            query=capacitor_query,
            out_path=capacitor_tsv,
        )
    return resistor_tsv, capacitor_tsv, resistor_rows, capacitor_rows


def _write_query_tsv(
    *,
    conn: sqlite3.Connection,
    query: str,
    out_path: Path,
    chunk_size: int = 20_000,
) -> int:
    cursor = conn.execute(query)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        while True:
            chunk = cursor.fetchmany(chunk_size)
            if not chunk:
                break
            for row in chunk:
                fields = [_format_tsv_field(value) for value in row]
                handle.write("\t".join(fields))
                handle.write("\n")
            rows_written += len(chunk)
    return rows_written


def _build_sample_db(
    *,
    source_db_path: Path,
    out_db_path: Path,
    rows_per_table: int,
) -> None:
    out_db_path.parent.mkdir(parents=True, exist_ok=True)
    if out_db_path.exists():
        out_db_path.unlink()

    with sqlite3.connect(out_db_path) as conn:
        conn.execute("ATTACH DATABASE ? AS src", (str(source_db_path),))
        conn.execute(
            """
            CREATE TABLE resistor_pick AS
            SELECT * FROM src.resistor_pick
            ORDER BY lcsc_id
            LIMIT ?
            """,
            (rows_per_table,),
        )
        conn.execute(
            """
            CREATE TABLE capacitor_pick AS
            SELECT * FROM src.capacitor_pick
            ORDER BY lcsc_id
            LIMIT ?
            """,
            (rows_per_table,),
        )
        conn.executescript(
            """
            CREATE INDEX resistor_pick_lookup_pkg_idx
            ON resistor_pick (
                package,
                resistance_min_ohm,
                resistance_max_ohm,
                max_power_w,
                max_voltage_v,
                stock DESC
            );
            CREATE INDEX resistor_pick_lookup_range_idx
            ON resistor_pick (
                resistance_min_ohm,
                resistance_max_ohm,
                max_power_w,
                max_voltage_v,
                stock DESC
            );
            CREATE INDEX capacitor_pick_lookup_pkg_idx
            ON capacitor_pick (
                package,
                tempco_code,
                capacitance_min_f,
                capacitance_max_f,
                max_voltage_v,
                stock DESC
            );
            CREATE INDEX capacitor_pick_lookup_range_idx
            ON capacitor_pick (
                capacitance_min_f,
                capacitance_max_f,
                max_voltage_v,
                stock DESC
            );
            ANALYZE;
            PRAGMA optimize;
            """
        )
        conn.execute("DETACH DATABASE src")
        conn.commit()


def _build_zig_benchmark_binary(
    *,
    source_path: Path,
    out_binary_path: Path,
) -> None:
    out_binary_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "zig",
        "build-exe",
        str(source_path),
        "-O",
        "ReleaseFast",
        f"-femit-bin={out_binary_path}",
    ]
    subprocess.run(cmd, check=True)


def _run_zig_benchmark(
    *,
    binary_path: Path,
    resistor_tsv: Path,
    capacitor_tsv: Path,
    iterations: int,
    warmup: int,
    seed: int,
) -> dict[str, Any]:
    cmd = [
        str(binary_path),
        "--resistors-tsv",
        str(resistor_tsv),
        "--capacitors-tsv",
        str(capacitor_tsv),
        "--iterations",
        str(iterations),
        "--warmup",
        str(warmup),
        "--seed",
        str(seed),
    ]
    proc = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.stderr.strip():
        print(proc.stderr.strip())
    return json.loads(proc.stdout)


def _engine_from_sqlite(summary: BenchmarkSummary) -> EngineSummary:
    return EngineSummary(
        name="sqlite",
        rows_resistors=summary.rows_resistors,
        rows_capacitors=summary.rows_capacitors,
        iterations=summary.iterations,
        warmup_iterations=summary.warmup_iterations,
        total_time_s=summary.total_time_s,
        qps=summary.qps,
        p50_ms=summary.overall.p50_ms,
        p95_ms=summary.overall.p95_ms,
        p99_ms=summary.overall.p99_ms,
        mean_ms=summary.overall.mean_ms,
        raw=asdict(summary),
    )


def _engine_from_zig(payload: dict[str, Any]) -> EngineSummary:
    overall = payload["overall"]
    return EngineSummary(
        name="zig_in_memory",
        rows_resistors=int(payload["rows_resistors"]),
        rows_capacitors=int(payload["rows_capacitors"]),
        iterations=int(payload["iterations"]),
        warmup_iterations=int(payload["warmup_iterations"]),
        total_time_s=float(payload["total_time_s"]),
        qps=float(payload["qps"]),
        p50_ms=float(overall["p50_ms"]),
        p95_ms=float(overall["p95_ms"]),
        p99_ms=float(overall["p99_ms"]),
        mean_ms=float(overall["mean_ms"]),
        raw=payload,
    )


def run_compare(
    *,
    db_path: Path,
    iterations: int,
    warmup: int,
    seed: int,
    sample_rows_per_table: int | None = None,
) -> CompareSummary:
    start = time.perf_counter()
    zig_source = Path(__file__).with_name("zig_lookup_bench.zig")

    with tempfile.TemporaryDirectory(prefix="components-zig-bench-") as temp_dir:
        temp_root = Path(temp_dir)
        benchmark_db = db_path
        if sample_rows_per_table is not None:
            benchmark_db = temp_root / "fast.sample.sqlite"
            _build_sample_db(
                source_db_path=db_path,
                out_db_path=benchmark_db,
                rows_per_table=sample_rows_per_table,
            )

        resistor_tsv, capacitor_tsv, rows_r, rows_c = _export_fast_tables_to_tsv(
            db_path=benchmark_db,
            out_dir=temp_root / "dataset",
        )

        zig_binary = temp_root / "zig_lookup_bench"
        _build_zig_benchmark_binary(
            source_path=zig_source,
            out_binary_path=zig_binary,
        )
        zig_payload = _run_zig_benchmark(
            binary_path=zig_binary,
            resistor_tsv=resistor_tsv,
            capacitor_tsv=capacitor_tsv,
            iterations=iterations,
            warmup=warmup,
            seed=seed,
        )
        zig_summary = _engine_from_zig(zig_payload)

        sqlite_summary_raw = run_lookup_benchmark(
            db_path=benchmark_db,
            iterations=iterations,
            warmup_iterations=warmup,
            cases=typical_query_cases(),
            seed=seed,
        )
        sqlite_summary = _engine_from_sqlite(sqlite_summary_raw)

        if (
            rows_r != zig_summary.rows_resistors
            or rows_c != zig_summary.rows_capacitors
        ):
            raise RuntimeError("Zig TSV export row count mismatch")
        if sqlite_summary.rows_resistors != zig_summary.rows_resistors:
            raise RuntimeError("SQLite and Zig resistor counts mismatch")
        if sqlite_summary.rows_capacitors != zig_summary.rows_capacitors:
            raise RuntimeError("SQLite and Zig capacitor counts mismatch")

        summary = CompareSummary(
            db_path=str(db_path),
            benchmark_db_path=str(benchmark_db),
            rows_resistors=zig_summary.rows_resistors,
            rows_capacitors=zig_summary.rows_capacitors,
            iterations=iterations,
            warmup_iterations=warmup,
            sample_rows_per_table=sample_rows_per_table,
            sqlite=sqlite_summary,
            zig=zig_summary,
            speedup_qps=_safe_ratio(zig_summary.qps, sqlite_summary.qps),
            speedup_p50=_safe_ratio(sqlite_summary.p50_ms, zig_summary.p50_ms),
            speedup_p95=_safe_ratio(sqlite_summary.p95_ms, zig_summary.p95_ms),
            speedup_p99=_safe_ratio(sqlite_summary.p99_ms, zig_summary.p99_ms),
        )
        elapsed = time.perf_counter() - start
        print(
            f"prepared+benchmarked in {elapsed:.2f}s "
            f"(rows={summary.rows_resistors + summary.rows_capacitors:,})"
        )
        return summary


def _safe_ratio(lhs: float, rhs: float) -> float:
    if rhs == 0:
        return 0.0
    return lhs / rhs


def _print_summary(summary: CompareSummary) -> None:
    print()
    print("Lookup Engine Comparison")
    print(f"  source_db: {summary.db_path}")
    print(f"  benchmark_db: {summary.benchmark_db_path}")
    print(
        "  rows: "
        f"resistor={summary.rows_resistors:,} "
        f"capacitor={summary.rows_capacitors:,}"
    )
    print(
        f"  run: iterations={summary.iterations:,} warmup={summary.warmup_iterations:,}"
    )
    print()
    for engine in (summary.sqlite, summary.zig):
        print(
            f"{engine.name:>13}: "
            f"qps={engine.qps:9.1f} "
            f"p50={engine.p50_ms:7.4f}ms "
            f"p95={engine.p95_ms:7.4f}ms "
            f"p99={engine.p99_ms:7.4f}ms "
            f"mean={engine.mean_ms:7.4f}ms"
        )
    print()
    print(
        "  speedup: "
        f"qps={summary.speedup_qps:.2f}x "
        f"p50={summary.speedup_p50:.2f}x "
        f"p95={summary.speedup_p95:.2f}x "
        f"p99={summary.speedup_p99:.2f}x"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare stage-3 SQLite lookup vs experimental Zig in-memory lookup "
            "on the same fast snapshot rows."
        )
    )
    parser.add_argument(
        "--db",
        type=Path,
        required=True,
        help="Path to fast.sqlite snapshot",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5_000,
        help="Measured lookup iterations per engine.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=500,
        help="Warmup iterations per engine.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="PRNG seed for weighted query workload.",
    )
    parser.add_argument(
        "--sample-rows-per-table",
        type=int,
        default=None,
        help=(
            "Optional row cap per pick table before benchmarking. "
            "Both engines use the same sampled sqlite."
        ),
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path for machine-readable summary JSON.",
    )
    args = parser.parse_args(argv)

    summary = run_compare(
        db_path=args.db,
        iterations=args.iterations,
        warmup=args.warmup,
        seed=args.seed,
        sample_rows_per_table=args.sample_rows_per_table,
    )
    _print_summary(summary)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(asdict(summary), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        print(f"\nWrote JSON summary to {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
