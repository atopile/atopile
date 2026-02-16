from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .models import ComponentSink, NormalizedComponent

_PACKAGE_NUMERIC_RE = re.compile(r"^\d{4,5}$")
_PACKAGE_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
_PASSIVE_PREFIX = {
    "resistor": "R",
    "capacitor": "C",
    "capacitor_polarized": "C",
    "inductor": "L",
    "ferrite_bead": "L",
}


class FastLookupDbBuilder(ComponentSink):
    def __init__(self, db_path: Path, *, batch_size: int = 5000):
        self.db_path = db_path
        self.batch_size = batch_size
        self._conn = sqlite3.connect(db_path)
        self._rows: dict[str, list[tuple]] = {
            "resistor": [],
            "capacitor": [],
            "capacitor_polarized": [],
            "inductor": [],
            "diode": [],
            "led": [],
            "bjt": [],
            "mosfet": [],
            "crystal": [],
            "ferrite_bead": [],
            "ldo": [],
        }
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
            """
        )

    def add_component(self, component: NormalizedComponent) -> None:
        if component.component_type == "resistor":
            if not _is_pickable_resistor(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["resistor"].append(
                (
                    component.lcsc_id,
                    package,
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
            self._flush_if_needed("resistor")
            return

        if component.component_type == "capacitor":
            if not _is_pickable_capacitor(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["capacitor"].append(
                (
                    component.lcsc_id,
                    package,
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
            self._flush_if_needed("capacitor")
            return

        if component.component_type == "capacitor_polarized":
            if not _is_pickable_capacitor_polarized(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["capacitor_polarized"].append(
                (
                    component.lcsc_id,
                    package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.capacitance_f,
                    component.capacitance_min_f,
                    component.capacitance_max_f,
                    component.tolerance_pct,
                    component.max_voltage_v,
                )
            )
            self._flush_if_needed("capacitor_polarized")
            return

        if component.component_type == "inductor":
            if not _is_pickable_inductor(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["inductor"].append(
                (
                    component.lcsc_id,
                    package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.inductance_h,
                    component.inductance_min_h,
                    component.inductance_max_h,
                    component.tolerance_pct,
                    component.max_current_a,
                    component.dc_resistance_ohm,
                    component.saturation_current_a,
                    component.self_resonant_frequency_hz,
                )
            )
            self._flush_if_needed("inductor")
            return

        if component.component_type == "diode":
            if not _is_pickable_diode(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["diode"].append(
                (
                    component.lcsc_id,
                    package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.forward_voltage_v,
                    component.reverse_working_voltage_v,
                    component.max_current_a,
                    component.reverse_leakage_current_a,
                )
            )
            self._flush_if_needed("diode")
            return

        if component.component_type == "led":
            if not _is_pickable_led(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["led"].append(
                (
                    component.lcsc_id,
                    package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.led_color_code,
                    component.forward_voltage_v,
                    component.max_current_a,
                    component.max_brightness_cd,
                )
            )
            self._flush_if_needed("led")
            return

        if component.component_type == "bjt":
            if not _is_pickable_bjt(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["bjt"].append(
                (
                    component.lcsc_id,
                    package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.bjt_doping_type,
                    component.max_collector_emitter_voltage_v,
                    component.max_collector_current_a,
                    component.max_power_w,
                    component.dc_current_gain_hfe,
                )
            )
            self._flush_if_needed("bjt")
            return

        if component.component_type == "mosfet":
            if not _is_pickable_mosfet(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["mosfet"].append(
                (
                    component.lcsc_id,
                    package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.mosfet_channel_type,
                    component.max_drain_source_voltage_v,
                    component.max_continuous_drain_current_a,
                    component.on_resistance_ohm,
                    component.gate_source_threshold_voltage_v,
                )
            )
            self._flush_if_needed("mosfet")
            return

        if component.component_type == "crystal":
            if not _is_pickable_crystal(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["crystal"].append(
                (
                    component.lcsc_id,
                    package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.frequency_hz,
                    component.frequency_min_hz,
                    component.frequency_max_hz,
                    component.load_capacitance_f,
                    component.frequency_tolerance_ppm,
                    component.frequency_stability_ppm,
                )
            )
            self._flush_if_needed("crystal")
            return

        if component.component_type == "ferrite_bead":
            if not _is_pickable_ferrite_bead(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["ferrite_bead"].append(
                (
                    component.lcsc_id,
                    package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.ferrite_impedance_ohm,
                    component.ferrite_current_rating_a,
                    component.dc_resistance_ohm,
                )
            )
            self._flush_if_needed("ferrite_bead")
            return

        if component.component_type == "ldo":
            if not _is_pickable_ldo(component):
                return
            package = _normalize_package(component.component_type, component.package)
            self._rows["ldo"].append(
                (
                    component.lcsc_id,
                    package,
                    component.stock,
                    int(component.is_basic),
                    int(component.is_preferred),
                    component.ldo_output_voltage_v,
                    component.ldo_max_input_voltage_v,
                    component.ldo_output_current_a,
                    component.ldo_dropout_voltage_v,
                    component.ldo_output_type,
                    component.ldo_output_polarity,
                )
            )
            self._flush_if_needed("ldo")

    def _flush_if_needed(self, component_type: str) -> None:
        if len(self._rows[component_type]) >= self.batch_size:
            self._flush(component_type)

    def _flush(self, component_type: str) -> None:
        rows = self._rows[component_type]
        if not rows:
            return
        self._conn.executemany(_INSERT_SQL_BY_TYPE[component_type], rows)
        self.inserted_count += len(rows)
        rows.clear()

    def finalize(self) -> None:
        for component_type in self._rows:
            self._flush(component_type)
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

            CREATE INDEX capacitor_polarized_pick_lookup_pkg_idx
            ON capacitor_polarized_pick (
                package,
                capacitance_min_f,
                capacitance_max_f,
                max_voltage_v,
                stock DESC
            );
            CREATE INDEX capacitor_polarized_pick_lookup_range_idx
            ON capacitor_polarized_pick (
                capacitance_min_f,
                capacitance_max_f,
                max_voltage_v,
                stock DESC
            );

            CREATE INDEX inductor_pick_lookup_pkg_idx
            ON inductor_pick (
                package,
                inductance_min_h,
                inductance_max_h,
                max_current_a,
                dc_resistance_ohm,
                stock DESC
            );
            CREATE INDEX inductor_pick_lookup_range_idx
            ON inductor_pick (
                inductance_min_h,
                inductance_max_h,
                max_current_a,
                dc_resistance_ohm,
                stock DESC
            );

            CREATE INDEX diode_pick_lookup_pkg_idx
            ON diode_pick (
                package,
                forward_voltage_v,
                reverse_working_voltage_v,
                max_current_a,
                stock DESC
            );

            CREATE INDEX led_pick_lookup_pkg_idx
            ON led_pick (
                package,
                color_code,
                forward_voltage_v,
                max_current_a,
                stock DESC
            );

            CREATE INDEX bjt_pick_lookup_pkg_idx
            ON bjt_pick (
                package,
                doping_type,
                max_collector_emitter_voltage_v,
                max_collector_current_a,
                max_power_w,
                stock DESC
            );

            CREATE INDEX mosfet_pick_lookup_pkg_idx
            ON mosfet_pick (
                package,
                channel_type,
                max_drain_source_voltage_v,
                max_continuous_drain_current_a,
                on_resistance_ohm,
                stock DESC
            );

            CREATE INDEX crystal_pick_lookup_pkg_idx
            ON crystal_pick (
                package,
                frequency_min_hz,
                frequency_max_hz,
                load_capacitance_f,
                frequency_tolerance_ppm,
                stock DESC
            );
            CREATE INDEX crystal_pick_lookup_range_idx
            ON crystal_pick (
                frequency_min_hz,
                frequency_max_hz,
                load_capacitance_f,
                stock DESC
            );

            CREATE INDEX ferrite_bead_pick_lookup_pkg_idx
            ON ferrite_bead_pick (
                package,
                impedance_ohm,
                current_rating_a,
                dc_resistance_ohm,
                stock DESC
            );

            CREATE INDEX ldo_pick_lookup_pkg_idx
            ON ldo_pick (
                package,
                output_type,
                output_polarity,
                output_voltage_v,
                max_input_voltage_v,
                output_current_a,
                dropout_voltage_v,
                stock DESC
            );
            ANALYZE;
            PRAGMA optimize;
            """
        )
        self._conn.commit()
        self._conn.close()


def _is_valid_package(raw_package: str) -> bool:
    package = raw_package.strip()
    if not package:
        return False
    if package == "-":
        return False
    return True


def _normalize_package(component_type: str, raw_package: str) -> str:
    package = raw_package.strip().upper()
    if component_type == "crystal":
        canonical = _PACKAGE_NON_ALNUM_RE.sub("", package)
        return canonical or package

    if component_type == "ferrite_bead":
        for prefix in ("L", "FB"):
            if package.startswith(prefix):
                suffix = package[len(prefix) :]
                if _PACKAGE_NUMERIC_RE.fullmatch(suffix):
                    return suffix
        return package

    prefix = _PASSIVE_PREFIX.get(component_type)
    if prefix and package.startswith(prefix):
        suffix = package[len(prefix) :]
        if _PACKAGE_NUMERIC_RE.fullmatch(suffix):
            return suffix
    return package


def _is_pickable_base(component: NormalizedComponent) -> bool:
    if component.stock <= 0:
        return False
    if not _is_valid_package(component.package):
        return False
    return True


def _is_pickable_resistor(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.resistance_ohm is None:
        return False
    if component.resistance_min_ohm is None or component.resistance_max_ohm is None:
        return False
    if component.tolerance_pct is None:
        return False
    if component.max_power_w is None or component.max_power_w <= 0:
        return False
    if component.max_voltage_v is None or component.max_voltage_v <= 0:
        return False
    return True


def _is_pickable_capacitor(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.capacitance_f is None or component.capacitance_f <= 0:
        return False
    if component.capacitance_min_f is None or component.capacitance_max_f is None:
        return False
    if component.tolerance_pct is None:
        return False
    if component.max_voltage_v is None or component.max_voltage_v <= 0:
        return False
    return True


def _is_pickable_capacitor_polarized(component: NormalizedComponent) -> bool:
    return _is_pickable_capacitor(component)


def _is_pickable_inductor(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.inductance_h is None or component.inductance_h <= 0:
        return False
    if component.inductance_min_h is None or component.inductance_max_h is None:
        return False
    if component.max_current_a is None or component.max_current_a <= 0:
        return False
    if component.dc_resistance_ohm is None or component.dc_resistance_ohm < 0:
        return False
    return True


def _is_pickable_diode(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.forward_voltage_v is None or component.forward_voltage_v <= 0:
        return False
    if (
        component.reverse_working_voltage_v is None
        or component.reverse_working_voltage_v <= 0
    ):
        return False
    if component.max_current_a is None or component.max_current_a <= 0:
        return False
    return True


def _is_pickable_led(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.led_color_code is None:
        return False
    if component.forward_voltage_v is None or component.forward_voltage_v <= 0:
        return False
    if component.max_current_a is None or component.max_current_a <= 0:
        return False
    return True


def _is_pickable_bjt(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.bjt_doping_type not in {"NPN", "PNP"}:
        return False
    if (
        component.max_collector_emitter_voltage_v is None
        or component.max_collector_emitter_voltage_v <= 0
    ):
        return False
    if (
        component.max_collector_current_a is None
        or component.max_collector_current_a <= 0
    ):
        return False
    if component.max_power_w is None or component.max_power_w <= 0:
        return False
    return True


def _is_pickable_mosfet(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.mosfet_channel_type not in {"N_CHANNEL", "P_CHANNEL"}:
        return False
    if (
        component.max_drain_source_voltage_v is None
        or component.max_drain_source_voltage_v <= 0
    ):
        return False
    if (
        component.max_continuous_drain_current_a is None
        or component.max_continuous_drain_current_a <= 0
    ):
        return False
    if component.on_resistance_ohm is None or component.on_resistance_ohm <= 0:
        return False
    return True


def _is_pickable_crystal(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.frequency_hz is None or component.frequency_hz <= 0:
        return False
    if component.frequency_min_hz is None or component.frequency_max_hz is None:
        return False
    if (
        component.frequency_tolerance_ppm is None
        or component.frequency_tolerance_ppm < 0
    ):
        return False
    if component.load_capacitance_f is None or component.load_capacitance_f <= 0:
        return False
    return True


def _is_pickable_ferrite_bead(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.ferrite_impedance_ohm is None or component.ferrite_impedance_ohm <= 0:
        return False
    if (
        component.ferrite_current_rating_a is None
        or component.ferrite_current_rating_a <= 0
    ):
        return False
    if component.dc_resistance_ohm is None or component.dc_resistance_ohm < 0:
        return False
    return True


def _is_pickable_ldo(component: NormalizedComponent) -> bool:
    if not _is_pickable_base(component):
        return False
    if component.ldo_output_voltage_v is None or component.ldo_output_voltage_v <= 0:
        return False
    if (
        component.ldo_max_input_voltage_v is None
        or component.ldo_max_input_voltage_v <= 0
    ):
        return False
    if component.ldo_output_current_a is None or component.ldo_output_current_a <= 0:
        return False
    if component.ldo_dropout_voltage_v is None or component.ldo_dropout_voltage_v <= 0:
        return False
    return True


_INSERT_SQL_BY_TYPE = {
    "resistor": """
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
    "capacitor": """
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
    "capacitor_polarized": """
        INSERT INTO capacitor_polarized_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            capacitance_f,
            capacitance_min_f,
            capacitance_max_f,
            tolerance_pct,
            max_voltage_v
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "inductor": """
        INSERT INTO inductor_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            inductance_h,
            inductance_min_h,
            inductance_max_h,
            tolerance_pct,
            max_current_a,
            dc_resistance_ohm,
            saturation_current_a,
            self_resonant_frequency_hz
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "diode": """
        INSERT INTO diode_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            forward_voltage_v,
            reverse_working_voltage_v,
            max_current_a,
            reverse_leakage_current_a
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "led": """
        INSERT INTO led_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            color_code,
            forward_voltage_v,
            max_current_a,
            max_brightness_cd
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "bjt": """
        INSERT INTO bjt_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            doping_type,
            max_collector_emitter_voltage_v,
            max_collector_current_a,
            max_power_w,
            dc_current_gain_hfe
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "mosfet": """
        INSERT INTO mosfet_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            channel_type,
            max_drain_source_voltage_v,
            max_continuous_drain_current_a,
            on_resistance_ohm,
            gate_source_threshold_voltage_v
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "crystal": """
        INSERT INTO crystal_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            frequency_hz,
            frequency_min_hz,
            frequency_max_hz,
            load_capacitance_f,
            frequency_tolerance_ppm,
            frequency_stability_ppm
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "ferrite_bead": """
        INSERT INTO ferrite_bead_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            impedance_ohm,
            current_rating_a,
            dc_resistance_ohm
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    "ldo": """
        INSERT INTO ldo_pick (
            lcsc_id,
            package,
            stock,
            is_basic,
            is_preferred,
            output_voltage_v,
            max_input_voltage_v,
            output_current_a,
            dropout_voltage_v,
            output_type,
            output_polarity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
}


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
            component_type="diode",
            category="Diodes",
            subcategory="Switching Diode",
            manufacturer_name="M",
            part_number="D1",
            package="SOD-123",
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
            capacitance_f=None,
            capacitance_min_f=None,
            capacitance_max_f=None,
            tolerance_pct=None,
            max_power_w=None,
            max_voltage_v=None,
            resistor_tempco_ppm=None,
            capacitor_tempco_code=None,
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
            forward_voltage_v=0.75,
            reverse_working_voltage_v=100.0,
            max_current_a=0.3,
        )
    )
    builder.finalize()

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM resistor_pick").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM diode_pick").fetchone()[0] == 1
    index_names = {
        row[1] for row in conn.execute("PRAGMA index_list('resistor_pick')").fetchall()
    }
    assert "resistor_pick_lookup_pkg_idx" in index_names
    conn.close()


def test_fast_lookup_db_builder_prefilters_non_pickable_rows(tmp_path) -> None:
    db_path = tmp_path / "fast.sqlite"
    builder = FastLookupDbBuilder(db_path, batch_size=10)

    builder.add_component(
        NormalizedComponent(
            lcsc_id=10,
            component_type="mosfet",
            category="Transistors",
            subcategory="MOSFETs",
            manufacturer_name="M",
            part_number="Q-good",
            package="SOT-23",
            description="d",
            is_basic=True,
            is_preferred=False,
            stock=1,
            datasheet_url=None,
            price_json="[]",
            attributes_json="{}",
            extra_json="{}",
            resistance_ohm=None,
            resistance_min_ohm=None,
            resistance_max_ohm=None,
            capacitance_f=None,
            capacitance_min_f=None,
            capacitance_max_f=None,
            tolerance_pct=None,
            max_power_w=None,
            max_voltage_v=None,
            resistor_tempco_ppm=None,
            capacitor_tempco_code=None,
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
            mosfet_channel_type="N_CHANNEL",
            max_drain_source_voltage_v=30.0,
            max_continuous_drain_current_a=2.0,
            on_resistance_ohm=0.05,
        )
    )
    builder.add_component(
        NormalizedComponent(
            lcsc_id=11,
            component_type="mosfet",
            category="Transistors",
            subcategory="MOSFETs",
            manufacturer_name="M",
            part_number="Q-bad",
            package="SOT-23",
            description="d",
            is_basic=True,
            is_preferred=False,
            stock=1,
            datasheet_url=None,
            price_json="[]",
            attributes_json="{}",
            extra_json="{}",
            resistance_ohm=None,
            resistance_min_ohm=None,
            resistance_max_ohm=None,
            capacitance_f=None,
            capacitance_min_f=None,
            capacitance_max_f=None,
            tolerance_pct=None,
            max_power_w=None,
            max_voltage_v=None,
            resistor_tempco_ppm=None,
            capacitor_tempco_code=None,
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
            mosfet_channel_type=None,
            max_drain_source_voltage_v=30.0,
            max_continuous_drain_current_a=2.0,
            on_resistance_ohm=0.05,
        )
    )

    builder.finalize()
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM mosfet_pick").fetchone()[0] == 1
    conn.close()


def test_normalize_package_crystal_is_separator_insensitive() -> None:
    assert _normalize_package("crystal", "HC-49U") == "HC49U"
    assert _normalize_package("crystal", " hc49u ") == "HC49U"
