from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import ComponentSink, NormalizedComponent


class FastLookupDbBuilder(ComponentSink):
    def __init__(self, db_path: Path, *, batch_size: int = 5000):
        self.db_path = db_path
        self.batch_size = batch_size
        self._conn = sqlite3.connect(db_path)
        self._resistor_rows: list[tuple] = []
        self._capacitor_rows: list[tuple] = []
        self.inserted_count = 0
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript(
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
            """
        )

    def add_component(self, component: NormalizedComponent) -> None:
        if component.component_type == "resistor":
            if component.resistance_ohm is None:
                return
            self._resistor_rows.append(
                (
                    component.lcsc_id,
                    component.package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.resistance_ohm,
                    component.resistance_min_ohm,
                    component.resistance_max_ohm,
                    component.tolerance_pct,
                    component.max_power_w,
                    component.max_voltage_v,
                    component.resistor_tempco_ppm,
                )
            )
            if len(self._resistor_rows) >= self.batch_size:
                self._flush_resistor_rows()
            return

        if component.component_type == "capacitor":
            if component.capacitance_f is None:
                return
            self._capacitor_rows.append(
                (
                    component.lcsc_id,
                    component.package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.capacitance_f,
                    component.capacitance_min_f,
                    component.capacitance_max_f,
                    component.tolerance_pct,
                    component.max_voltage_v,
                    component.capacitor_tempco_code,
                )
            )
            if len(self._capacitor_rows) >= self.batch_size:
                self._flush_capacitor_rows()

    def _flush_resistor_rows(self) -> None:
        if not self._resistor_rows:
            return
        self._conn.executemany(
            """
            INSERT INTO resistor_pick (
                lcsc_id,
                package,
                stock,
                is_basic,
                is_preferred,
                resistance_ohm,
                resistance_min_ohm,
                resistance_max_ohm,
                tolerance_pct,
                max_power_w,
                max_voltage_v,
                tempco_ppm
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._resistor_rows,
        )
        self.inserted_count += len(self._resistor_rows)
        self._resistor_rows.clear()

    def _flush_capacitor_rows(self) -> None:
        if not self._capacitor_rows:
            return
        self._conn.executemany(
            """
            INSERT INTO capacitor_pick (
                lcsc_id,
                package,
                stock,
                is_basic,
                is_preferred,
                capacitance_f,
                capacitance_min_f,
                capacitance_max_f,
                tolerance_pct,
                max_voltage_v,
                tempco_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._capacitor_rows,
        )
        self.inserted_count += len(self._capacitor_rows)
        self._capacitor_rows.clear()

    def finalize(self) -> None:
        self._flush_resistor_rows()
        self._flush_capacitor_rows()
        self._conn.executescript(
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
        self._conn.commit()
        self._conn.close()


def test_fast_lookup_db_builder(tmp_path) -> None:
    db_path = tmp_path / "fast.sqlite"
    builder = FastLookupDbBuilder(db_path, batch_size=1)
    builder.add_component(
        NormalizedComponent(
            lcsc_id=1,
            component_type="resistor",
            category="Resistors",
            subcategory="Chip Resistor - Surface Mount",
            manufacturer_name="M",
            part_number="R1",
            package="0402",
            description="d",
            is_basic=True,
            is_preferred=False,
            stock=100,
            datasheet_url=None,
            price_json="[]",
            attributes_json="{}",
            extra_json="{}",
            resistance_ohm=10_000.0,
            resistance_min_ohm=9_900.0,
            resistance_max_ohm=10_100.0,
            capacitance_f=None,
            capacitance_min_f=None,
            capacitance_max_f=None,
            tolerance_pct=1.0,
            max_power_w=0.0625,
            max_voltage_v=50.0,
            resistor_tempco_ppm=100.0,
            capacitor_tempco_code=None,
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
        )
    )
    builder.add_component(
        NormalizedComponent(
            lcsc_id=2,
            component_type="capacitor",
            category="Capacitors",
            subcategory="Multilayer Ceramic Capacitors MLCC - SMD/SMT",
            manufacturer_name="M",
            part_number="C1",
            package="0402",
            description="d",
            is_basic=False,
            is_preferred=True,
            stock=200,
            datasheet_url=None,
            price_json="[]",
            attributes_json="{}",
            extra_json="{}",
            resistance_ohm=None,
            resistance_min_ohm=None,
            resistance_max_ohm=None,
            capacitance_f=1e-7,
            capacitance_min_f=0.9e-7,
            capacitance_max_f=1.1e-7,
            tolerance_pct=10.0,
            max_power_w=None,
            max_voltage_v=16.0,
            resistor_tempco_ppm=None,
            capacitor_tempco_code="X7R",
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
        )
    )
    builder.finalize()

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM resistor_pick").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM capacitor_pick").fetchone()[0] == 1
    index_names = {
        row[1] for row in conn.execute("PRAGMA index_list('resistor_pick')").fetchall()
    }
    assert "resistor_pick_lookup_pkg_idx" in index_names
    conn.close()
