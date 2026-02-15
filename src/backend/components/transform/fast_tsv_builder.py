from __future__ import annotations

import re
from pathlib import Path

from .models import ComponentSink, NormalizedComponent

_PACKAGE_NUMERIC_RE = re.compile(r"^\d{4,5}$")
_PASSIVE_PREFIX = {
    "resistor": "R",
    "capacitor": "C",
}


class FastLookupTsvBuilder(ComponentSink):
    def __init__(
        self,
        resistor_path: Path,
        capacitor_path: Path,
        *,
        batch_size: int = 5000,
    ):
        self.resistor_path = resistor_path
        self.capacitor_path = capacitor_path
        self.batch_size = batch_size

        self.resistor_path.parent.mkdir(parents=True, exist_ok=True)
        self.capacitor_path.parent.mkdir(parents=True, exist_ok=True)
        self._resistor_handle = self.resistor_path.open(
            "w", encoding="utf-8", newline="\n"
        )
        self._capacitor_handle = self.capacitor_path.open(
            "w", encoding="utf-8", newline="\n"
        )
        self._resistor_rows: list[str] = []
        self._capacitor_rows: list[str] = []
        self.inserted_count = 0
        self.resistor_count = 0
        self.capacitor_count = 0
        self._closed = False

    def add_component(self, component: NormalizedComponent) -> None:
        if component.component_type == "resistor":
            package = _normalize_package("resistor", component.package)
            if package is None or not _is_pickable_resistor(component):
                return
            self._resistor_rows.append(
                _join_tsv_fields(
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
            )
            self.resistor_count += 1
            self.inserted_count += 1
            if len(self._resistor_rows) >= self.batch_size:
                self._flush_resistors()
            return

        if component.component_type == "capacitor":
            package = _normalize_package("capacitor", component.package)
            if package is None or not _is_pickable_capacitor(component):
                return
            self._capacitor_rows.append(
                _join_tsv_fields(
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
            )
            self.capacitor_count += 1
            self.inserted_count += 1
            if len(self._capacitor_rows) >= self.batch_size:
                self._flush_capacitors()

    def finalize(self) -> None:
        if self._closed:
            return
        try:
            self._flush_resistors()
            self._flush_capacitors()
        finally:
            self._resistor_handle.close()
            self._capacitor_handle.close()
            self._closed = True

    def _flush_resistors(self) -> None:
        if not self._resistor_rows:
            return
        self._resistor_handle.write("".join(self._resistor_rows))
        self._resistor_rows.clear()

    def _flush_capacitors(self) -> None:
        if not self._capacitor_rows:
            return
        self._capacitor_handle.write("".join(self._capacitor_rows))
        self._capacitor_rows.clear()


def _join_tsv_fields(values: tuple[object, ...]) -> str:
    return "\t".join(_format_tsv_field(value) for value in values) + "\n"


def _format_tsv_field(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return format(value, ".17g")
    text = str(value)
    return text.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _normalize_package(component_type: str, raw_package: str) -> str | None:
    package = raw_package.strip().upper()
    if not package or package == "-":
        return None

    prefix = _PASSIVE_PREFIX.get(component_type)
    if prefix and package.startswith(prefix):
        suffix = package[len(prefix) :]
        if _PACKAGE_NUMERIC_RE.fullmatch(suffix):
            return suffix
    return package


def _is_pickable_resistor(component: NormalizedComponent) -> bool:
    if component.stock <= 0:
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
    if component.stock <= 0:
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


def test_fast_lookup_tsv_builder(tmp_path) -> None:
    resistor_path = tmp_path / "resistor_pick.tsv"
    capacitor_path = tmp_path / "capacitor_pick.tsv"
    builder = FastLookupTsvBuilder(resistor_path, capacitor_path, batch_size=1)
    builder.add_component(
        NormalizedComponent(
            lcsc_id=1,
            component_type="resistor",
            category="Resistors",
            subcategory="Chip Resistor - Surface Mount",
            manufacturer_name="M",
            part_number="R1",
            package="R0402",
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
            package="C0603",
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
            capacitance_f=1e-6,
            capacitance_min_f=0.9e-6,
            capacitance_max_f=1.1e-6,
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

    resistor_lines = resistor_path.read_text(encoding="utf-8").strip().splitlines()
    capacitor_lines = capacitor_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(resistor_lines) == 1
    assert len(capacitor_lines) == 1
    resistor_fields = resistor_lines[0].split("\t")
    capacitor_fields = capacitor_lines[0].split("\t")
    assert resistor_fields[0] == "1"
    assert resistor_fields[1] == "0402"
    assert capacitor_fields[0] == "2"
    assert capacitor_fields[1] == "0603"


def test_fast_lookup_tsv_builder_prefilters_non_pickable_rows(tmp_path) -> None:
    resistor_path = tmp_path / "resistor_pick.tsv"
    capacitor_path = tmp_path / "capacitor_pick.tsv"
    builder = FastLookupTsvBuilder(resistor_path, capacitor_path, batch_size=10)

    builder.add_component(
        NormalizedComponent(
            lcsc_id=10,
            component_type="resistor",
            category="Resistors",
            subcategory="Chip Resistor - Surface Mount",
            manufacturer_name="M",
            part_number="R-good",
            package="0402",
            description="d",
            is_basic=True,
            is_preferred=False,
            stock=1,
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
            resistor_tempco_ppm=None,
            capacitor_tempco_code=None,
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
        )
    )
    builder.add_component(
        NormalizedComponent(
            lcsc_id=11,
            component_type="resistor",
            category="Resistors",
            subcategory="Chip Resistor - Surface Mount",
            manufacturer_name="M",
            part_number="R-oos",
            package="0402",
            description="d",
            is_basic=True,
            is_preferred=False,
            stock=0,
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
            resistor_tempco_ppm=None,
            capacitor_tempco_code=None,
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
        )
    )
    builder.add_component(
        NormalizedComponent(
            lcsc_id=20,
            component_type="capacitor",
            category="Capacitors",
            subcategory="Multilayer Ceramic Capacitors MLCC - SMD/SMT",
            manufacturer_name="M",
            part_number="C-good",
            package="0402",
            description="d",
            is_basic=False,
            is_preferred=True,
            stock=2,
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
    builder.add_component(
        NormalizedComponent(
            lcsc_id=21,
            component_type="capacitor",
            category="Capacitors",
            subcategory="Multilayer Ceramic Capacitors MLCC - SMD/SMT",
            manufacturer_name="M",
            part_number="C-missing-voltage",
            package="0402",
            description="d",
            is_basic=False,
            is_preferred=True,
            stock=2,
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
            max_voltage_v=None,
            resistor_tempco_ppm=None,
            capacitor_tempco_code="X7R",
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
        )
    )
    builder.finalize()

    resistor_lines = [
        line
        for line in resistor_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    capacitor_lines = [
        line
        for line in capacitor_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(resistor_lines) == 1
    assert len(capacitor_lines) == 1
