from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SnapshotValidationResult:
    snapshot_dir: Path
    fast_total_rows: int
    detail_total_rows: int
    resistor_rows: int
    capacitor_rows: int


def validate_snapshot(snapshot_dir: Path) -> SnapshotValidationResult:
    fast_db = snapshot_dir / "fast.sqlite"
    detail_db = snapshot_dir / "detail.sqlite"
    if not fast_db.exists():
        raise FileNotFoundError(f"Missing fast.sqlite in snapshot: {snapshot_dir}")
    if not detail_db.exists():
        raise FileNotFoundError(f"Missing detail.sqlite in snapshot: {snapshot_dir}")

    _validate_fast_schema(fast_db)
    _validate_detail_schema(detail_db)

    with sqlite3.connect(fast_db) as conn:
        resistor_rows = int(
            conn.execute("SELECT COUNT(*) FROM resistor_pick").fetchone()[0]
        )
        capacitor_rows = int(
            conn.execute("SELECT COUNT(*) FROM capacitor_pick").fetchone()[0]
        )
        # Validate range column integrity for solver range queries.
        bad_res_bounds = int(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM resistor_pick
                WHERE resistance_min_ohm > resistance_ohm
                   OR resistance_ohm > resistance_max_ohm
                """
            ).fetchone()[0]
        )
        bad_cap_bounds = int(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM capacitor_pick
                WHERE capacitance_min_f > capacitance_f
                   OR capacitance_f > capacitance_max_f
                """
            ).fetchone()[0]
        )
        if bad_res_bounds:
            raise RuntimeError(
                "Invalid resistor bounds found in snapshot "
                f"{snapshot_dir}: {bad_res_bounds}"
            )
        if bad_cap_bounds:
            raise RuntimeError(
                "Invalid capacitor bounds found in snapshot "
                f"{snapshot_dir}: {bad_cap_bounds}"
            )

    with sqlite3.connect(detail_db) as conn:
        detail_rows = int(
            conn.execute("SELECT COUNT(*) FROM components_full").fetchone()[0]
        )
        asset_component_rows = int(
            conn.execute(
                "SELECT COUNT(DISTINCT lcsc_id) FROM component_assets"
            ).fetchone()[0]
        )
        if detail_rows != asset_component_rows:
            raise RuntimeError(
                f"Detail/components asset coverage mismatch in {snapshot_dir}: "
                "components_full="
                f"{detail_rows} "
                "component_assets_distinct_lcsc="
                f"{asset_component_rows}"
            )

    return SnapshotValidationResult(
        snapshot_dir=snapshot_dir,
        fast_total_rows=resistor_rows + capacitor_rows,
        detail_total_rows=detail_rows,
        resistor_rows=resistor_rows,
        capacitor_rows=capacitor_rows,
    )


def _validate_fast_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required_tables = {"resistor_pick", "capacitor_pick"}
        if not required_tables.issubset(tables):
            missing = sorted(required_tables - tables)
            raise RuntimeError(f"Missing fast tables in {db_path}: {missing}")

        resistor_indexes = _index_names(conn, "resistor_pick")
        capacitor_indexes = _index_names(conn, "capacitor_pick")
        required_resistor_indexes = {
            "resistor_pick_lookup_pkg_idx",
            "resistor_pick_lookup_range_idx",
        }
        required_capacitor_indexes = {
            "capacitor_pick_lookup_pkg_idx",
            "capacitor_pick_lookup_range_idx",
        }
        if not required_resistor_indexes.issubset(resistor_indexes):
            missing = sorted(required_resistor_indexes - resistor_indexes)
            raise RuntimeError(f"Missing resistor indexes in {db_path}: {missing}")
        if not required_capacitor_indexes.issubset(capacitor_indexes):
            missing = sorted(required_capacitor_indexes - capacitor_indexes)
            raise RuntimeError(f"Missing capacitor indexes in {db_path}: {missing}")


def _validate_detail_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required_tables = {"components_full", "component_assets"}
        if not required_tables.issubset(tables):
            missing = sorted(required_tables - tables)
            raise RuntimeError(f"Missing detail tables in {db_path}: {missing}")


def _index_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1] for row in conn.execute(f"PRAGMA index_list('{table_name}')").fetchall()
    }


def test_validate_snapshot(tmp_path) -> None:
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir(parents=True)
    fast_db = snapshot_dir / "fast.sqlite"
    detail_db = snapshot_dir / "detail.sqlite"

    with sqlite3.connect(fast_db) as conn:
        conn.executescript(
            """
            CREATE TABLE resistor_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                resistance_ohm REAL NOT NULL,
                resistance_min_ohm REAL NOT NULL,
                resistance_max_ohm REAL NOT NULL,
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
                capacitance_min_f REAL NOT NULL,
                capacitance_max_f REAL NOT NULL,
                tolerance_pct REAL,
                max_voltage_v REAL,
                tempco_code TEXT
            );
            CREATE INDEX resistor_pick_lookup_pkg_idx
                ON resistor_pick(package, resistance_min_ohm, resistance_max_ohm);
            CREATE INDEX resistor_pick_lookup_range_idx
                ON resistor_pick(resistance_min_ohm, resistance_max_ohm);
            CREATE INDEX capacitor_pick_lookup_pkg_idx
                ON capacitor_pick(package, capacitance_min_f, capacitance_max_f);
            CREATE INDEX capacitor_pick_lookup_range_idx
                ON capacitor_pick(capacitance_min_f, capacitance_max_f);
            """
        )
        conn.execute(
            """
            INSERT INTO resistor_pick VALUES
            (1,'0402',10,1,0,10000.0,9900.0,10100.0,1.0,0.0625,50.0,100.0)
            """
        )
        conn.execute(
            """
            INSERT INTO capacitor_pick VALUES
            (2,'0402',20,0,1,1e-7,0.9e-7,1.1e-7,10.0,16.0,'X7R')
            """
        )
        conn.commit()

    with sqlite3.connect(detail_db) as conn:
        conn.executescript(
            """
            CREATE TABLE components_full (lcsc_id INTEGER PRIMARY KEY NOT NULL);
            CREATE TABLE component_assets (lcsc_id INTEGER PRIMARY KEY NOT NULL);
            """
        )
        conn.execute("INSERT INTO components_full VALUES (1)")
        conn.execute("INSERT INTO components_full VALUES (2)")
        conn.execute("INSERT INTO component_assets VALUES (1)")
        conn.execute("INSERT INTO component_assets VALUES (2)")
        conn.commit()

    result = validate_snapshot(snapshot_dir)
    assert result.fast_total_rows == 2
    assert result.detail_total_rows == 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a built stage-2 snapshot directory."
    )
    parser.add_argument("snapshot_dir", type=Path)
    args = parser.parse_args(argv)

    result = validate_snapshot(args.snapshot_dir)
    print(
        f"{result.snapshot_dir} "
        f"fast_rows={result.fast_total_rows} "
        f"detail_rows={result.detail_total_rows}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
