from __future__ import annotations

import argparse
import json
import random
import sqlite3
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .fast_lookup_sqlite import SQLiteFastLookupStore, _quote_ident
from .interfaces import NumericRange, ParameterQuery

ComponentKind = Literal["resistor", "capacitor"]


@dataclass(frozen=True)
class QueryCase:
    name: str
    component_type: ComponentKind
    query: ParameterQuery
    weight: int = 1


@dataclass(frozen=True)
class QueryLatencyStats:
    name: str
    component_type: ComponentKind
    runs: int
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    avg_candidates: float


@dataclass(frozen=True)
class BenchmarkSummary:
    db_path: str
    rows_resistors: int
    rows_capacitors: int
    iterations: int
    warmup_iterations: int
    total_time_s: float
    qps: float
    overall: QueryLatencyStats
    per_case: list[QueryLatencyStats]


def typical_query_cases() -> list[QueryCase]:
    """
    Typical workloads derived from:
    - faebryk library usage examples for Resistor/Capacitor
    - examples/passives, examples/pick_parts, examples/i2c, examples/led_badge
    """
    return [
        QueryCase(
            name="r_10k_5pct_pkg",
            component_type="resistor",
            weight=20,
            query=ParameterQuery(
                qty=1,
                limit=50,
                package="R0402",
                ranges={
                    "resistance_ohm": NumericRange(minimum=9_500, maximum=10_500),
                    "tolerance_pct": NumericRange(maximum=5.0),
                },
            ),
        ),
        QueryCase(
            name="r_10k_20pct_pkg",
            component_type="resistor",
            weight=14,
            query=ParameterQuery(
                qty=1,
                limit=50,
                package="R0402",
                ranges={
                    "resistance_ohm": NumericRange(minimum=8_000, maximum=12_000),
                    "tolerance_pct": NumericRange(maximum=20.0),
                },
            ),
        ),
        QueryCase(
            name="r_10k_1pct_unpkg",
            component_type="resistor",
            weight=8,
            query=ParameterQuery(
                qty=1,
                limit=50,
                ranges={
                    "resistance_ohm": NumericRange(minimum=9_900, maximum=10_100),
                    "tolerance_pct": NumericRange(maximum=1.0),
                },
            ),
        ),
        QueryCase(
            name="r_5k1_1pct_pkg",
            component_type="resistor",
            weight=6,
            query=ParameterQuery(
                qty=1,
                limit=30,
                package="R0402",
                ranges={
                    "resistance_ohm": NumericRange(minimum=5_050, maximum=5_150),
                    "tolerance_pct": NumericRange(maximum=1.0),
                },
            ),
        ),
        QueryCase(
            name="r_120r_1pct_pkg",
            component_type="resistor",
            weight=5,
            query=ParameterQuery(
                qty=1,
                limit=30,
                package="R0603",
                ranges={
                    "resistance_ohm": NumericRange(minimum=118, maximum=122),
                    "tolerance_pct": NumericRange(maximum=1.0),
                },
            ),
        ),
        QueryCase(
            name="r_50k_10pct_unpkg",
            component_type="resistor",
            weight=4,
            query=ParameterQuery(
                qty=1,
                limit=30,
                ranges={
                    "resistance_ohm": NumericRange(minimum=45_000, maximum=55_000),
                    "tolerance_pct": NumericRange(maximum=10.0),
                },
            ),
        ),
        QueryCase(
            name="c_100n_20pct_pkg",
            component_type="capacitor",
            weight=20,
            query=ParameterQuery(
                qty=1,
                limit=50,
                package="C0402",
                ranges={
                    "capacitance_f": NumericRange(minimum=80e-9, maximum=120e-9),
                    "tolerance_pct": NumericRange(maximum=20.0),
                    "max_voltage_v": NumericRange(minimum=10.0),
                },
                exact={"tempco_code": "X7R"},
            ),
        ),
        QueryCase(
            name="c_100n_10pct_unpkg",
            component_type="capacitor",
            weight=8,
            query=ParameterQuery(
                qty=1,
                limit=50,
                ranges={
                    "capacitance_f": NumericRange(minimum=90e-9, maximum=110e-9),
                    "tolerance_pct": NumericRange(maximum=10.0),
                    "max_voltage_v": NumericRange(minimum=16.0),
                },
            ),
        ),
        QueryCase(
            name="c_2u2_20pct_pkg",
            component_type="capacitor",
            weight=10,
            query=ParameterQuery(
                qty=1,
                limit=40,
                package="C0402",
                ranges={
                    "capacitance_f": NumericRange(minimum=1.8e-6, maximum=2.6e-6),
                    "tolerance_pct": NumericRange(maximum=20.0),
                    "max_voltage_v": NumericRange(minimum=6.3),
                },
                exact={"tempco_code": "X5R"},
            ),
        ),
        QueryCase(
            name="c_22pf_5pct_pkg",
            component_type="capacitor",
            weight=4,
            query=ParameterQuery(
                qty=1,
                limit=20,
                package="C0402",
                ranges={
                    "capacitance_f": NumericRange(minimum=21e-12, maximum=23e-12),
                    "tolerance_pct": NumericRange(maximum=5.0),
                    "max_voltage_v": NumericRange(minimum=16.0),
                },
                exact={"tempco_code": "C0G"},
            ),
        ),
    ]


def build_synthetic_fast_db(
    db_path: Path,
    *,
    resistor_rows: int,
    capacitor_rows: int,
    seed: int = 0,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    rng = random.Random(seed)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        PRAGMA cache_size=-200000;
        PRAGMA locking_mode=EXCLUSIVE;

        CREATE TABLE resistor_pick (
            lcsc_id INTEGER PRIMARY KEY NOT NULL,
            package TEXT NOT NULL,
            stock INTEGER NOT NULL,
            is_basic INTEGER NOT NULL,
            is_preferred INTEGER NOT NULL,
            resistance_ohm REAL NOT NULL,
            tolerance_pct REAL,
            max_power_w REAL,
            max_voltage_v REAL,
            tempco_ppm REAL
        );

        CREATE TABLE capacitor_pick (
            lcsc_id INTEGER PRIMARY KEY NOT NULL,
            package TEXT NOT NULL,
            stock INTEGER NOT NULL,
            is_basic INTEGER NOT NULL,
            is_preferred INTEGER NOT NULL,
            capacitance_f REAL NOT NULL,
            tolerance_pct REAL,
            max_voltage_v REAL,
            tempco_code TEXT
        );
        """
    )

    resistor_pool = _resistor_value_pool()
    capacitor_pool = _capacitor_value_pool()

    res_rows: list[tuple[Any, ...]] = []
    for i in range(resistor_rows):
        lcsc_id = 100_000_000 + i
        value = _weighted_pick(rng, resistor_pool["resistance_ohm"])
        tolerance = _weighted_pick(rng, resistor_pool["tolerance_pct"])
        package = _weighted_pick(rng, resistor_pool["package"])
        stock = _synth_stock(rng)
        is_basic = 1 if rng.random() < 0.35 else 0
        is_preferred = 1 if rng.random() < 0.10 else 0
        max_power = _weighted_pick(rng, resistor_pool["max_power_w"])
        max_voltage = _weighted_pick(rng, resistor_pool["max_voltage_v"])
        tempco = _weighted_pick(rng, resistor_pool["tempco_ppm"])
        res_rows.append(
            (
                lcsc_id,
                package,
                stock,
                is_basic,
                is_preferred,
                value,
                tolerance,
                max_power,
                max_voltage,
                tempco,
            )
        )
    conn.executemany(
        """
        INSERT INTO resistor_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            resistance_ohm,
            tolerance_pct,
            max_power_w,
            max_voltage_v,
            tempco_ppm
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        res_rows,
    )

    cap_rows: list[tuple[Any, ...]] = []
    for i in range(capacitor_rows):
        lcsc_id = 200_000_000 + i
        value = _weighted_pick(rng, capacitor_pool["capacitance_f"])
        tolerance = _weighted_pick(rng, capacitor_pool["tolerance_pct"])
        package = _weighted_pick(rng, capacitor_pool["package"])
        stock = _synth_stock(rng)
        is_basic = 1 if rng.random() < 0.40 else 0
        is_preferred = 1 if rng.random() < 0.12 else 0
        max_voltage = _weighted_pick(rng, capacitor_pool["max_voltage_v"])
        tempco_code = _weighted_pick(rng, capacitor_pool["tempco_code"])
        cap_rows.append(
            (
                lcsc_id,
                package,
                stock,
                is_basic,
                is_preferred,
                value,
                tolerance,
                max_voltage,
                tempco_code,
            )
        )
    conn.executemany(
        """
        INSERT INTO capacitor_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            capacitance_f,
            tolerance_pct,
            max_voltage_v,
            tempco_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        cap_rows,
    )

    conn.executescript(
        """
        CREATE INDEX resistor_pick_lookup_pkg_idx
        ON resistor_pick (
            package,
            resistance_ohm,
            tolerance_pct,
            max_power_w,
            max_voltage_v,
            stock DESC
        );
        CREATE INDEX resistor_pick_lookup_range_idx
        ON resistor_pick (
            resistance_ohm,
            tolerance_pct,
            max_power_w,
            max_voltage_v,
            stock DESC
        );
        CREATE INDEX capacitor_pick_lookup_pkg_idx
        ON capacitor_pick (
            package,
            tempco_code,
            capacitance_f,
            tolerance_pct,
            max_voltage_v,
            stock DESC
        );
        CREATE INDEX capacitor_pick_lookup_range_idx
        ON capacitor_pick (
            capacitance_f,
            tolerance_pct,
            max_voltage_v,
            stock DESC
        );
        ANALYZE;
        PRAGMA optimize;
        """
    )
    conn.commit()
    conn.close()


def run_lookup_benchmark(
    *,
    db_path: Path,
    iterations: int,
    warmup_iterations: int,
    cases: list[QueryCase] | None = None,
    seed: int = 0,
) -> BenchmarkSummary:
    query_cases = cases or typical_query_cases()
    if not query_cases:
        raise ValueError("No query cases provided")

    weighted_cases = _weighted_case_list(query_cases)
    rng = random.Random(seed)
    store = SQLiteFastLookupStore(db_path)

    for _ in range(max(0, warmup_iterations)):
        case = rng.choice(weighted_cases)
        _execute_case(store, case)

    total_start = time.perf_counter_ns()
    all_latencies_ns: list[int] = []
    per_case_latencies: dict[str, list[int]] = {case.name: [] for case in query_cases}
    per_case_candidates: dict[str, int] = {case.name: 0 for case in query_cases}

    for _ in range(iterations):
        case = rng.choice(weighted_cases)
        start = time.perf_counter_ns()
        candidates = _execute_case(store, case)
        elapsed = time.perf_counter_ns() - start
        all_latencies_ns.append(elapsed)
        per_case_latencies[case.name].append(elapsed)
        per_case_candidates[case.name] += len(candidates)
    total_elapsed_ns = time.perf_counter_ns() - total_start

    per_case_stats: list[QueryLatencyStats] = []
    for case in query_cases:
        case_latencies = per_case_latencies[case.name]
        if not case_latencies:
            continue
        per_case_stats.append(
            _stats_from_latencies(
                name=case.name,
                component_type=case.component_type,
                latencies_ns=case_latencies,
                total_candidates=per_case_candidates[case.name],
            )
        )

    qps = 0.0
    total_s = total_elapsed_ns / 1e9
    if total_s > 0:
        qps = iterations / total_s

    return BenchmarkSummary(
        db_path=str(db_path),
        rows_resistors=_count_rows(db_path, "resistor_pick"),
        rows_capacitors=_count_rows(db_path, "capacitor_pick"),
        iterations=iterations,
        warmup_iterations=warmup_iterations,
        total_time_s=total_s,
        qps=qps,
        overall=_stats_from_latencies(
            name="overall",
            component_type="resistor",
            latencies_ns=all_latencies_ns,
            total_candidates=sum(per_case_candidates.values()),
        ),
        per_case=sorted(per_case_stats, key=lambda stat: stat.p95_ms, reverse=True),
    )


def explain_query_plans(db_path: Path, cases: list[QueryCase]) -> dict[str, list[str]]:
    store = SQLiteFastLookupStore(db_path)
    out: dict[str, list[str]] = {}
    for case in cases:
        table = (
            "resistor_pick" if case.component_type == "resistor" else "capacitor_pick"
        )
        with store._connect() as conn:  # noqa: SLF001 - intentional for tuning tool
            columns = store._table_columns(conn, table)  # noqa: SLF001
            where, params = store._build_filters(  # noqa: SLF001
                component_type=case.component_type,
                query=case.query,
                columns=columns,
            )
            where_sql = f" where {' and '.join(where)}" if where else ""
            order_sql = store._build_order_sql(table, columns)  # noqa: SLF001
            sql = (
                "EXPLAIN QUERY PLAN "
                f"select * from {_quote_ident(table)}{where_sql}{order_sql} limit ?"
            )
            plan_rows = conn.execute(sql, [*params, case.query.limit]).fetchall()
        out[case.name] = [str(row[3]) for row in plan_rows]
    return out


def _execute_case(store: SQLiteFastLookupStore, case: QueryCase):
    if case.component_type == "resistor":
        return store.query_resistors(case.query)
    return store.query_capacitors(case.query)


def _weighted_case_list(cases: list[QueryCase]) -> list[QueryCase]:
    weighted: list[QueryCase] = []
    for case in cases:
        if case.weight < 1:
            raise ValueError(f"Case {case.name} has invalid weight {case.weight}")
        weighted.extend([case] * case.weight)
    return weighted


def _stats_from_latencies(
    *,
    name: str,
    component_type: ComponentKind,
    latencies_ns: list[int],
    total_candidates: int,
) -> QueryLatencyStats:
    sorted_ns = sorted(latencies_ns)
    runs = len(sorted_ns)
    return QueryLatencyStats(
        name=name,
        component_type=component_type,
        runs=runs,
        p50_ms=_percentile_ms(sorted_ns, 50),
        p90_ms=_percentile_ms(sorted_ns, 90),
        p95_ms=_percentile_ms(sorted_ns, 95),
        p99_ms=_percentile_ms(sorted_ns, 99),
        mean_ms=(sum(sorted_ns) / runs) / 1e6 if runs else 0.0,
        avg_candidates=(total_candidates / runs) if runs else 0.0,
    )


def _percentile_ms(sorted_ns: list[int], percentile: int) -> float:
    if not sorted_ns:
        return 0.0
    if percentile <= 0:
        return sorted_ns[0] / 1e6
    if percentile >= 100:
        return sorted_ns[-1] / 1e6
    rank = (len(sorted_ns) - 1) * (percentile / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_ns) - 1)
    frac = rank - lower
    value = sorted_ns[lower] * (1 - frac) + sorted_ns[upper] * frac
    return value / 1e6


def _count_rows(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(f"select count(*) from {_quote_ident(table)}").fetchone()
    return int(row[0]) if row else 0


def _weighted_pick(rng: random.Random, items: list[tuple[Any, int]]) -> Any:
    values = [item[0] for item in items]
    weights = [item[1] for item in items]
    return rng.choices(values, weights=weights, k=1)[0]


def _synth_stock(rng: random.Random) -> int:
    # Heavy tail: mostly moderate stock, some very large pools.
    base = int(rng.paretovariate(1.4) * 40)
    return min(max(base, 0), 2_000_000)


def _resistor_value_pool() -> dict[str, list[tuple[Any, int]]]:
    return {
        "package": [
            ("R0402", 26),
            ("R0603", 20),
            ("R0805", 12),
            ("0402", 20),
            ("0603", 14),
            ("0805", 8),
        ],
        "resistance_ohm": [
            (10.0, 4),
            (22.0, 4),
            (33.0, 4),
            (47.0, 4),
            (68.0, 4),
            (100.0, 8),
            (120.0, 6),
            (220.0, 7),
            (330.0, 7),
            (470.0, 7),
            (680.0, 7),
            (1_000.0, 20),
            (2_200.0, 10),
            (4_700.0, 10),
            (5_100.0, 16),
            (10_000.0, 38),
            (47_000.0, 9),
            (50_000.0, 7),
            (100_000.0, 8),
            (150_000.0, 5),
        ],
        "tolerance_pct": [
            (0.1, 1),
            (0.5, 4),
            (1.0, 24),
            (2.0, 6),
            (5.0, 20),
            (10.0, 8),
            (20.0, 10),
        ],
        "max_power_w": [
            (0.03125, 7),
            (0.0625, 30),
            (0.1, 6),
            (0.125, 10),
            (0.25, 8),
        ],
        "max_voltage_v": [
            (16.0, 3),
            (25.0, 12),
            (50.0, 28),
            (75.0, 6),
            (100.0, 6),
            (150.0, 2),
        ],
        "tempco_ppm": [
            (25.0, 2),
            (50.0, 6),
            (100.0, 30),
            (200.0, 8),
            (300.0, 4),
            (None, 6),
        ],
    }


def _capacitor_value_pool() -> dict[str, list[tuple[Any, int]]]:
    return {
        "package": [
            ("C0402", 28),
            ("C0603", 18),
            ("C0805", 10),
            ("0402", 20),
            ("0603", 14),
            ("0805", 8),
        ],
        "capacitance_f": [
            (22e-12, 4),
            (100e-12, 4),
            (1e-9, 6),
            (10e-9, 8),
            (100e-9, 36),
            (220e-9, 8),
            (470e-9, 8),
            (1e-6, 12),
            (2.2e-6, 24),
            (4.7e-6, 10),
            (10e-6, 7),
            (22e-6, 5),
            (100e-6, 3),
            (1000e-6, 1),
        ],
        "tolerance_pct": [
            (1.0, 2),
            (2.0, 4),
            (5.0, 18),
            (10.0, 20),
            (20.0, 30),
        ],
        "max_voltage_v": [
            (6.3, 12),
            (10.0, 16),
            (16.0, 24),
            (25.0, 18),
            (35.0, 8),
            (50.0, 6),
        ],
        "tempco_code": [
            ("X7R", 34),
            ("X5R", 28),
            ("C0G", 10),
            ("Y5V", 4),
            ("Z5U", 3),
            (None, 6),
        ],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark stage-3 fast lookup query latency and throughput."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help=(
            "Path to an existing fast.sqlite file. "
            "If omitted, synthetic DB is generated."
        ),
    )
    parser.add_argument(
        "--synthetic-db",
        type=Path,
        default=None,
        help="Optional output path for generated synthetic DB.",
    )
    parser.add_argument(
        "--resistor-rows",
        type=int,
        default=250_000,
        help="Synthetic resistor row count when --db is not provided.",
    )
    parser.add_argument(
        "--capacitor-rows",
        type=int,
        default=250_000,
        help="Synthetic capacitor row count when --db is not provided.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=50_000,
        help="Number of measured query iterations.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=5_000,
        help="Warmup query iterations before measurement.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="PRNG seed for workload and synthetic data.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write machine-readable benchmark summary JSON.",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Print EXPLAIN QUERY PLAN for each workload case.",
    )
    return parser.parse_args(argv)


def _print_summary(summary: BenchmarkSummary) -> None:
    print("")
    print("Lookup benchmark summary")
    print(f"  db: {summary.db_path}")
    print(
        "  rows: "
        f"resistor={summary.rows_resistors:,} "
        f"capacitor={summary.rows_capacitors:,}"
    )
    print(
        "  run: "
        f"iterations={summary.iterations:,} "
        f"warmup={summary.warmup_iterations:,} "
        f"time={summary.total_time_s:.3f}s "
        f"qps={summary.qps:,.1f}"
    )
    overall = summary.overall
    print(
        "  overall latency (ms): "
        f"p50={overall.p50_ms:.4f} "
        f"p95={overall.p95_ms:.4f} "
        f"p99={overall.p99_ms:.4f} "
        f"mean={overall.mean_ms:.4f}"
    )
    print("")
    print("Per-case latency (sorted by p95):")
    for case in summary.per_case:
        print(
            f"  {case.name:<22} "
            f"p50={case.p50_ms:.4f} "
            f"p95={case.p95_ms:.4f} "
            f"p99={case.p99_ms:.4f} "
            f"avg_candidates={case.avg_candidates:.2f} "
            f"n={case.runs}"
        )


def _json_ready(summary: BenchmarkSummary) -> dict[str, Any]:
    payload = asdict(summary)
    payload["per_case"] = [asdict(case) for case in summary.per_case]
    payload["overall"] = asdict(summary.overall)
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    cases = typical_query_cases()

    db_path: Path
    temp_db_context = None
    if args.db is not None:
        db_path = args.db
    else:
        if args.synthetic_db is None:
            temp_db_context = tempfile.TemporaryDirectory(prefix="atopile-fast-bench-")
            db_path = Path(temp_db_context.name) / "fast.synthetic.sqlite"
        else:
            db_path = args.synthetic_db
        build_synthetic_fast_db(
            db_path,
            resistor_rows=args.resistor_rows,
            capacitor_rows=args.capacitor_rows,
            seed=args.seed,
        )

    summary = run_lookup_benchmark(
        db_path=db_path,
        iterations=args.iterations,
        warmup_iterations=args.warmup,
        cases=cases,
        seed=args.seed,
    )
    _print_summary(summary)

    if args.explain:
        print("")
        print("EXPLAIN QUERY PLAN:")
        plans = explain_query_plans(db_path, cases)
        for case_name in [case.name for case in cases]:
            print(f"  {case_name}:")
            for line in plans[case_name]:
                print(f"    - {line}")

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(_json_ready(summary), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        print("")
        print(f"Wrote JSON summary to {args.json_out}")

    if temp_db_context is not None:
        temp_db_context.cleanup()
    return 0


def test_typical_query_cases_cover_resistor_and_capacitor() -> None:
    cases = typical_query_cases()
    types = {case.component_type for case in cases}
    assert "resistor" in types
    assert "capacitor" in types
    assert all(case.weight > 0 for case in cases)


def test_synthetic_db_benchmark_smoke(tmp_path) -> None:
    db_path = tmp_path / "fast.synthetic.sqlite"
    build_synthetic_fast_db(
        db_path,
        resistor_rows=2_000,
        capacitor_rows=2_000,
        seed=7,
    )
    summary = run_lookup_benchmark(
        db_path=db_path,
        iterations=1_000,
        warmup_iterations=100,
        seed=7,
    )
    assert summary.rows_resistors == 2_000
    assert summary.rows_capacitors == 2_000
    assert summary.iterations == 1_000
    assert summary.qps > 0
    assert summary.overall.p95_ms >= 0
    assert summary.per_case


def test_explain_query_plans_smoke(tmp_path) -> None:
    db_path = tmp_path / "fast.synthetic.sqlite"
    build_synthetic_fast_db(
        db_path,
        resistor_rows=1_000,
        capacitor_rows=1_000,
        seed=11,
    )
    cases = typical_query_cases()[:3]
    plans = explain_query_plans(db_path, cases)
    assert set(plans) == {case.name for case in cases}
    assert all(plans[case.name] for case in cases)


if __name__ == "__main__":
    raise SystemExit(main())
