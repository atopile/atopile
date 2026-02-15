from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Protocol

ComponentType = Literal["resistor", "capacitor"]

RESISTOR_SUBCATEGORIES: tuple[str, ...] = (
    "Current Sense Resistors / Shunt Resistors",
    "Current Sense Resistors/Shunt Resistors",
    "Through Hole Resistors",
    "Chip Resistor - Surface Mount",
)

CAPACITOR_SUBCATEGORIES: tuple[str, ...] = (
    "Film Capacitors",
    "Multilayer Ceramic Capacitors MLCC - Leaded",
    "Through Hole Ceramic Capacitors",
    "Aluminum Electrolytic Capacitors - Leaded",
    "Multilayer Ceramic Capacitors MLCC - SMD/SMT",
    "Polymer Aluminum Capacitors",
    "Aluminum Electrolytic Capacitors - SMD",
    "Ceramic Disc Capacitors",
    "Horn-Type Electrolytic Capacitors",
    "Polypropylene Film Capacitors (CBB)",
    "Tantalum Capacitors",
)

_SI_PREFIX: dict[str, float] = {
    "y": 1e-24,
    "z": 1e-21,
    "a": 1e-18,
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "": 1.0,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
}

_SI_VALUE_RE = re.compile(
    r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
    r"([yzafpnumkMGT]?)"
    r"[A-Za-zΩΩ°℃%/\-\(\)]*$"
)
_TOLERANCE_SINGLE_RE = re.compile(r"^[±]?\s*([+-]?\d+(?:\.\d+)?)\s*%$")
_TOLERANCE_RANGE_RE = re.compile(
    r"^([+-]?\d+(?:\.\d+)?)\s*%\s*~\s*([+-]?\d+(?:\.\d+)?)\s*%$"
)
_TOLERANCE_SPLIT_RE = re.compile(
    r"^\+?\s*(\d+(?:\.\d+)?)\s*/\s*-?\s*(\d+(?:\.\d+)?)\s*%?$"
)
_TEMPCO_RE = re.compile(r"[±+\-]?\s*(\d+(?:\.\d+)?)\s*ppm", re.IGNORECASE)


@dataclass(frozen=True)
class SourceComponent:
    lcsc_id: int
    component_type: ComponentType
    category: str
    subcategory: str
    manufacturer_name: str | None
    part_number: str
    package: str
    description: str
    is_basic: bool
    is_preferred: bool
    stock: int
    datasheet_url: str | None
    price_json: str
    extra_json: str | None
    resistance_raw: str | None
    tolerance_raw: str | None
    power_raw: str | None
    resistor_voltage_raw: str | None
    tempco_raw: str | None
    capacitance_raw: str | None
    capacitor_voltage_raw: str | None
    data_manual_url: str | None
    model_3d_path: str | None
    easyeda_model_uuid: str | None
    footprint_name: str | None


@dataclass(frozen=True)
class NormalizedComponent:
    lcsc_id: int
    component_type: ComponentType
    category: str
    subcategory: str
    manufacturer_name: str | None
    part_number: str
    package: str
    description: str
    is_basic: bool
    is_preferred: bool
    stock: int
    datasheet_url: str | None
    price_json: str
    attributes_json: str
    extra_json: str | None
    resistance_ohm: float | None
    resistance_min_ohm: float | None
    resistance_max_ohm: float | None
    capacitance_f: float | None
    capacitance_min_f: float | None
    capacitance_max_f: float | None
    tolerance_pct: float | None
    max_power_w: float | None
    max_voltage_v: float | None
    resistor_tempco_ppm: float | None
    capacitor_tempco_code: str | None
    data_manual_url: str | None
    model_3d_path: str | None
    easyeda_model_uuid: str | None
    footprint_name: str | None


class ComponentSink(Protocol):
    inserted_count: int

    def add_component(self, component: NormalizedComponent) -> None: ...

    def finalize(self) -> None: ...


def category_to_component_type(category: str, subcategory: str) -> ComponentType | None:
    if category == "Resistors" and subcategory in RESISTOR_SUBCATEGORIES:
        return "resistor"
    if category == "Capacitors" and subcategory in CAPACITOR_SUBCATEGORIES:
        return "capacitor"
    return None


def normalize_component(component: SourceComponent) -> NormalizedComponent:
    attributes = _extract_attributes(component.extra_json)
    tolerance_pct = parse_tolerance_percent(component.tolerance_raw)

    resistance_ohm: float | None = None
    resistance_min_ohm: float | None = None
    resistance_max_ohm: float | None = None
    capacitance_f: float | None = None
    capacitance_min_f: float | None = None
    capacitance_max_f: float | None = None
    max_power_w: float | None = None
    max_voltage_v: float | None = None
    resistor_tempco_ppm: float | None = None
    capacitor_tempco_code: str | None = None

    if component.component_type == "resistor":
        resistance_ohm = parse_si_value(component.resistance_raw)
        resistance_min_ohm, resistance_max_ohm = tolerance_bounds(
            nominal=resistance_ohm,
            tolerance_pct=tolerance_pct,
        )
        max_power_w = parse_si_value(component.power_raw)
        max_voltage_v = parse_si_value(component.resistor_voltage_raw)
        resistor_tempco_ppm = parse_tempco_ppm(component.tempco_raw)
    elif component.component_type == "capacitor":
        capacitance_f = parse_si_value(component.capacitance_raw)
        capacitance_min_f, capacitance_max_f = tolerance_bounds(
            nominal=capacitance_f,
            tolerance_pct=tolerance_pct,
        )
        max_voltage_v = parse_si_value(component.capacitor_voltage_raw)
        capacitor_tempco_code = normalize_tempco_code(component.tempco_raw)

    return NormalizedComponent(
        lcsc_id=component.lcsc_id,
        component_type=component.component_type,
        category=component.category,
        subcategory=component.subcategory,
        manufacturer_name=component.manufacturer_name,
        part_number=component.part_number,
        package=component.package,
        description=component.description,
        is_basic=component.is_basic,
        is_preferred=component.is_preferred,
        stock=component.stock,
        datasheet_url=component.datasheet_url,
        price_json=component.price_json,
        attributes_json=json.dumps(
            attributes,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ),
        extra_json=component.extra_json,
        resistance_ohm=resistance_ohm,
        resistance_min_ohm=resistance_min_ohm,
        resistance_max_ohm=resistance_max_ohm,
        capacitance_f=capacitance_f,
        capacitance_min_f=capacitance_min_f,
        capacitance_max_f=capacitance_max_f,
        tolerance_pct=tolerance_pct,
        max_power_w=max_power_w,
        max_voltage_v=max_voltage_v,
        resistor_tempco_ppm=resistor_tempco_ppm,
        capacitor_tempco_code=capacitor_tempco_code,
        data_manual_url=component.data_manual_url,
        model_3d_path=component.model_3d_path,
        easyeda_model_uuid=component.easyeda_model_uuid,
        footprint_name=component.footprint_name,
    )


def parse_si_value(raw: str | None) -> float | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped in {"-", "null"}:
        return None

    parts = _split_multi_value_tokens(stripped)
    parsed_values: list[float] = []
    for part in parts:
        normalized = (
            part.strip()
            .replace(" ", "")
            .replace(",", "")
            .replace("μ", "u")
            .replace("µ", "u")
            .replace("Ω", "")
            .replace("Ω", "")
        )
        if not normalized:
            continue
        match = _SI_VALUE_RE.match(normalized)
        if not match:
            continue
        magnitude = float(match.group(1))
        prefix = match.group(2)
        multiplier = _SI_PREFIX.get(prefix)
        if multiplier is None:
            continue
        parsed_values.append(magnitude * multiplier)
    if not parsed_values:
        return None
    return min(parsed_values)


def parse_tolerance_percent(raw: str | None) -> float | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped == "-":
        return None
    match_single = _TOLERANCE_SINGLE_RE.match(stripped)
    if match_single:
        return abs(float(match_single.group(1)))
    match_range = _TOLERANCE_RANGE_RE.match(stripped)
    if match_range:
        left = float(match_range.group(1))
        right = float(match_range.group(2))
        return max(abs(left), abs(right))
    match_split = _TOLERANCE_SPLIT_RE.match(stripped)
    if match_split:
        pos = float(match_split.group(1))
        neg = float(match_split.group(2))
        return max(abs(pos), abs(neg))
    if stripped.endswith("%"):
        try:
            return abs(float(stripped[:-1]))
        except ValueError:
            return None
    return None


def parse_tempco_ppm(raw: str | None) -> float | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped == "-":
        return None
    match = _TEMPCO_RE.search(stripped)
    if not match:
        return None
    return abs(float(match.group(1)))


def normalize_tempco_code(raw: str | None) -> str | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped in {"-", "null"}:
        return None
    first_token = re.split(r"[;,\s]+", stripped)[0].upper()
    if first_token == "NP0":
        return "C0G"
    return first_token


def tolerance_bounds(
    *,
    nominal: float | None,
    tolerance_pct: float | None,
) -> tuple[float | None, float | None]:
    if nominal is None:
        return None, None
    if tolerance_pct is None:
        return nominal, nominal
    fraction = tolerance_pct / 100.0
    return nominal * (1.0 - fraction), nominal * (1.0 + fraction)


def _split_multi_value_tokens(raw: str) -> list[str]:
    parts = re.split(r"[;~]", raw)
    if len(parts) == 1:
        return [raw]
    return [part for part in parts if part.strip()]


def _extract_attributes(extra_json: str | None) -> dict[str, str]:
    if not extra_json:
        return {}
    try:
        parsed = json.loads(extra_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    attrs = parsed.get("attributes")
    if not isinstance(attrs, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in attrs.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, (str, int, float)):
            result[key] = str(value)
    return result


def normalize_components(
    source_components: Iterable[SourceComponent],
) -> list[NormalizedComponent]:
    return [normalize_component(component) for component in source_components]


def test_parse_si_value() -> None:
    assert parse_si_value("10kΩ") == 10_000.0
    assert parse_si_value("62.5mW") == 0.0625
    assert parse_si_value("1.2kV;700V") == 700.0
    assert parse_si_value("-") is None
    assert parse_si_value(None) is None


def test_parse_tolerance_percent() -> None:
    assert parse_tolerance_percent("±5%") == 5.0
    assert parse_tolerance_percent("-20%~+80%") == 80.0
    assert parse_tolerance_percent("+80/-20%") == 80.0
    assert parse_tolerance_percent("-") is None


def test_tolerance_bounds() -> None:
    assert tolerance_bounds(nominal=100.0, tolerance_pct=5.0) == (95.0, 105.0)
    assert tolerance_bounds(nominal=100.0, tolerance_pct=None) == (100.0, 100.0)
    assert tolerance_bounds(nominal=None, tolerance_pct=5.0) == (None, None)


def test_normalize_tempco_and_category() -> None:
    assert normalize_tempco_code("NP0") == "C0G"
    assert normalize_tempco_code("x7r") == "X7R"
    assert normalize_tempco_code("-") is None
    assert (
        category_to_component_type("Resistors", "Chip Resistor - Surface Mount")
        == "resistor"
    )
    assert (
        category_to_component_type("Capacitors", "Tantalum Capacitors") == "capacitor"
    )
    assert category_to_component_type("Resistors", "Resistor Networks & Arrays") is None


def test_normalize_component_resistor() -> None:
    source = SourceComponent(
        lcsc_id=123,
        component_type="resistor",
        category="Resistors",
        subcategory="Chip Resistor - Surface Mount",
        manufacturer_name="MFR",
        part_number="PN",
        package="0402",
        description="desc",
        is_basic=True,
        is_preferred=False,
        stock=10,
        datasheet_url="https://example.com/ds.pdf",
        price_json="[]",
        extra_json='{"attributes":{"Resistance":"10kΩ"}}',
        resistance_raw="10kΩ",
        tolerance_raw="±1%",
        power_raw="62.5mW",
        resistor_voltage_raw="50V",
        tempco_raw="±100ppm/℃",
        capacitance_raw=None,
        capacitor_voltage_raw=None,
        data_manual_url=None,
        model_3d_path=None,
        easyeda_model_uuid=None,
        footprint_name=None,
    )
    normalized = normalize_component(source)
    assert normalized.resistance_ohm == 10_000.0
    assert normalized.resistance_min_ohm == 9_900.0
    assert normalized.resistance_max_ohm == 10_100.0
    assert normalized.tolerance_pct == 1.0
    assert normalized.max_power_w == 0.0625
    assert normalized.max_voltage_v == 50.0
    assert normalized.resistor_tempco_ppm == 100.0
