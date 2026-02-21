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
    capacitor_polarized_rows: int
    inductor_rows: int
    diode_rows: int
    led_rows: int
    bjt_rows: int
    mosfet_rows: int
    crystal_rows: int
    ferrite_bead_rows: int
    ldo_rows: int


_FAST_TABLES_BY_TYPE = {
    "resistor": "resistor_pick",
    "capacitor": "capacitor_pick",
    "capacitor_polarized": "capacitor_polarized_pick",
    "inductor": "inductor_pick",
    "diode": "diode_pick",
    "led": "led_pick",
    "bjt": "bjt_pick",
    "mosfet": "mosfet_pick",
    "crystal": "crystal_pick",
    "ferrite_bead": "ferrite_bead_pick",
    "ldo": "ldo_pick",
}

_REQUIRED_INDEXES_BY_TABLE = {
    "resistor_pick": {"resistor_pick_lookup_pkg_idx", "resistor_pick_lookup_range_idx"},
    "capacitor_pick": {
        "capacitor_pick_lookup_pkg_idx",
        "capacitor_pick_lookup_range_idx",
    },
    "capacitor_polarized_pick": {
        "capacitor_polarized_pick_lookup_pkg_idx",
        "capacitor_polarized_pick_lookup_range_idx",
    },
    "inductor_pick": {"inductor_pick_lookup_pkg_idx", "inductor_pick_lookup_range_idx"},
    "diode_pick": {"diode_pick_lookup_pkg_idx"},
    "led_pick": {"led_pick_lookup_pkg_idx"},
    "bjt_pick": {"bjt_pick_lookup_pkg_idx"},
    "mosfet_pick": {"mosfet_pick_lookup_pkg_idx"},
    "crystal_pick": {"crystal_pick_lookup_pkg_idx", "crystal_pick_lookup_range_idx"},
    "ferrite_bead_pick": {"ferrite_bead_pick_lookup_pkg_idx"},
    "ldo_pick": {"ldo_pick_lookup_pkg_idx"},
}


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
        row_counts = {
            component_type: int(
                conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            )
            for component_type, table_name in _FAST_TABLES_BY_TYPE.items()
        }
        _validate_fast_pickability(conn)

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
                f"components_full={detail_rows} "
                f"component_assets_distinct_lcsc={asset_component_rows}"
            )

    return SnapshotValidationResult(
        snapshot_dir=snapshot_dir,
        fast_total_rows=sum(row_counts.values()),
        detail_total_rows=detail_rows,
        resistor_rows=row_counts["resistor"],
        capacitor_rows=row_counts["capacitor"],
        capacitor_polarized_rows=row_counts["capacitor_polarized"],
        inductor_rows=row_counts["inductor"],
        diode_rows=row_counts["diode"],
        led_rows=row_counts["led"],
        bjt_rows=row_counts["bjt"],
        mosfet_rows=row_counts["mosfet"],
        crystal_rows=row_counts["crystal"],
        ferrite_bead_rows=row_counts["ferrite_bead"],
        ldo_rows=row_counts["ldo"],
    )


def _validate_fast_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required_tables = set(_FAST_TABLES_BY_TYPE.values())
        if not required_tables.issubset(tables):
            missing = sorted(required_tables - tables)
            raise RuntimeError(f"Missing fast tables in {db_path}: {missing}")

        for table_name, required_indexes in _REQUIRED_INDEXES_BY_TABLE.items():
            index_names = _index_names(conn, table_name)
            if not required_indexes.issubset(index_names):
                missing = sorted(required_indexes - index_names)
                raise RuntimeError(
                    f"Missing indexes for {table_name} in {db_path}: {missing}"
                )


def _validate_fast_pickability(conn: sqlite3.Connection) -> None:
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
    bad_cap_pol_bounds = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM capacitor_polarized_pick
            WHERE capacitance_min_f > capacitance_f
               OR capacitance_f > capacitance_max_f
            """
        ).fetchone()[0]
    )
    bad_ind_bounds = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM inductor_pick
            WHERE inductance_min_h > inductance_h
               OR inductance_h > inductance_max_h
            """
        ).fetchone()[0]
    )
    bad_crystal_bounds = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM crystal_pick
            WHERE frequency_min_hz > frequency_hz
               OR frequency_hz > frequency_max_hz
            """
        ).fetchone()[0]
    )
    if bad_res_bounds:
        raise RuntimeError(
            f"Invalid resistor bounds in fast snapshot: {bad_res_bounds}"
        )
    if bad_cap_bounds:
        raise RuntimeError(
            f"Invalid capacitor bounds in fast snapshot: {bad_cap_bounds}"
        )
    if bad_cap_pol_bounds:
        raise RuntimeError(
            f"Invalid polarized capacitor bounds in fast snapshot: {bad_cap_pol_bounds}"
        )
    if bad_ind_bounds:
        raise RuntimeError(
            f"Invalid inductor bounds in fast snapshot: {bad_ind_bounds}"
        )
    if bad_crystal_bounds:
        raise RuntimeError(
            f"Invalid crystal bounds in fast snapshot: {bad_crystal_bounds}"
        )

    checks: list[tuple[str, str]] = [
        (
            "resistor",
            """
            SELECT COUNT(*) FROM resistor_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR tolerance_pct IS NULL
               OR max_power_w IS NULL OR max_power_w <= 0
               OR max_voltage_v IS NULL OR max_voltage_v <= 0
            """,
        ),
        (
            "capacitor",
            """
            SELECT COUNT(*) FROM capacitor_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR tolerance_pct IS NULL
               OR max_voltage_v IS NULL OR max_voltage_v <= 0
            """,
        ),
        (
            "capacitor_polarized",
            """
            SELECT COUNT(*) FROM capacitor_polarized_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR tolerance_pct IS NULL
               OR max_voltage_v IS NULL OR max_voltage_v <= 0
            """,
        ),
        (
            "inductor",
            """
            SELECT COUNT(*) FROM inductor_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR max_current_a IS NULL OR max_current_a <= 0
               OR dc_resistance_ohm IS NULL OR dc_resistance_ohm < 0
            """,
        ),
        (
            "diode",
            """
            SELECT COUNT(*) FROM diode_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR forward_voltage_v IS NULL OR forward_voltage_v <= 0
               OR reverse_working_voltage_v IS NULL OR reverse_working_voltage_v <= 0
               OR max_current_a IS NULL OR max_current_a <= 0
            """,
        ),
        (
            "led",
            """
            SELECT COUNT(*) FROM led_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR trim(color_code) = ''
               OR forward_voltage_v IS NULL OR forward_voltage_v <= 0
               OR max_current_a IS NULL OR max_current_a <= 0
            """,
        ),
        (
            "bjt",
            """
            SELECT COUNT(*) FROM bjt_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR doping_type NOT IN ('NPN', 'PNP')
               OR max_collector_emitter_voltage_v IS NULL
               OR max_collector_emitter_voltage_v <= 0
               OR max_collector_current_a IS NULL OR max_collector_current_a <= 0
               OR max_power_w IS NULL OR max_power_w <= 0
            """,
        ),
        (
            "mosfet",
            """
            SELECT COUNT(*) FROM mosfet_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR channel_type NOT IN ('N_CHANNEL', 'P_CHANNEL')
               OR max_drain_source_voltage_v IS NULL OR max_drain_source_voltage_v <= 0
               OR max_continuous_drain_current_a IS NULL
               OR max_continuous_drain_current_a <= 0
               OR on_resistance_ohm IS NULL OR on_resistance_ohm <= 0
            """,
        ),
        (
            "crystal",
            """
            SELECT COUNT(*) FROM crystal_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR frequency_hz IS NULL OR frequency_hz <= 0
               OR frequency_min_hz IS NULL OR frequency_max_hz IS NULL
               OR frequency_tolerance_ppm IS NULL OR frequency_tolerance_ppm < 0
               OR load_capacitance_f IS NULL OR load_capacitance_f <= 0
            """,
        ),
        (
            "ferrite_bead",
            """
            SELECT COUNT(*) FROM ferrite_bead_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR impedance_ohm IS NULL OR impedance_ohm <= 0
               OR current_rating_a IS NULL OR current_rating_a <= 0
               OR dc_resistance_ohm IS NULL OR dc_resistance_ohm < 0
            """,
        ),
        (
            "ldo",
            """
            SELECT COUNT(*) FROM ldo_pick
            WHERE stock <= 0
               OR trim(package) IN ('', '-')
               OR output_voltage_v IS NULL OR output_voltage_v <= 0
               OR max_input_voltage_v IS NULL OR max_input_voltage_v <= 0
               OR output_current_a IS NULL OR output_current_a <= 0
               OR dropout_voltage_v IS NULL OR dropout_voltage_v <= 0
            """,
        ),
    ]
    for component_type, sql in checks:
        bad_rows = int(conn.execute(sql).fetchone()[0])
        if bad_rows:
            raise RuntimeError(
                f"Non-pickable {component_type} rows found in fast snapshot: {bad_rows}"
            )


def _validate_detail_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required_tables = {
            "components_full",
            "component_assets",
            "component_mfr_lookup",
        }
        if not required_tables.issubset(tables):
            missing = sorted(required_tables - tables)
            raise RuntimeError(f"Missing detail tables in {db_path}: {missing}")
        index_names = _index_names(conn, "component_mfr_lookup")
        if "component_mfr_lookup_match_idx" not in index_names:
            raise RuntimeError(
                "Missing indexes for component_mfr_lookup "
                f"in {db_path}: ['component_mfr_lookup_match_idx']"
            )


def _index_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1] for row in conn.execute(f"PRAGMA index_list('{table_name}')").fetchall()
    }


def test_validate_snapshot(tmp_path) -> None:
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir(parents=True)
    fast_db = snapshot_dir / "fast.sqlite"
    detail_db = snapshot_dir / "detail.sqlite"
    _write_valid_fast_db(fast_db)
    _write_valid_detail_db(detail_db)

    result = validate_snapshot(snapshot_dir)
    assert result.fast_total_rows == 11
    assert result.detail_total_rows == 11


def test_validate_snapshot_rejects_non_pickable_fast_rows(tmp_path) -> None:
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir(parents=True)
    fast_db = snapshot_dir / "fast.sqlite"
    detail_db = snapshot_dir / "detail.sqlite"
    _write_valid_fast_db(fast_db)
    _write_valid_detail_db(detail_db)
    with sqlite3.connect(fast_db) as conn:
        conn.execute(
            "UPDATE mosfet_pick SET channel_type = 'INVALID' WHERE lcsc_id = 8"
        )
        conn.commit()

    try:
        validate_snapshot(snapshot_dir)
    except RuntimeError as exc:
        assert "Non-pickable mosfet rows" in str(exc)
    else:
        assert False, "Expected RuntimeError"


def _write_valid_fast_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
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
            CREATE TABLE capacitor_polarized_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                capacitance_f REAL NOT NULL,
                capacitance_min_f REAL NOT NULL,
                capacitance_max_f REAL NOT NULL,
                tolerance_pct REAL,
                max_voltage_v REAL
            );
            CREATE TABLE inductor_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                inductance_h REAL NOT NULL,
                inductance_min_h REAL NOT NULL,
                inductance_max_h REAL NOT NULL,
                tolerance_pct REAL,
                max_current_a REAL NOT NULL,
                dc_resistance_ohm REAL NOT NULL,
                saturation_current_a REAL,
                self_resonant_frequency_hz REAL
            );
            CREATE TABLE diode_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                forward_voltage_v REAL NOT NULL,
                reverse_working_voltage_v REAL NOT NULL,
                max_current_a REAL NOT NULL,
                reverse_leakage_current_a REAL
            );
            CREATE TABLE led_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                color_code TEXT NOT NULL,
                forward_voltage_v REAL NOT NULL,
                max_current_a REAL NOT NULL,
                max_brightness_cd REAL
            );
            CREATE TABLE bjt_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                doping_type TEXT NOT NULL,
                max_collector_emitter_voltage_v REAL NOT NULL,
                max_collector_current_a REAL NOT NULL,
                max_power_w REAL NOT NULL,
                dc_current_gain_hfe REAL
            );
            CREATE TABLE mosfet_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                channel_type TEXT NOT NULL,
                max_drain_source_voltage_v REAL NOT NULL,
                max_continuous_drain_current_a REAL NOT NULL,
                on_resistance_ohm REAL NOT NULL,
                gate_source_threshold_voltage_v REAL
            );
            CREATE TABLE crystal_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                frequency_hz REAL NOT NULL,
                frequency_min_hz REAL NOT NULL,
                frequency_max_hz REAL NOT NULL,
                load_capacitance_f REAL NOT NULL,
                frequency_tolerance_ppm REAL NOT NULL,
                frequency_stability_ppm REAL
            );
            CREATE TABLE ferrite_bead_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                impedance_ohm REAL NOT NULL,
                current_rating_a REAL NOT NULL,
                dc_resistance_ohm REAL NOT NULL
            );
            CREATE TABLE ldo_pick (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                package TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                output_voltage_v REAL NOT NULL,
                max_input_voltage_v REAL NOT NULL,
                output_current_a REAL NOT NULL,
                dropout_voltage_v REAL NOT NULL,
                output_type TEXT,
                output_polarity TEXT
            );

            CREATE INDEX resistor_pick_lookup_pkg_idx
                ON resistor_pick(package, resistance_min_ohm, resistance_max_ohm);
            CREATE INDEX resistor_pick_lookup_range_idx
                ON resistor_pick(resistance_min_ohm, resistance_max_ohm);
            CREATE INDEX capacitor_pick_lookup_pkg_idx
                ON capacitor_pick(package, capacitance_min_f, capacitance_max_f);
            CREATE INDEX capacitor_pick_lookup_range_idx
                ON capacitor_pick(capacitance_min_f, capacitance_max_f);
            CREATE INDEX capacitor_polarized_pick_lookup_pkg_idx
                ON capacitor_polarized_pick(
                    package,
                    capacitance_min_f,
                    capacitance_max_f
                );
            CREATE INDEX capacitor_polarized_pick_lookup_range_idx
                ON capacitor_polarized_pick(capacitance_min_f, capacitance_max_f);
            CREATE INDEX inductor_pick_lookup_pkg_idx
                ON inductor_pick(package, inductance_min_h, inductance_max_h);
            CREATE INDEX inductor_pick_lookup_range_idx
                ON inductor_pick(inductance_min_h, inductance_max_h);
            CREATE INDEX diode_pick_lookup_pkg_idx
                ON diode_pick(package, forward_voltage_v);
            CREATE INDEX led_pick_lookup_pkg_idx
                ON led_pick(package, color_code);
            CREATE INDEX bjt_pick_lookup_pkg_idx
                ON bjt_pick(package, doping_type);
            CREATE INDEX mosfet_pick_lookup_pkg_idx
                ON mosfet_pick(package, channel_type);
            CREATE INDEX crystal_pick_lookup_pkg_idx
                ON crystal_pick(package, frequency_min_hz, frequency_max_hz);
            CREATE INDEX crystal_pick_lookup_range_idx
                ON crystal_pick(frequency_min_hz, frequency_max_hz);
            CREATE INDEX ferrite_bead_pick_lookup_pkg_idx
                ON ferrite_bead_pick(package, impedance_ohm);
            CREATE INDEX ldo_pick_lookup_pkg_idx
                ON ldo_pick(package, output_type, output_voltage_v);
            """
        )
        conn.executescript(
            """
            INSERT INTO resistor_pick VALUES
                (1,'0402',10,1,0,10000.0,9900.0,10100.0,1.0,0.0625,50.0,100.0);
            INSERT INTO capacitor_pick VALUES
                (2,'0402',20,0,1,1e-7,0.9e-7,1.1e-7,10.0,16.0,'X7R');
            INSERT INTO capacitor_polarized_pick VALUES
                (3,'C_CASE',20,0,1,1e-5,0.8e-5,1.2e-5,20.0,25.0);
            INSERT INTO inductor_pick VALUES
                (4,'0805',50,1,1,1e-5,0.9e-5,1.1e-5,10.0,1.5,0.05,2.0,1e8);
            INSERT INTO diode_pick VALUES
                (5,'SOD-123',100,1,0,0.75,100.0,0.3,2e-6);
            INSERT INTO led_pick VALUES
                (6,'0603',100,0,1,'RED',2.1,0.02,0.5);
            INSERT INTO bjt_pick VALUES
                (7,'SOT-23',100,0,1,'NPN',40.0,0.2,0.35,120.0);
            INSERT INTO mosfet_pick VALUES
                (8,'SOT-23',100,0,1,'N_CHANNEL',30.0,2.0,0.05,1.8);
            INSERT INTO crystal_pick VALUES
                (9,'SMD-3225',100,1,1,16000000.0,15999680.0,16000320.0,18e-12,20.0,30.0);
            INSERT INTO ferrite_bead_pick VALUES
                (10,'0603',100,0,1,120.0,2.0,0.05);
            INSERT INTO ldo_pick VALUES
                (11,'SOT-23-5',100,1,0,3.3,6.0,0.15,0.3,'FIXED','POSITIVE');
            """
        )
        conn.commit()


def _write_valid_detail_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE components_full (lcsc_id INTEGER PRIMARY KEY NOT NULL);
            CREATE TABLE component_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lcsc_id INTEGER NOT NULL
            );
            CREATE TABLE component_mfr_lookup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mfr_norm TEXT NOT NULL,
                part_number_norm TEXT NOT NULL,
                lcsc_id INTEGER NOT NULL
            );
            CREATE INDEX component_mfr_lookup_match_idx
                ON component_mfr_lookup (mfr_norm, part_number_norm, lcsc_id);
            """
        )
        for lcsc_id in range(1, 12):
            conn.execute(
                "INSERT INTO components_full (lcsc_id) VALUES (?)",
                (lcsc_id,),
            )
            conn.execute(
                "INSERT INTO component_assets (lcsc_id) VALUES (?)",
                (lcsc_id,),
            )
            conn.execute(
                """
                INSERT INTO component_mfr_lookup (
                    mfr_norm,
                    part_number_norm,
                    lcsc_id
                ) VALUES (?, ?, ?)
                """,
                ("m", f"p{lcsc_id}", lcsc_id),
            )
        conn.commit()


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
