# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


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


def _extract_float(param) -> float | None:
    """Extract a float from a StringParameter storing a numeric value.

    The ato compiler creates Numbers literals for bare numbers (e.g. ``2e-7``),
    even when the target is a StringParameter.  The primary extraction path
    fails in that case, so we fall back to extracting via the Numbers literal.
    """
    try:
        v = param.get().try_extract_singleton()
        return float(v) if v is not None else None
    except Exception:
        try:
            from faebryk.library.Literals import Numbers

            nums = param.get().is_parameter_operatable.get().try_extract_superset(
                lit_type=Numbers
            )
            if nums is not None:
                return float(nums.get_single())
        except Exception:
            pass
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

    # --- Common config fields ---
    spice = F.Parameters.StringParameter.MakeChild()
    extra_spice = F.Parameters.StringParameter.MakeChild()
    remove_elements = F.Parameters.StringParameter.MakeChild()

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

    def get_time_start(self) -> float | None:
        return _extract_float(self.time_start)

    def get_time_stop(self) -> float | None:
        return _extract_float(self.time_stop)

    def get_time_step(self) -> float | None:
        return _extract_float(self.time_step)


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

    # --- Common config fields ---
    spice = F.Parameters.StringParameter.MakeChild()
    extra_spice = F.Parameters.StringParameter.MakeChild()
    remove_elements = F.Parameters.StringParameter.MakeChild()

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

    def get_start_freq(self) -> float | None:
        return _extract_float(self.start_freq)

    def get_stop_freq(self) -> float | None:
        return _extract_float(self.stop_freq)

    def get_points_per_dec(self) -> int | None:
        v = _extract_float(self.points_per_dec)
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

    # --- Common config fields ---
    spice = F.Parameters.StringParameter.MakeChild()
    extra_spice = F.Parameters.StringParameter.MakeChild()
    remove_elements = F.Parameters.StringParameter.MakeChild()

    def get_spice(self) -> str | None:
        return self.spice.get().try_extract_singleton()

    def get_extra_spice(self) -> list[str]:
        return _parse_pipe_list(self.extra_spice)

    def get_remove_elements(self) -> list[str]:
        return _parse_comma_list(self.remove_elements)


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

    # --- Sweep parameters ---
    param_name = F.Parameters.StringParameter.MakeChild()
    param_values = F.Parameters.StringParameter.MakeChild()  # comma-separated floats
    param_unit = F.Parameters.StringParameter.MakeChild()

    # --- SPICE template with {param_name} placeholders ---
    spice_template = F.Parameters.StringParameter.MakeChild()
    extra_spice_template = F.Parameters.StringParameter.MakeChild()

    # --- Common config fields ---
    spice = F.Parameters.StringParameter.MakeChild()
    extra_spice = F.Parameters.StringParameter.MakeChild()
    remove_elements = F.Parameters.StringParameter.MakeChild()

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

    def get_time_start(self) -> float | None:
        return _extract_float(self.time_start)

    def get_time_stop(self) -> float | None:
        return _extract_float(self.time_stop)

    def get_time_step(self) -> float | None:
        return _extract_float(self.time_step)
