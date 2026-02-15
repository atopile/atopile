from __future__ import annotations

import re

from .interfaces import NumericRange

_QUERY_ALIASES = {
    "resistance": "resistance_ohm",
    "capacitance": "capacitance_f",
    "inductance": "inductance_h",
    "max_power": "max_power_w",
    "max_voltage": "max_voltage_v",
    "max_current": "max_current_a",
    "dc_resistance": "dc_resistance_ohm",
    "saturation_current": "saturation_current_a",
    "self_resonant_frequency": "self_resonant_frequency_hz",
    "forward_voltage": "forward_voltage_v",
    "reverse_working_voltage": "reverse_working_voltage_v",
    "reverse_leakage_current": "reverse_leakage_current_a",
    "color": "color_code",
    "max_brightness": "max_brightness_cd",
    "max_collector_emitter_voltage": "max_collector_emitter_voltage_v",
    "max_collector_current": "max_collector_current_a",
    "dc_current_gain": "dc_current_gain_hfe",
    "gate_source_threshold_voltage": "gate_source_threshold_voltage_v",
    "max_drain_source_voltage": "max_drain_source_voltage_v",
    "max_continuous_drain_current": "max_continuous_drain_current_a",
    "on_resistance": "on_resistance_ohm",
    "temperature_coefficient": "tempco_code",
    "tolerance": "tolerance_pct",
}
_EPSILON_RELATIVE = 1e-5
_PACKAGE_NUMERIC_RE = re.compile(r"^\d{4,5}$")
_COMPONENT_PACKAGE_PREFIX = {
    "resistor": "R",
    "capacitor": "C",
    "capacitor_polarized": "C",
    "inductor": "L",
}


def expanded_range_bounds(
    numeric_range: NumericRange,
) -> tuple[float | None, float | None]:
    minimum = numeric_range.minimum
    maximum = numeric_range.maximum
    if minimum is not None:
        minimum = minimum * (1.0 - _EPSILON_RELATIVE)
    if maximum is not None:
        maximum = maximum * (1.0 + _EPSILON_RELATIVE)
    return minimum, maximum


def normalize_package(component_type: str, raw_package: str) -> str | None:
    normalized = raw_package.strip().upper()
    if not normalized:
        return None

    prefix = _COMPONENT_PACKAGE_PREFIX.get(component_type)
    if prefix is None:
        return normalized

    if normalized.startswith(prefix):
        suffix = normalized[len(prefix) :]
        if _PACKAGE_NUMERIC_RE.fullmatch(suffix):
            return suffix
    return normalized


def test_normalize_package_passive_prefixes() -> None:
    assert normalize_package("resistor", "R0402") == "0402"
    assert normalize_package("capacitor", "C0603") == "0603"
    assert normalize_package("inductor", "L0805") == "0805"
    assert normalize_package("resistor", "0402") == "0402"
