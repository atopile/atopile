from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import ComponentSink, NormalizedComponent


class DetailDbBuilder(ComponentSink):
    def __init__(
        self,
        db_path: Path,
        *,
        batch_size: int = 5000,
        stage1_assets_by_lcsc: dict[int, list[dict[str, Any]]] | None = None,
    ):
        self.db_path = db_path
        self.batch_size = batch_size
        self.stage1_assets_by_lcsc = stage1_assets_by_lcsc or {}
        self._conn = sqlite3.connect(db_path)
        self._component_rows: list[tuple] = []
        self._asset_rows: list[tuple] = []
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

            CREATE TABLE components_full (
                lcsc_id INTEGER PRIMARY KEY NOT NULL,
                component_type TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                manufacturer_name TEXT,
                part_number TEXT NOT NULL,
                package TEXT NOT NULL,
                description TEXT NOT NULL,
                stock INTEGER NOT NULL,
                is_basic INTEGER NOT NULL,
                is_preferred INTEGER NOT NULL,
                datasheet_url TEXT,
                price_json TEXT NOT NULL,
                attributes_json TEXT NOT NULL,
                extra_json TEXT,
                resistance_ohm REAL,
                resistance_min_ohm REAL,
                resistance_max_ohm REAL,
                capacitance_f REAL,
                capacitance_min_f REAL,
                capacitance_max_f REAL,
                tolerance_pct REAL,
                max_power_w REAL,
                max_voltage_v REAL,
                resistor_tempco_ppm REAL,
                capacitor_tempco_code TEXT,
                inductance_h REAL,
                inductance_min_h REAL,
                inductance_max_h REAL,
                max_current_a REAL,
                dc_resistance_ohm REAL,
                saturation_current_a REAL,
                self_resonant_frequency_hz REAL,
                forward_voltage_v REAL,
                reverse_working_voltage_v REAL,
                reverse_leakage_current_a REAL,
                led_color_code TEXT,
                max_brightness_cd REAL,
                bjt_doping_type TEXT,
                max_collector_emitter_voltage_v REAL,
                max_collector_current_a REAL,
                dc_current_gain_hfe REAL,
                mosfet_channel_type TEXT,
                gate_source_threshold_voltage_v REAL,
                max_drain_source_voltage_v REAL,
                max_continuous_drain_current_a REAL,
                on_resistance_ohm REAL
            );

            CREATE TABLE component_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lcsc_id INTEGER NOT NULL,
                artifact_type TEXT,
                stored_key TEXT,
                encoding TEXT,
                mime TEXT,
                raw_sha256 TEXT,
                raw_size_bytes INTEGER,
                source_url TEXT,
                source_meta_json TEXT,
                datasheet_url TEXT,
                data_manual_url TEXT,
                footprint_name TEXT,
                model_3d_path TEXT,
                easyeda_model_uuid TEXT,
                FOREIGN KEY(lcsc_id) REFERENCES components_full(lcsc_id)
            );
            """
        )

    def add_component(self, component: NormalizedComponent) -> None:
        self._component_rows.append(
            (
                component.lcsc_id,
                component.component_type,
                component.category,
                component.subcategory,
                component.manufacturer_name,
                component.part_number,
                component.package,
                component.description,
                component.stock,
                int(component.is_basic),
                int(component.is_preferred),
                component.datasheet_url,
                component.price_json,
                component.attributes_json,
                component.extra_json,
                component.resistance_ohm,
                component.resistance_min_ohm,
                component.resistance_max_ohm,
                component.capacitance_f,
                component.capacitance_min_f,
                component.capacitance_max_f,
                component.tolerance_pct,
                component.max_power_w,
                component.max_voltage_v,
                component.resistor_tempco_ppm,
                component.capacitor_tempco_code,
                component.inductance_h,
                component.inductance_min_h,
                component.inductance_max_h,
                component.max_current_a,
                component.dc_resistance_ohm,
                component.saturation_current_a,
                component.self_resonant_frequency_hz,
                component.forward_voltage_v,
                component.reverse_working_voltage_v,
                component.reverse_leakage_current_a,
                component.led_color_code,
                component.max_brightness_cd,
                component.bjt_doping_type,
                component.max_collector_emitter_voltage_v,
                component.max_collector_current_a,
                component.dc_current_gain_hfe,
                component.mosfet_channel_type,
                component.gate_source_threshold_voltage_v,
                component.max_drain_source_voltage_v,
                component.max_continuous_drain_current_a,
                component.on_resistance_ohm,
            )
        )
        self._asset_rows.append(
            (
                component.lcsc_id,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                component.datasheet_url,
                component.data_manual_url,
                component.footprint_name,
                component.model_3d_path,
                component.easyeda_model_uuid,
            )
        )
        for asset in self.stage1_assets_by_lcsc.get(component.lcsc_id, []):
            self._asset_rows.append(
                (
                    component.lcsc_id,
                    asset["artifact_type"],
                    asset["stored_key"],
                    asset["encoding"],
                    asset["mime"],
                    asset["raw_sha256"],
                    asset["raw_size_bytes"],
                    asset["source_url"],
                    json.dumps(
                        asset["source_meta"],
                        ensure_ascii=True,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    None,
                    None,
                    None,
                    None,
                    None,
                )
            )

        if len(self._component_rows) >= self.batch_size:
            self._flush_rows()

    def _flush_rows(self) -> None:
        if not self._component_rows:
            return
        self._conn.executemany(
            """
            INSERT INTO components_full (
                lcsc_id,
                component_type,
                category,
                subcategory,
                manufacturer_name,
                part_number,
                package,
                description,
                stock,
                is_basic,
                is_preferred,
                datasheet_url,
                price_json,
                attributes_json,
                extra_json,
                resistance_ohm,
                resistance_min_ohm,
                resistance_max_ohm,
                capacitance_f,
                capacitance_min_f,
                capacitance_max_f,
                tolerance_pct,
                max_power_w,
                max_voltage_v,
                resistor_tempco_ppm,
                capacitor_tempco_code,
                inductance_h,
                inductance_min_h,
                inductance_max_h,
                max_current_a,
                dc_resistance_ohm,
                saturation_current_a,
                self_resonant_frequency_hz,
                forward_voltage_v,
                reverse_working_voltage_v,
                reverse_leakage_current_a,
                led_color_code,
                max_brightness_cd,
                bjt_doping_type,
                max_collector_emitter_voltage_v,
                max_collector_current_a,
                dc_current_gain_hfe,
                mosfet_channel_type,
                gate_source_threshold_voltage_v,
                max_drain_source_voltage_v,
                max_continuous_drain_current_a,
                on_resistance_ohm
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
            )
            """,
            self._component_rows,
        )
        self._conn.executemany(
            """
            INSERT INTO component_assets (
                lcsc_id,
                artifact_type,
                stored_key,
                encoding,
                mime,
                raw_sha256,
                raw_size_bytes,
                source_url,
                source_meta_json,
                datasheet_url,
                data_manual_url,
                footprint_name,
                model_3d_path,
                easyeda_model_uuid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._asset_rows,
        )
        self.inserted_count += len(self._component_rows)
        self._component_rows.clear()
        self._asset_rows.clear()

    def finalize(self) -> None:
        self._flush_rows()
        self._conn.executescript(
            """
            CREATE INDEX components_full_type_stock_idx
            ON components_full (component_type, stock DESC);
            CREATE INDEX components_full_package_idx
            ON components_full (component_type, package);
            CREATE INDEX component_assets_lcsc_idx
            ON component_assets (lcsc_id);
            CREATE INDEX component_assets_artifact_idx
            ON component_assets (artifact_type);
            ANALYZE;
            PRAGMA optimize;
            """
        )
        self._conn.commit()
        self._conn.close()


def test_detail_db_builder(tmp_path) -> None:
    db_path = tmp_path / "detail.sqlite"
    builder = DetailDbBuilder(db_path, batch_size=1)
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
            datasheet_url="https://example.com/a.pdf",
            price_json="[]",
            attributes_json='{"Resistance":"10kΩ"}',
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
            data_manual_url="https://example.com/manual",
            model_3d_path="/3d/path",
            easyeda_model_uuid="uuid",
            footprint_name="R0402",
        )
    )
    builder.finalize()

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM components_full").fetchone()[0] == 1
    asset = conn.execute(
        """
        SELECT datasheet_url, footprint_name, easyeda_model_uuid
        FROM component_assets
        WHERE lcsc_id = 1
          AND artifact_type IS NULL
        """
    ).fetchone()
    assert asset == ("https://example.com/a.pdf", "R0402", "uuid")
    conn.close()


def test_detail_db_builder_includes_stage1_asset_rows(tmp_path) -> None:
    db_path = tmp_path / "detail.sqlite"
    builder = DetailDbBuilder(
        db_path,
        batch_size=1,
        stage1_assets_by_lcsc={
            1: [
                {
                    "artifact_type": "datasheet_pdf",
                    "stored_key": "objects/datasheet_pdf/abc.zst",
                    "encoding": "zstd",
                    "mime": "application/pdf",
                    "raw_sha256": "abc",
                    "raw_size_bytes": 42,
                    "source_url": "https://example.com/a.pdf",
                    "source_meta": {"status_code": 200},
                }
            ]
        },
    )
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
            datasheet_url="https://example.com/a.pdf",
            price_json="[]",
            attributes_json='{"Resistance":"10kΩ"}',
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
            footprint_name="R0402",
        )
    )
    builder.finalize()

    conn = sqlite3.connect(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM component_assets WHERE lcsc_id = 1"
    ).fetchone()[0]
    assert count == 2
    artifact = conn.execute(
        """
        SELECT artifact_type, stored_key, source_meta_json
        FROM component_assets
        WHERE lcsc_id = 1
          AND artifact_type = 'datasheet_pdf'
        """
    ).fetchone()
    assert artifact is not None
    assert artifact[0] == "datasheet_pdf"
    assert artifact[1] == "objects/datasheet_pdf/abc.zst"
    assert json.loads(artifact[2])["status_code"] == 200
    conn.close()
