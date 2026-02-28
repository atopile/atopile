# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _parse_pipe_list(param) -> list[str]:
    """Parse pipe-delimited strings from a StringParameter (e.g. extra_spice)."""
    raw = param.get().try_extract_singleton()
    if raw is None:
        return []
    return [line.strip() for line in raw.split("|") if line.strip()]


def _parse_comma_list(param) -> list[str]:
    """Parse comma-delimited strings from a StringParameter (e.g. remove_elements)."""
    raw = param.get().try_extract_singleton()
    if raw is None:
        return []
    return [name.strip() for name in raw.split(",") if name.strip()]


def _extract_text(param) -> str | None:
    """Extract a string from a parameter, with fallbacks for numeric values.

    Handles:
    1. Quoted strings (``"100ns"``) — direct singleton extraction.
    2. Bare numbers (``2e-7``) — Numbers literal → str.
    3. Values with units (``1ms``) — NumericParameter extraction → str.
    """
    node = param.get()

    # Path 1: string singleton
    try:
        v = node.try_extract_singleton()
        if v is not None:
            return v
    except Exception:
        pass

    # Path 2: Numbers literal (bare numbers)
    try:
        from faebryk.library.Literals import Numbers

        nums = node.is_parameter_operatable.get().try_extract_superset(
            lit_type=Numbers
        )
        if nums is not None:
            return str(nums.get_single())
    except Exception:
        pass

    # Path 3: NumericParameter extraction (values with units like 1ms)
    try:
        nums = node.try_extract_superset()
        if nums is not None:
            min_val = nums.get_min_value()
            max_val = nums.get_max_value()
            if not _math.isinf(min_val) and not _math.isinf(max_val):
                return str((min_val + max_val) / 2.0)
    except Exception:
        pass

    return None


_SI_PREFIXES: dict[str, float] = {
    "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "μ": 1e-6,
    "m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12,
}

import math as _math
import re as _re

_VALUE_WITH_UNIT_RE = _re.compile(
    r"^([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*([fpnuμmkMGT]?)([A-Za-z%]*)$"
)


def _parse_si_value(text: str) -> float | None:
    """Parse a string like ``1ms``, ``100ns``, ``5kHz`` to a float in base SI units."""
    m = _VALUE_WITH_UNIT_RE.match(text.strip())
    if not m:
        return None
    number = float(m.group(1))
    prefix = m.group(2)
    if prefix and prefix in _SI_PREFIXES:
        return number * _SI_PREFIXES[prefix]
    if not prefix:
        return number
    return None


def _extract_float(
    param, field_name: str = "", node_name: str = ""
) -> float | None:
    """Extract a float from a parameter storing a numeric value.

    Handles multiple representations the ato compiler may produce:

    1. **Quoted strings** (``"100ns"``) — ``try_extract_singleton()`` returns
       the string, then ``float()`` or SI-prefix parsing converts it.
    2. **Bare numbers** (``2e-7``) — compiler creates a ``Numbers`` literal;
       extracted via ``is_parameter_operatable``.
    3. **Values with units** (``1ms``, ``100ns``) — compiler creates a
       ``Numbers`` literal with unit; extracted via ``try_extract_superset()``.

    Args:
        param: The parameter to extract from.
        field_name: Optional field name for diagnostic logging (e.g. "time_step").
        node_name: Optional node name for diagnostic logging (e.g. "tran_startup").
    """
    node = param.get()

    # Path 1: string singleton → float (quoted numeric strings like "1e-3")
    try:
        v = node.try_extract_singleton()
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                # Maybe a string with units like "100ns" — parse SI prefix
                parsed = _parse_si_value(str(v))
                if parsed is not None:
                    return parsed
    except Exception:
        pass

    # Path 2: Numbers literal via is_parameter_operatable (bare numbers)
    try:
        from faebryk.library.Literals import Numbers

        nums = node.is_parameter_operatable.get().try_extract_superset(
            lit_type=Numbers
        )
        if nums is not None:
            return float(nums.get_single())
    except Exception:
        pass

    # Path 3: NumericParameter-style extraction (values with SI units like 1ms)
    try:
        nums = node.try_extract_superset()
        if nums is not None:
            min_val = nums.get_min_value()
            max_val = nums.get_max_value()
            if not _math.isinf(min_val) and not _math.isinf(max_val):
                return (min_val + max_val) / 2.0
    except Exception:
        pass

    if field_name:
        ctx = f" for '{node_name}'" if node_name else ""
        logger.debug(
            f"Could not extract numeric value from '{field_name}'{ctx}."
        )
    return None


# ---------------------------------------------------------------------------
# SimulationTransient
# ---------------------------------------------------------------------------


class SimulationTransient(fabll.Node):
    """Transient analysis configuration (flat — no inheritance from SimulationConfig).

    Usage in ato::

        sim = new SimulationTransient
        sim.time_start = 0s
        sim.time_stop = 10ms
        sim.time_step = 100ns
        sim.spice = "V1 power_in_hv 0 PULSE(0 12 0 10u 10u 10 10)"
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_spice_simulation = fabll.Traits.MakeEdge(F.is_spice_simulation.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # --- Common config fields ---
    spice = F.Parameters.StringParameter.MakeChild()
    extra_spice = F.Parameters.StringParameter.MakeChild()
    remove_elements = F.Parameters.StringParameter.MakeChild()
    duts = F.Parameters.StringParameter.MakeChild()

    # --- Transient-specific fields (StringParameter for bare-number ato assignments) ---
    time_start = F.Parameters.StringParameter.MakeChild()
    time_stop = F.Parameters.StringParameter.MakeChild()
    time_step = F.Parameters.StringParameter.MakeChild()

    def get_spice(self) -> str | None:
        return self.spice.get().try_extract_singleton()

    def get_extra_spice(self) -> list[str]:
        return _parse_pipe_list(self.extra_spice)

    def get_remove_elements(self) -> list[str]:
        return _parse_comma_list(self.remove_elements)

    def get_duts(self) -> list[str]:
        return _parse_comma_list(self.duts)

    def get_time_start(self) -> float | None:
        return _extract_float(self.time_start, "time_start", "SimulationTransient")

    def get_time_stop(self) -> float | None:
        return _extract_float(self.time_stop, "time_stop", "SimulationTransient")

    def get_time_step(self) -> float | None:
        return _extract_float(self.time_step, "time_step", "SimulationTransient")

    def get_time_start_text(self) -> str | None:
        return _extract_text(self.time_start)

    def get_time_stop_text(self) -> str | None:
        return _extract_text(self.time_stop)

    def get_time_step_text(self) -> str | None:
        return _extract_text(self.time_step)


# ---------------------------------------------------------------------------
# SimulationAC
# ---------------------------------------------------------------------------


class SimulationAC(fabll.Node):
    """AC small-signal analysis configuration (flat — no inheritance).

    Usage in ato::

        sim = new SimulationAC
        sim.start_freq = 1Hz
        sim.stop_freq = 10MHz
        sim.points_per_dec = 100
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_spice_simulation = fabll.Traits.MakeEdge(F.is_spice_simulation.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # --- Common config fields ---
    spice = F.Parameters.StringParameter.MakeChild()
    extra_spice = F.Parameters.StringParameter.MakeChild()
    remove_elements = F.Parameters.StringParameter.MakeChild()
    duts = F.Parameters.StringParameter.MakeChild()

    # --- AC-specific fields (StringParameter for bare-number ato assignments) ---
    start_freq = F.Parameters.StringParameter.MakeChild()
    stop_freq = F.Parameters.StringParameter.MakeChild()
    points_per_dec = F.Parameters.StringParameter.MakeChild()

    def get_spice(self) -> str | None:
        return self.spice.get().try_extract_singleton()

    def get_extra_spice(self) -> list[str]:
        return _parse_pipe_list(self.extra_spice)

    def get_remove_elements(self) -> list[str]:
        return _parse_comma_list(self.remove_elements)

    def get_duts(self) -> list[str]:
        return _parse_comma_list(self.duts)

    def get_start_freq(self) -> float | None:
        return _extract_float(self.start_freq, "start_freq", "SimulationAC")

    def get_stop_freq(self) -> float | None:
        return _extract_float(self.stop_freq, "stop_freq", "SimulationAC")

    def get_points_per_dec(self) -> int | None:
        v = _extract_float(self.points_per_dec, "points_per_dec", "SimulationAC")
        return int(v) if v is not None else None


# ---------------------------------------------------------------------------
# SimulationDCOP
# ---------------------------------------------------------------------------


class SimulationDCOP(fabll.Node):
    """DC operating point configuration (flat — no inheritance).

    Usage in ato::

        sim = new SimulationDCOP
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_spice_simulation = fabll.Traits.MakeEdge(F.is_spice_simulation.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # --- Common config fields ---
    spice = F.Parameters.StringParameter.MakeChild()
    extra_spice = F.Parameters.StringParameter.MakeChild()
    remove_elements = F.Parameters.StringParameter.MakeChild()
    duts = F.Parameters.StringParameter.MakeChild()

    def get_spice(self) -> str | None:
        return self.spice.get().try_extract_singleton()

    def get_extra_spice(self) -> list[str]:
        return _parse_pipe_list(self.extra_spice)

    def get_remove_elements(self) -> list[str]:
        return _parse_comma_list(self.remove_elements)

    def get_duts(self) -> list[str]:
        return _parse_comma_list(self.duts)


# ---------------------------------------------------------------------------
# SimulationSweep
# ---------------------------------------------------------------------------


class SimulationSweep(fabll.Node):
    """Parametric sweep — runs a transient simulation N times varying a parameter.

    Each sweep point substitutes `{param_name}` in the `spice_template` string
    with the current value from `param_values`.

    Usage in ato::

        sweep = new SimulationSweep
        sweep.param_name = "VIN"
        sweep.param_values = "6,8,12,24,36,48"
        sweep.param_unit = "V"
        sweep.time_start = 4ms
        sweep.time_stop = 5ms
        sweep.time_step = 200ns
        sweep.spice_template = "VIN power_in_hv 0 PULSE(0 {VIN} 0 10u 10u 10 10)"
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_spice_simulation = fabll.Traits.MakeEdge(F.is_spice_simulation.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # --- Sweep parameters ---
    param_name = F.Parameters.StringParameter.MakeChild()
    param_values = F.Parameters.StringParameter.MakeChild()  # comma-separated floats
    param_unit = F.Parameters.StringParameter.MakeChild()
    spice_param = F.Parameters.StringParameter.MakeChild()  # explicit SPICE param name

    # --- SPICE template with {param_name} placeholders ---
    spice_template = F.Parameters.StringParameter.MakeChild()
    extra_spice_template = F.Parameters.StringParameter.MakeChild()

    # --- Common config fields ---
    spice = F.Parameters.StringParameter.MakeChild()
    extra_spice = F.Parameters.StringParameter.MakeChild()
    remove_elements = F.Parameters.StringParameter.MakeChild()
    duts = F.Parameters.StringParameter.MakeChild()

    # --- Transient-specific fields (StringParameter for bare-number ato assignments) ---
    time_start = F.Parameters.StringParameter.MakeChild()
    time_stop = F.Parameters.StringParameter.MakeChild()
    time_step = F.Parameters.StringParameter.MakeChild()

    def get_param_name(self) -> str | None:
        return self.param_name.get().try_extract_singleton()

    def get_param_values(self) -> list[float]:
        """Parse comma-separated parameter values."""
        raw = self.param_values.get().try_extract_singleton()
        if raw is None:
            return []
        return [float(v.strip()) for v in raw.split(",") if v.strip()]

    def get_param_unit(self) -> str:
        raw = self.param_unit.get().try_extract_singleton()
        return raw or ""

    def get_spice_param(self) -> str | None:
        return self.spice_param.get().try_extract_singleton()

    def get_time_start_text(self) -> str | None:
        return _extract_text(self.time_start)

    def get_time_stop_text(self) -> str | None:
        return _extract_text(self.time_stop)

    def get_time_step_text(self) -> str | None:
        return _extract_text(self.time_step)

    def get_spice_template(self) -> str | None:
        return self.spice_template.get().try_extract_singleton()

    def get_extra_spice_template(self) -> str | None:
        return self.extra_spice_template.get().try_extract_singleton()

    def resolve_spice(self, value: float) -> str | None:
        """Substitute {param_name} in spice_template with the given value."""
        template = self.get_spice_template()
        if template is None:
            return self.get_spice()
        name = self.get_param_name() or "PARAM"
        return template.replace(f"{{{name}}}", str(value))

    def resolve_extra_spice(self, value: float) -> list[str]:
        """Substitute {param_name} in extra_spice_template with the given value."""
        template = self.get_extra_spice_template()
        if template is None:
            return self.get_extra_spice()
        name = self.get_param_name() or "PARAM"
        resolved = template.replace(f"{{{name}}}", str(value))
        return [line.strip() for line in resolved.split("|") if line.strip()]

    def get_spice(self) -> str | None:
        return self.spice.get().try_extract_singleton()

    def get_extra_spice(self) -> list[str]:
        return _parse_pipe_list(self.extra_spice)

    def get_remove_elements(self) -> list[str]:
        return _parse_comma_list(self.remove_elements)

    def get_duts(self) -> list[str]:
        return _parse_comma_list(self.duts)

    def get_time_start(self) -> float | None:
        return _extract_float(self.time_start, "time_start", "SimulationSweep")

    def get_time_stop(self) -> float | None:
        return _extract_float(self.time_stop, "time_stop", "SimulationSweep")

    def get_time_step(self) -> float | None:
        return _extract_float(self.time_step, "time_step", "SimulationSweep")
