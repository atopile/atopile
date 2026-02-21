from __future__ import annotations

import re

from backend.components.shared.package_normalization import (
    normalize_package as _normalize_package,
)

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
    "frequency": "frequency_hz",
    "frequency_temperature_tolerance": "frequency_stability_ppm",
    "load_capacitance": "load_capacitance_f",
    "impedance_at_frequency": "impedance_ohm",
    "current_rating": "current_rating_a",
    "output_voltage": "output_voltage_v",
    "max_input_voltage": "max_input_voltage_v",
    "dropout_voltage": "dropout_voltage_v",
    "output_current": "output_current_a",
}
_EPSILON_RELATIVE = 1e-5
_PPM_SI_TO_PPM_THRESHOLD = 0.01

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


def expanded_range_bounds_for_column(
    column: str,
    numeric_range: NumericRange,
) -> tuple[float | None, float | None]:
    minimum, maximum = expanded_range_bounds(numeric_range)
    if _is_ppm_column(column):
        minimum = _normalize_ppm_value(minimum)
        maximum = _normalize_ppm_value(maximum)
    return minimum, maximum


def normalize_exact_filter_value(column: str, value: object) -> object:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and _is_ppm_column(column):
        normalized = _normalize_ppm_value(float(value))
        if normalized is not None:
            return normalized
    return value


def normalize_package(component_type: str, raw_package: str) -> str | None:
    return _normalize_package(component_type, raw_package)


def _is_ppm_column(column: str) -> bool:
    return column.endswith("_ppm")


def _normalize_ppm_value(value: float | None) -> float | None:
    if value is None:
        return None
    if abs(value) <= _PPM_SI_TO_PPM_THRESHOLD:
        return value * 1_000_000.0
    return value


def test_normalize_package_passive_prefixes() -> None:
    assert normalize_package("resistor", "R0402") == "0402"
    assert normalize_package("capacitor", "C0603") == "0603"
    assert normalize_package("inductor", "L0805") == "0805"
    assert normalize_package("ferrite_bead", "L0603") == "0603"
    assert normalize_package("ferrite_bead", "FB0603") == "0603"
    assert normalize_package("resistor", "0402") == "0402"


def test_normalize_package_crystal_is_separator_insensitive() -> None:
    assert normalize_package("crystal", "HC-49U") == "HC49U"
    assert normalize_package("crystal", "  hc49u ") == "HC49U"


def test_normalize_exact_filter_value_scales_si_ppm() -> None:
    assert normalize_exact_filter_value("frequency_stability_ppm", 3e-5) == 30.0
    assert normalize_exact_filter_value("frequency_stability_ppm", 30.0) == 30.0
    assert normalize_exact_filter_value("frequency_stability_ppm", True) is True
    assert normalize_exact_filter_value("resistance_ohm", 2e-5) == 2e-5


def test_expanded_range_bounds_for_column_scales_si_ppm() -> None:
    minimum, maximum = expanded_range_bounds_for_column(
        "frequency_stability_ppm",
        NumericRange(minimum=3e-5, maximum=3e-5),
    )
    assert minimum is not None and maximum is not None
    assert abs(minimum - 29.9997) < 1e-4
    assert abs(maximum - 30.0003) < 1e-4
