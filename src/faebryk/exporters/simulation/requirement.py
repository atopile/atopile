"""Graph-paradigm simulation requirements.

Each Requirement is a fabll.Node carrying bounds (min/typical/max),
referencing a net to check, and labeling context nets for plotting.

The `capture` field determines how data is acquired ("dcop" or "transient").
The `measurement` field determines what to compute ("final_value", "average", etc.).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path

import faebryk.library._F as F
from faebryk.exporters.simulation.ngspice import ACResult, Circuit, TransientResult

logger = logging.getLogger(__name__)


@dataclass
class RequirementResult:
    """Result of checking a single requirement."""

    requirement: F.Requirement
    actual: float
    passed: bool
    display_net: str = ""  # original ato address (e.g. "package.SW")
    resolved_net: str = ""  # canonical SPICE net (e.g. "package_8")
    resolved_diff_ref: str | None = None
    resolved_ctx_nets: list[str] | None = None


# ---------------------------------------------------------------------------
# Measurement dispatch
# ---------------------------------------------------------------------------


def _measure_dcop(measurement: str, op_value: float) -> float:
    """Compute measurement from a DCOP value."""
    # For DCOP, most measurements just return the OP value
    return op_value


def _slice_from(
    time_data: list[float],
    signal_data: list[float],
    start: float | None,
) -> tuple[list[float], list[float]]:
    """Return (time, signal) sliced to only include t >= start.

    If start is None or 0, returns the original data unchanged.
    """
    if not start or start <= 0:
        return time_data, signal_data
    for i, t in enumerate(time_data):
        if t >= start:
            return time_data[i:], signal_data[i:]
    return [], []


def _measure_tran(
    measurement: str,
    signal_data: list[float],
    time_data: list[float],
    settling_tolerance: float | None = None,
) -> float:
    """Compute measurement from transient data."""
    if not signal_data:
        return float("nan")

    if measurement == "final_value":
        return signal_data[-1]

    if measurement == "average":
        return sum(signal_data) / len(signal_data)

    if measurement == "settling_time":
        tol = settling_tolerance or 0.01
        final = signal_data[-1]
        if final == 0:
            return float("inf")
        band = abs(final * tol)
        for i in range(len(signal_data) - 1, -1, -1):
            if abs(signal_data[i] - final) > band:
                return time_data[i] if i < len(time_data) else float("inf")
        return 0.0

    if measurement == "peak_to_peak":
        return max(signal_data) - min(signal_data)

    if measurement == "overshoot":
        final = signal_data[-1]
        if final == 0:
            return float("inf")
        peak = max(signal_data)
        return (peak - final) / abs(final) * 100.0

    if measurement == "rms":
        mean_sq = sum(x * x for x in signal_data) / len(signal_data)
        return math.sqrt(mean_sq)

    if measurement == "sweep":
        return signal_data[-1]

    if measurement == "frequency":
        # Count rising-edge threshold crossings to determine frequency.
        # Threshold = midpoint between min and max of signal.
        if len(signal_data) < 3 or len(time_data) < 3:
            return float("nan")
        sig_min = min(signal_data)
        sig_max = max(signal_data)
        threshold = (sig_min + sig_max) / 2.0
        crossings: list[float] = []
        for i in range(len(signal_data) - 1):
            if signal_data[i] <= threshold < signal_data[i + 1]:
                # Linear interpolation to find crossing time
                frac = (threshold - signal_data[i]) / (
                    signal_data[i + 1] - signal_data[i]
                )
                t_cross = time_data[i] + frac * (time_data[i + 1] - time_data[i])
                crossings.append(t_cross)
        if len(crossings) < 2:
            return float("nan")
        total_time = crossings[-1] - crossings[0]
        num_cycles = len(crossings) - 1
        return num_cycles / total_time

    # Default: final value
    return signal_data[-1]


# ---------------------------------------------------------------------------
# Transient grouping
# ---------------------------------------------------------------------------


def _tran_group_key(req: F.Requirement) -> tuple:
    """Group key for transient requirements sharing the same config."""
    override = req.get_source_override()
    start = req.get_tran_start()
    extra = tuple(req.get_extra_spice()) or None
    removed = tuple(req.get_remove_elements()) or None
    return (
        req.get_tran_step(),
        req.get_tran_stop(),
        start if start and start > 0 else None,
        override[0] if override else None,
        override[1] if override else None,
        extra,
        removed,
    )


# ---------------------------------------------------------------------------
# AC grouping + measurement
# ---------------------------------------------------------------------------


def _ac_group_key(req: F.Requirement) -> tuple:
    """Group key for AC requirements sharing the same sweep config."""
    return (
        req.get_ac_start_freq(),
        req.get_ac_stop_freq(),
        req.get_ac_points_per_dec(),
        req.get_ac_source_name(),
        tuple(req.get_extra_spice()) or None,
        tuple(req.get_remove_elements()) or None,
    )


def _interpolate_at_freq(
    freq: list[float], values: list[float], target: float
) -> float:
    """Log-frequency interpolation of values at target frequency."""
    if not freq or target <= 0:
        return float("nan")
    if target <= freq[0]:
        return values[0]
    if target >= freq[-1]:
        return values[-1]
    for i in range(len(freq) - 1):
        if freq[i] <= target <= freq[i + 1]:
            # Log-scale interpolation on frequency axis
            log_f0 = math.log10(freq[i])
            log_f1 = math.log10(freq[i + 1])
            log_ft = math.log10(target)
            t = (log_ft - log_f0) / (log_f1 - log_f0) if log_f1 != log_f0 else 0.0
            return values[i] + t * (values[i + 1] - values[i])
    return values[-1]


def _measure_ac(
    measurement: str,
    ac_result: ACResult,
    net: str,
    ref_net: str | None,
    measure_freq: float | None,
) -> float:
    """Compute an AC measurement from frequency-domain data."""
    if measurement == "gain_db":
        if measure_freq is None:
            return float("nan")
        if ref_net:
            gain = ac_result.gain_db_relative(net, ref_net)
        else:
            gain = ac_result.gain_db(net)
        return _interpolate_at_freq(ac_result.freq, gain, measure_freq)

    if measurement == "phase_deg":
        if measure_freq is None:
            return float("nan")
        if ref_net:
            phase = ac_result.phase_deg_relative(net, ref_net)
        else:
            phase = ac_result.phase_deg(net)
        return _interpolate_at_freq(ac_result.freq, phase, measure_freq)

    if measurement == "bandwidth_3db":
        if ref_net:
            gain = ac_result.gain_db_relative(net, ref_net)
        else:
            gain = ac_result.gain_db(net)
        if not gain:
            return float("nan")
        dc_gain = gain[0]
        max_gain = max(gain)

        # High-pass case: DC gain is well below passband
        if max_gain - dc_gain > 3.0:
            threshold = max_gain - 3.0
            for i in range(len(gain) - 1):
                if gain[i] < threshold <= gain[i + 1]:
                    log_f0 = math.log10(ac_result.freq[i])
                    log_f1 = math.log10(ac_result.freq[i + 1])
                    if gain[i] == gain[i + 1]:
                        return ac_result.freq[i]
                    t = (threshold - gain[i]) / (gain[i + 1] - gain[i])
                    log_fc = log_f0 + t * (log_f1 - log_f0)
                    return 10 ** log_fc
            return float("nan")

        # Low-pass case: find where gain drops 3dB below DC
        threshold = dc_gain - 3.0
        for i in range(len(gain) - 1):
            if gain[i] >= threshold and gain[i + 1] < threshold:
                log_f0 = math.log10(ac_result.freq[i])
                log_f1 = math.log10(ac_result.freq[i + 1])
                if gain[i] == gain[i + 1]:
                    return ac_result.freq[i]
                t = (threshold - gain[i]) / (gain[i + 1] - gain[i])
                log_fc = log_f0 + t * (log_f1 - log_f0)
                return 10 ** log_fc
        return float("nan")

    if measurement == "bode_plot":
        # Actual value = DC gain (gain at lowest frequency)
        if ref_net:
            gain = ac_result.gain_db_relative(net, ref_net)
        else:
            gain = ac_result.gain_db(net)
        if not gain:
            return float("nan")
        return gain[0]

    return float("nan")


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------


def _req_net(req: F.Requirement, overrides: dict[int, _ResolvedNets] | None) -> str:
    """Get the resolved net name for *req* (SPICE-level)."""
    if overrides and id(req) in overrides:
        return overrides[id(req)].net
    return req.get_net()


def _req_diff_ref(
    req: F.Requirement, overrides: dict[int, _ResolvedNets] | None
) -> str | None:
    if overrides and id(req) in overrides:
        return overrides[id(req)].diff_ref_net
    return req.get_diff_ref_net()


def _req_ctx_nets(
    req: F.Requirement, overrides: dict[int, _ResolvedNets] | None
) -> list[str]:
    if overrides and id(req) in overrides:
        return overrides[id(req)].context_nets
    return req.get_context_nets()


def _result_net(result: "RequirementResult") -> str:
    """Get the resolved SPICE net from a RequirementResult."""
    return result.resolved_net or result.requirement.get_net()


def _result_diff_ref(result: "RequirementResult") -> str | None:
    if result.resolved_diff_ref is not None:
        return result.resolved_diff_ref
    return result.requirement.get_diff_ref_net()


def _result_ctx_nets(result: "RequirementResult") -> list[str]:
    if result.resolved_ctx_nets is not None:
        return result.resolved_ctx_nets
    return result.requirement.get_context_nets()


def verify_requirements(
    circuit: Circuit,
    requirements: list[F.Requirement],
    uic: bool = False,
    net_overrides: dict[int, _ResolvedNets] | None = None,
) -> tuple[list[RequirementResult], dict[tuple, TransientResult], dict[tuple, ACResult]]:
    """Run simulations and check all requirements.

    1. Partition requirements by capture type ("dcop", "transient", "ac").
    2. Run .op() once for all DCOP requirements.
    3. Group transient requirements by shared config (step/stop), run .tran() per group.
    4. Group AC requirements by shared config, run .ac() per group.
    5. For each requirement, apply its measurement to compute actual value.
    6. Check actual against [min_val, max_val].

    Returns (results, {tran_group_key: TransientResult}, {ac_group_key: ACResult}).
    """
    dcop_reqs: list[F.Requirement] = []
    tran_reqs: list[F.Requirement] = []
    ac_reqs: list[F.Requirement] = []

    for req in requirements:
        capture = req.get_capture()
        if capture == "transient":
            tran_reqs.append(req)
        elif capture == "ac":
            ac_reqs.append(req)
        else:
            dcop_reqs.append(req)

    results: list[RequirementResult] = []

    # -- DCOP analysis --
    if dcop_reqs:
        op = circuit.op()
        for req in dcop_reqs:
            measurement = req.get_measurement()
            actual = _measure_dcop(measurement, op[_req_net(req, net_overrides)])
            passed = req.get_min_val() <= actual <= req.get_max_val()
            results.append(RequirementResult(requirement=req, actual=actual, passed=passed))

    # -- Transient analysis --
    tran_data: dict[tuple, TransientResult] = {}
    if tran_reqs:
        # Group by shared transient config
        groups: dict[tuple, list[F.Requirement]] = {}
        for req in tran_reqs:
            key = _tran_group_key(req)
            groups.setdefault(key, []).append(req)

        for key, group in groups.items():
            first = group[0]

            # Save circuit state so modifications are isolated per group
            saved_state = circuit.save_state()

            try:
                override = first.get_source_override()
                if override is not None:
                    circuit.set_source(override[0], override[1])

                # Apply circuit modifications (remove/add elements)
                for name in first.get_remove_elements():
                    circuit.remove_element(name)
                for line in first.get_extra_spice():
                    circuit.add_element(line)

                # Collect all signals needed
                signals: list[str] = []
                seen: set[str] = set()
                for req in group:
                    for net in [_req_net(req, net_overrides),
                                *_req_ctx_nets(req, net_overrides)]:
                        sig = (
                            f"v({net})"
                            if not net.startswith(("v(", "i("))
                            else net
                        )
                        if sig not in seen:
                            signals.append(sig)
                            seen.add(sig)
                    diff_ref = _req_diff_ref(req, net_overrides)
                    if diff_ref:
                        diff_sig = (
                            f"v({diff_ref})"
                            if not diff_ref.startswith(("v(", "i("))
                            else diff_ref
                        )
                        if diff_sig not in seen:
                            signals.append(diff_sig)
                            seen.add(diff_sig)

                step = first.get_tran_step()
                stop = first.get_tran_stop()
                start = first.get_tran_start() or 0
                if step is None or stop is None:
                    raise ValueError(
                        f"Transient requirement '{first.get_name()}' "
                        "missing tran_step or tran_stop"
                    )

                tran_result = circuit.tran(
                    step=step, stop=stop, start=start, signals=signals, uic=uic
                )
                tran_data[key] = tran_result

                for req in group:
                    net = _req_net(req, net_overrides)
                    sig_key = (
                        f"v({net})"
                        if not net.startswith(("v(", "i("))
                        else net
                    )
                    diff_ref = _req_diff_ref(req, net_overrides)
                    if diff_ref:
                        ref_key = (
                            f"v({diff_ref})"
                            if not diff_ref.startswith(("v(", "i("))
                            else diff_ref
                        )
                        signal_data = [
                            a - b
                            for a, b in zip(
                                tran_result[sig_key], tran_result[ref_key]
                            )
                        ]
                    else:
                        signal_data = tran_result[sig_key]
                    time_data, meas_data = _slice_from(
                        tran_result.time, signal_data, req.get_tran_start()
                    )
                    measurement = req.get_measurement()
                    actual = _measure_tran(
                        measurement,
                        meas_data,
                        time_data,
                        settling_tolerance=req.get_settling_tolerance(),
                    )
                    passed = req.get_min_val() <= actual <= req.get_max_val()
                    results.append(
                        RequirementResult(
                            requirement=req, actual=actual, passed=passed
                        )
                    )
            except Exception:
                req_names = [r.get_name() for r in group]
                logger.warning(
                    f"Transient group failed for {req_names} — skipping",
                    exc_info=True,
                )
            finally:
                # Restore circuit state for next group
                circuit.restore_state(saved_state)

    # -- AC analysis --
    ac_data: dict[tuple, ACResult] = {}
    if ac_reqs:
        ac_groups: dict[tuple, list[F.Requirement]] = {}
        for req in ac_reqs:
            key = _ac_group_key(req)
            ac_groups.setdefault(key, []).append(req)

        for key, group in ac_groups.items():
            first = group[0]

            # Save circuit state so modifications are isolated per group
            saved_state = circuit.save_state()

            try:
                # Apply circuit modifications (remove/add elements)
                for name in first.get_remove_elements():
                    circuit.remove_element(name)
                for line in first.get_extra_spice():
                    circuit.add_element(line)

                # Set up AC source: append "AC 1" to the existing source spec
                ac_source = first.get_ac_source_name()
                if ac_source:
                    existing_spec = circuit.get_source_spec(ac_source)
                    if existing_spec:
                        # Append AC 1 if not already present
                        if "AC" not in existing_spec.upper():
                            circuit.set_source(ac_source, f"{existing_spec} AC 1")
                    else:
                        circuit.set_source(ac_source, "DC 0 AC 1")

                # Collect all signals needed
                signals: list[str] = []
                seen: set[str] = set()
                for req in group:
                    net = _req_net(req, net_overrides)
                    sig = f"v({net})" if not net.startswith(("v(", "i(")) else net
                    if sig not in seen:
                        signals.append(sig)
                        seen.add(sig)
                    ref_net = req.get_ac_ref_net()
                    if ref_net:
                        ref_sig = (
                            f"v({ref_net})"
                            if not ref_net.startswith(("v(", "i("))
                            else ref_net
                        )
                        if ref_sig not in seen:
                            signals.append(ref_sig)
                            seen.add(ref_sig)
                    diff_ref = _req_diff_ref(req, net_overrides)
                    if diff_ref:
                        diff_sig = (
                            f"v({diff_ref})"
                            if not diff_ref.startswith(("v(", "i("))
                            else diff_ref
                        )
                        if diff_sig not in seen:
                            signals.append(diff_sig)
                            seen.add(diff_sig)

                start = first.get_ac_start_freq()
                stop = first.get_ac_stop_freq()
                ppd = first.get_ac_points_per_dec() or 100
                if start is None or stop is None:
                    raise ValueError(
                        f"AC requirement '{first.get_name()}' "
                        "missing ac_start_freq or ac_stop_freq"
                    )

                ac_result = circuit.ac(
                    start_freq=start,
                    stop_freq=stop,
                    points_per_decade=ppd,
                    signals=signals,
                )
                ac_data[key] = ac_result

                for req in group:
                    net = _req_net(req, net_overrides)
                    ref_net = req.get_ac_ref_net()
                    measurement = req.get_measurement()
                    measure_freq = req.get_ac_measure_freq()
                    diff_ref = _req_diff_ref(req, net_overrides)
                    if diff_ref:
                        diff_key = ac_result.compute_diff(net, diff_ref)
                        actual = _measure_ac(
                            measurement, ac_result, diff_key, ref_net, measure_freq
                        )
                    else:
                        actual = _measure_ac(
                            measurement, ac_result, net, ref_net, measure_freq
                        )
                    passed = req.get_min_val() <= actual <= req.get_max_val()
                    results.append(
                        RequirementResult(
                            requirement=req, actual=actual, passed=passed
                        )
                    )
            except Exception:
                req_names = [r.get_name() for r in group]
                logger.warning(
                    f"AC group failed for {req_names} — skipping",
                    exc_info=True,
                )
            finally:
                # Restore circuit state for next group
                circuit.restore_state(saved_state)

    return results, tran_data, ac_data


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

# SI prefix table for engineering notation
_SI_PREFIXES = [
    (1e-15, "f"),
    (1e-12, "p"),
    (1e-9, "n"),
    (1e-6, "u"),
    (1e-3, "m"),
    (1.0, ""),
    (1e3, "k"),
    (1e6, "M"),
    (1e9, "G"),
]


def _auto_scale_time(t_max: float) -> tuple[float, str]:
    """Choose time unit scale factor and label."""
    if t_max <= 0:
        return 1.0, "s"
    if t_max < 1e-6:
        return 1e9, "ns"
    if t_max < 1e-3:
        return 1e6, "us"
    if t_max < 1.0:
        return 1e3, "ms"
    return 1.0, "s"


def _signal_unit(key: str) -> str:
    """Infer unit type from signal key: 'V' for voltage, 'A' for current."""
    if key.startswith("i("):
        return "A"
    return "V"


def _format_eng(value: float, unit: str) -> str:
    """Format a value in engineering notation with SI prefix.

    Examples:
        _format_eng(7.5, "V")   → "7.500 V"
        _format_eng(0.3, "s")   → "300.0 ms"
        _format_eng(12.5, "%")  → "12.50%"
    """
    if unit == "%":
        return f"{value:.2f}%"

    abs_val = abs(value)
    if abs_val == 0:
        return f"0.000 {unit}"

    for threshold, prefix in _SI_PREFIXES:
        if abs_val < threshold * 1000:
            scaled = value / threshold
            return f"{scaled:.4g} {prefix}{unit}"

    # Fallback for very large values
    return f"{value:.4g} {unit}"


_CTX_COLORS = ["orange", "green", "purple", "brown"]


def _setup_common_plot(
    result: RequirementResult,
    tran_data: TransientResult,
) -> tuple[
    "go.Figure",
    list[float],  # time_scaled
    list[float],  # nut_signal
    str,  # nut_unit
    float,  # scale
    str,  # t_unit
    bool,  # has_secondary_y
]:
    """Create figure, plot NUT + context signals, return figure and data."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    req = result.requirement
    net = _result_net(result)
    context_nets = _result_ctx_nets(result)
    net_key = f"v({net})" if not net.startswith(("v(", "i(")) else net
    nut_unit = _signal_unit(net_key)

    # Auto-scale time axis (ngspice already limits data to [start, stop])
    t_max = tran_data.time[-1] if tran_data.time else 1.0
    scale, t_unit = _auto_scale_time(t_max)
    time_scaled = [t * scale for t in tran_data.time]

    # Compute differential signal if diff_ref_net is set
    diff_ref = _result_diff_ref(result)
    if diff_ref:
        ref_key = (
            f"v({diff_ref})"
            if not diff_ref.startswith(("v(", "i("))
            else diff_ref
        )
        nut_signal = [
            a - b for a, b in zip(tran_data[net_key], tran_data[ref_key])
        ]
        net_key = f"{net_key} - {ref_key}"
    else:
        nut_signal = tran_data[net_key]

    # Partition context signals by unit
    same_unit: list[str] = []
    diff_unit: list[str] = []
    for ctx_net in context_nets:
        ctx_key = (
            f"v({ctx_net})" if not ctx_net.startswith(("v(", "i(")) else ctx_net
        )
        if ctx_key in tran_data:
            if _signal_unit(ctx_key) == nut_unit:
                same_unit.append(ctx_key)
            else:
                diff_unit.append(ctx_key)

    has_secondary = bool(diff_unit)
    if has_secondary:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    # NUT signal (thick blue) — use ato address as label when available
    nut_label = result.display_net if result.display_net else net_key
    fig.add_trace(
        go.Scatter(
            x=time_scaled,
            y=nut_signal,
            mode="lines",
            name=nut_label,
            line=dict(color="royalblue", width=3),
        ),
        secondary_y=False if has_secondary else None,
    )

    # Same-unit context signals (thin, left axis)
    for i, ctx_key in enumerate(same_unit):
        c = _CTX_COLORS[i % len(_CTX_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=time_scaled,
                y=list(tran_data[ctx_key]),
                mode="lines",
                name=ctx_key,
                line=dict(color=c, width=1.2),
            ),
            secondary_y=False if has_secondary else None,
        )

    unit_label = (
        f"Voltage ({nut_unit})" if nut_unit == "V" else f"Current ({nut_unit})"
    )

    # Different-unit context signals (right axis)
    if has_secondary:
        for i, ctx_key in enumerate(diff_unit):
            c = _CTX_COLORS[(i + len(same_unit)) % len(_CTX_COLORS)]
            fig.add_trace(
                go.Scatter(
                    x=time_scaled,
                    y=list(tran_data[ctx_key]),
                    mode="lines",
                    name=ctx_key,
                    line=dict(color=c, width=1.2),
                ),
                secondary_y=True,
            )
        diff_unit_type = _signal_unit(diff_unit[0])
        right_label = (
            f"Voltage ({diff_unit_type})"
            if diff_unit_type == "V"
            else f"Current ({diff_unit_type})"
        )
        fig.update_yaxes(title_text=right_label, secondary_y=True)

    fig.update_xaxes(title_text=f"Time ({t_unit})")
    fig.update_yaxes(
        title_text=unit_label,
        secondary_y=False if has_secondary else None,
    )

    return fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_secondary


def _add_limit_labels(
    fig: "go.Figure",
    min_val: float,
    max_val: float,
    unit: str,
) -> None:
    """Add horizontal limit lines with text annotations."""
    fig.add_hline(y=min_val, line=dict(color="red", dash="dot", width=2))
    fig.add_hline(y=max_val, line=dict(color="red", dash="dot", width=2))

    fig.add_annotation(
        x=0.02, y=min_val, xref="paper", yref="y",
        text=f"LSL = {_format_eng(min_val, unit)}",
        showarrow=False, font=dict(color="red", size=10),
        xanchor="left", yanchor="bottom",
    )
    fig.add_annotation(
        x=0.98, y=max_val, xref="paper", yref="y",
        text=f"USL = {_format_eng(max_val, unit)}",
        showarrow=False, font=dict(color="red", size=10),
        xanchor="right", yanchor="top",
    )


def _add_time_limit_labels(
    fig: "go.Figure",
    min_val: float,
    max_val: float,
    scale: float,
    t_unit: str,
) -> None:
    """Add vertical limit lines at time values with text annotations."""
    min_scaled = min_val * scale
    max_scaled = max_val * scale
    fig.add_vline(x=min_scaled, line=dict(color="red", dash="dot", width=2))
    fig.add_vline(x=max_scaled, line=dict(color="red", dash="dot", width=2))

    fig.add_annotation(
        x=min_scaled, y=0.98, xref="x", yref="paper",
        text=f"LSL = {_format_eng(min_val, 's')}",
        showarrow=False, font=dict(color="red", size=10),
        xanchor="right", yanchor="top", textangle=-90,
    )
    fig.add_annotation(
        x=max_scaled, y=0.98, xref="x", yref="paper",
        text=f"USL = {_format_eng(max_val, 's')}",
        showarrow=False, font=dict(color="red", size=10),
        xanchor="left", yanchor="top", textangle=-90,
    )


def _finalize_plot(
    fig: "go.Figure",
    title: str,
    subtitle: str,
    time_scaled: list[float],
    path: Path,
) -> Path:
    """Apply layout, save as HTML."""
    t_margin = 0.0
    if time_scaled:
        t_span = time_scaled[-1] - time_scaled[0]
        t_margin = 0.05 * t_span

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b><br><span style='font-size:12px;color:gray'>"
                 f"{subtitle}</span>",
            x=0.5,
        ),
        width=900,
        height=500,
        template="plotly_white",
        showlegend=True,
        legend=dict(font=dict(size=10), x=0.01, y=0.99, xanchor="left", yanchor="top"),
    )

    if time_scaled:
        fig.update_xaxes(
            range=[
                time_scaled[0] - t_margin,
                time_scaled[-1] + t_margin,
            ]
        )

    fig.write_html(str(path))
    return path


def _compute_settling_milestones(
    signal_data: list[float],
    time_data: list[float],
    final: float,
) -> list[tuple[float, float, str]]:
    """Compute 90%, 95%, 99% settling times.

    Returns list of (time, tolerance_pct, label) tuples.
    """
    if final == 0:
        return []

    milestones = []
    for pct, tol in [(90, 0.10), (95, 0.05), (99, 0.01)]:
        band = abs(final * tol)
        settled_time = 0.0
        for i in range(len(signal_data) - 1, -1, -1):
            if abs(signal_data[i] - final) > band:
                settled_time = time_data[i] if i < len(time_data) else float("inf")
                break
        if settled_time != float("inf"):
            milestones.append((settled_time, pct, f"{pct}%"))
    return milestones


# ---------------------------------------------------------------------------
# Per-measurement plot functions
# ---------------------------------------------------------------------------


def _plot_final_value(
    result: RequirementResult,
    tran_data: TransientResult,
    path: Path,
) -> Path:
    """Plot for FinalValue measurement: horizontal limits, pass band, actual marker."""
    import plotly.graph_objects as go

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()

    fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
        _setup_common_plot(result, tran_data)
    )

    # Pass band shading
    fig.add_hrect(y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
                  line_width=0)

    # Horizontal limit lines with labels
    _add_limit_labels(fig, min_val, max_val, nut_unit)

    # Actual value line and marker
    actual = result.actual
    marker_color = "#2ecc71" if result.passed else "#e74c3c"
    fig.add_hline(y=actual, line=dict(color=marker_color, dash="dash", width=1.5),
                  opacity=0.7)
    fig.add_trace(go.Scatter(
        x=[time_scaled[-1]], y=[actual],
        mode="markers+text",
        marker=dict(color=marker_color, size=10),
        text=[f"Actual = {_format_eng(actual, nut_unit)}"],
        textposition="top left",
        textfont=dict(color=marker_color, size=11),
        showlegend=False,
    ))

    # Margin annotation
    margin_lo = abs(actual - min_val)
    margin_hi = abs(max_val - actual)
    nearest = min(margin_lo, margin_hi)
    span = max_val - min_val
    margin_pct = (nearest / span * 100) if span > 0 else 0
    fig.add_annotation(
        x=0.02, y=0.02, xref="paper", yref="paper",
        text=f"Margin: {margin_pct:.1f}% to nearest limit",
        showarrow=False, font=dict(color="gray", size=10),
        xanchor="left", yanchor="bottom",
    )

    subtitle = f"Measurement: final_value | Actual: {_format_eng(actual, nut_unit)}"
    return _finalize_plot(fig, req.get_name(), subtitle, time_scaled, path)


def _plot_average_value(
    result: RequirementResult,
    tran_data: TransientResult,
    path: Path,
) -> Path:
    """Plot for AverageValue measurement: mean line, deviation shading."""
    import plotly.graph_objects as go

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()

    fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
        _setup_common_plot(result, tran_data)
    )

    avg = result.actual

    # Pass band shading
    fig.add_hrect(y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
                  line_width=0)

    # Horizontal limit lines with labels
    _add_limit_labels(fig, min_val, max_val, nut_unit)

    # Average line
    fig.add_hline(y=avg, line=dict(color="royalblue", dash="dash", width=1.5),
                  opacity=0.7)
    fig.add_annotation(
        x=time_scaled[len(time_scaled) // 2], y=avg,
        text=f"<b>Avg = {_format_eng(avg, nut_unit)}</b>",
        showarrow=False, font=dict(color="royalblue", size=11),
        yshift=12,
    )

    # Deviation fill (upper bound = signal, lower bound = avg)
    fig.add_trace(go.Scatter(
        x=time_scaled, y=[avg] * len(nut_signal),
        mode="lines", line=dict(width=0), showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=time_scaled, y=list(nut_signal),
        mode="lines", line=dict(width=0), fill="tonexty",
        fillcolor="rgba(65,105,225,0.15)", showlegend=False,
    ))

    # Std dev info
    mean_sq_dev = sum((x - avg) ** 2 for x in nut_signal) / len(nut_signal)
    std_dev = math.sqrt(mean_sq_dev)
    fig.add_annotation(
        x=0.02, y=0.02, xref="paper", yref="paper",
        text=f"Std Dev: {_format_eng(std_dev, nut_unit)}",
        showarrow=False, font=dict(color="gray", size=10),
        xanchor="left", yanchor="bottom",
    )

    subtitle = f"Measurement: average | Actual: {_format_eng(avg, nut_unit)}"
    return _finalize_plot(fig, req.get_name(), subtitle, time_scaled, path)


def _plot_settling_time(
    result: RequirementResult,
    tran_data: TransientResult,
    path: Path,
) -> Path:
    """Plot for SettlingTime: vertical time limits, tolerance band, milestones."""
    import plotly.graph_objects as go

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()

    fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
        _setup_common_plot(result, tran_data)
    )

    final = nut_signal[-1] if nut_signal else 0.0
    tol = req.get_settling_tolerance() or 0.01
    band = abs(final * tol)

    # Final value reference line
    fig.add_hline(y=final, line=dict(color="gray", dash="dash", width=1.2),
                  opacity=0.7)
    fig.add_annotation(
        x=time_scaled[-1], y=final,
        text=f"Final = {_format_eng(final, nut_unit)}",
        showarrow=True, arrowhead=0, ax=-80, ay=-15,
        font=dict(color="gray", size=11),
    )

    # Settling tolerance band
    fig.add_hline(y=final + band, line=dict(color="gray", dash="dot", width=1),
                  opacity=0.5)
    fig.add_hline(y=final - band, line=dict(color="gray", dash="dot", width=1),
                  opacity=0.5)
    fig.add_hrect(y0=final - band, y1=final + band, fillcolor="green",
                  opacity=0.08, line_width=0)
    fig.add_annotation(
        x=0.98, y=final + band, xref="paper", yref="y",
        text=f"+/-{tol * 100:.1f}% band",
        showarrow=False, font=dict(color="green", size=9),
        xanchor="left", yanchor="bottom",
    )

    # Vertical time limit lines (bounds are time values)
    _add_time_limit_labels(fig, min_val, max_val, scale, t_unit)

    # Actual settling time vertical line
    actual = result.actual
    actual_scaled = actual * scale
    settle_color = "#2ecc71" if result.passed else "#e74c3c"
    fig.add_vline(x=actual_scaled, line=dict(color=settle_color, dash="dash",
                  width=2), opacity=0.8)
    fig.add_annotation(
        x=actual_scaled, y=0.85, xref="x", yref="paper",
        text=f"<b>Settled @ {_format_eng(actual, 's')}</b>",
        showarrow=False, font=dict(color=settle_color, size=11),
        textangle=-90, xanchor="right", yanchor="top",
    )

    # Settling milestones (90%, 95%, 99%)
    milestones = _compute_settling_milestones(
        nut_signal, [t / scale for t in time_scaled], final
    )
    milestone_colors = ["#f39c12", "#e67e22", "#8e44ad"]
    milestone_symbols = ["diamond", "diamond", "diamond"]
    for idx, (m_time, m_pct, m_label) in enumerate(milestones):
        m_time_scaled = m_time * scale
        m_idx = 0
        for j, t in enumerate(time_scaled):
            if t >= m_time_scaled:
                m_idx = j
                break
        m_color = milestone_colors[idx % len(milestone_colors)]
        fig.add_trace(go.Scatter(
            x=[m_time_scaled], y=[nut_signal[m_idx]],
            mode="markers",
            marker=dict(color=m_color, size=9,
                        symbol=milestone_symbols[idx % len(milestone_symbols)]),
            showlegend=False,
        ))
        fig.add_annotation(
            x=m_time_scaled, y=nut_signal[m_idx],
            text=f"<b>{m_label} @ {_format_eng(m_time, 's')}</b>",
            showarrow=True, arrowhead=2, arrowcolor=m_color,
            ax=10, ay=-(10 + idx * 18),
            font=dict(color=m_color, size=9),
        )

    subtitle = f"Measurement: settling_time | Actual: {_format_eng(actual, 's')}"
    return _finalize_plot(fig, req.get_name(), subtitle, time_scaled, path)


def _plot_peak_to_peak(
    result: RequirementResult,
    tran_data: TransientResult,
    path: Path,
) -> Path:
    """Plot for PeakToPeak: peak/trough markers, double arrow, info box."""
    import plotly.graph_objects as go

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()

    fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
        _setup_common_plot(result, tran_data)
    )

    peak_val = max(nut_signal)
    trough_val = min(nut_signal)
    peak_idx = nut_signal.index(peak_val)
    trough_idx = nut_signal.index(trough_val)
    actual = result.actual

    # Peak and trough markers
    fig.add_trace(go.Scatter(
        x=[time_scaled[peak_idx]], y=[peak_val],
        mode="markers",
        marker=dict(color="#e74c3c", size=12, symbol="triangle-up"),
        name=f"Peak = {_format_eng(peak_val, nut_unit)}",
    ))
    fig.add_trace(go.Scatter(
        x=[time_scaled[trough_idx]], y=[trough_val],
        mode="markers",
        marker=dict(color="#3498db", size=12, symbol="triangle-down"),
        name=f"Trough = {_format_eng(trough_val, nut_unit)}",
    ))

    # Horizontal lines at peak and trough
    fig.add_hline(y=peak_val, line=dict(color="#e74c3c", dash="dot", width=1),
                  opacity=0.4)
    fig.add_hline(y=trough_val, line=dict(color="#3498db", dash="dot", width=1),
                  opacity=0.4)

    # P-P label at midpoint
    mid_y = (peak_val + trough_val) / 2
    arrow_x = time_scaled[-1] * 0.95
    fig.add_annotation(
        x=arrow_x, y=peak_val, ax=arrow_x, ay=trough_val,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=3, arrowsize=1.5, arrowwidth=2,
        arrowcolor="black", text="",
    )
    fig.add_annotation(
        x=arrow_x, y=mid_y,
        text=f"<b>P-P: {_format_eng(actual, nut_unit)}</b>",
        showarrow=False, font=dict(size=11),
        xanchor="right",
        bgcolor="rgba(255,255,255,0.8)", bordercolor="gray", borderwidth=1,
    )

    # Annotations for peak/trough times
    peak_time = time_scaled[peak_idx] / scale
    trough_time = time_scaled[trough_idx] / scale
    fig.add_annotation(
        x=time_scaled[peak_idx], y=peak_val,
        text=f"@ {_format_eng(peak_time, 's')}",
        showarrow=True, arrowhead=0, ax=10, ay=-15,
        font=dict(color="#e74c3c", size=9),
    )
    fig.add_annotation(
        x=time_scaled[trough_idx], y=trough_val,
        text=f"@ {_format_eng(trough_time, 's')}",
        showarrow=True, arrowhead=0, ax=10, ay=15,
        font=dict(color="#3498db", size=9),
    )

    # Info box
    margin_lo = abs(actual - min_val)
    margin_hi = abs(max_val - actual)
    nearest = min(margin_lo, margin_hi)
    span = max_val - min_val
    margin_pct = (nearest / span * 100) if span > 0 else 0
    info_text = (
        f"P-P: {_format_eng(actual, nut_unit)}<br>"
        f"Limit: [{_format_eng(min_val, nut_unit)}, "
        f"{_format_eng(max_val, nut_unit)}]<br>"
        f"Margin: {margin_pct:.1f}%"
    )
    fig.add_annotation(
        x=0.02, y=0.02, xref="paper", yref="paper",
        text=info_text, showarrow=False,
        font=dict(color="gray", size=10, family="monospace"),
        xanchor="left", yanchor="bottom", align="left",
    )

    subtitle = (
        f"Measurement: peak_to_peak | Actual: {_format_eng(actual, nut_unit)}"
    )
    return _finalize_plot(fig, req.get_name(), subtitle, time_scaled, path)


def _plot_overshoot(
    result: RequirementResult,
    tran_data: TransientResult,
    path: Path,
) -> Path:
    """Plot for Overshoot: final line, peak marker, overshoot arrow, red fill."""
    import plotly.graph_objects as go

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()

    fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
        _setup_common_plot(result, tran_data)
    )

    final = nut_signal[-1] if nut_signal else 0.0
    peak_val = max(nut_signal)
    peak_idx = nut_signal.index(peak_val)
    actual = result.actual  # overshoot percentage

    # Final value line
    fig.add_hline(y=final, line=dict(color="gray", dash="dash", width=1.5),
                  opacity=0.7)
    fig.add_annotation(
        x=time_scaled[-1], y=final,
        text=f"Final = {_format_eng(final, nut_unit)}",
        showarrow=True, arrowhead=0, ax=-80, ay=-15,
        font=dict(color="gray", size=11),
    )

    # Max allowed overshoot line
    if final != 0:
        max_os_voltage = final * (1 + max_val / 100.0)
        fig.add_hline(y=max_os_voltage,
                      line=dict(color="red", dash="dash", width=1.2), opacity=0.6)
        fig.add_annotation(
            x=0.02, y=max_os_voltage, xref="paper", yref="y",
            text=f"Max OS = {max_val:.1f}%",
            showarrow=False, font=dict(color="red", size=10),
            xanchor="left", yanchor="bottom",
        )

    # Peak marker
    fig.add_trace(go.Scatter(
        x=[time_scaled[peak_idx]], y=[peak_val],
        mode="markers",
        marker=dict(color="#e74c3c", size=10),
        showlegend=False,
    ))

    # Overshoot arrow from final to peak
    fig.add_annotation(
        x=time_scaled[peak_idx], y=peak_val,
        ax=time_scaled[peak_idx], ay=final,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=3, arrowsize=1.5, arrowwidth=1.5,
        arrowcolor="#e74c3c", text="",
    )
    fig.add_annotation(
        x=time_scaled[peak_idx], y=(peak_val + final) / 2,
        text=f"<b>OS = {actual:.2f}%</b>",
        showarrow=False, font=dict(color="#e74c3c", size=11),
        xanchor="left", xshift=8,
    )

    # Red fill where signal exceeds final
    fill_y_upper = [s if s > final else final for s in nut_signal]
    fig.add_trace(go.Scatter(
        x=time_scaled, y=[final] * len(nut_signal),
        mode="lines", line=dict(width=0), showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=time_scaled, y=fill_y_upper,
        mode="lines", line=dict(width=0), fill="tonexty",
        fillcolor="rgba(231,76,60,0.15)", showlegend=False,
    ))

    # Info box
    info_text = (
        f"Overshoot: {actual:.2f}%<br>"
        f"Limit: [{min_val:.1f}%, {max_val:.1f}%]<br>"
        f"Peak: {_format_eng(peak_val, nut_unit)}<br>"
        f"Final: {_format_eng(final, nut_unit)}"
    )
    fig.add_annotation(
        x=0.02, y=0.02, xref="paper", yref="paper",
        text=info_text, showarrow=False,
        font=dict(color="gray", size=10, family="monospace"),
        xanchor="left", yanchor="bottom", align="left",
    )

    subtitle = f"Measurement: overshoot | Actual: {actual:.2f}%"
    return _finalize_plot(fig, req.get_name(), subtitle, time_scaled, path)


def _plot_rms(
    result: RequirementResult,
    tran_data: TransientResult,
    path: Path,
) -> Path:
    """Plot for RMS measurement: RMS line, mean line, pass band, crest factor."""
    import plotly.graph_objects as go  # noqa: F811

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()

    fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
        _setup_common_plot(result, tran_data)
    )

    rms = result.actual
    mean = sum(nut_signal) / len(nut_signal) if nut_signal else 0.0
    peak = max(abs(s) for s in nut_signal) if nut_signal else 0.0
    crest = peak / rms if rms > 0 else float("inf")

    # Pass band shading
    fig.add_hrect(y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
                  line_width=0)

    # Horizontal limit lines with labels
    _add_limit_labels(fig, min_val, max_val, nut_unit)

    # RMS line
    fig.add_hline(y=rms, line=dict(color="royalblue", dash="dash", width=1.5),
                  opacity=0.7)
    fig.add_annotation(
        x=time_scaled[len(time_scaled) // 2], y=rms,
        text=f"<b>RMS = {_format_eng(rms, nut_unit)}</b>",
        showarrow=False, font=dict(color="royalblue", size=11),
        yshift=12,
    )

    # Mean line (muted)
    fig.add_hline(y=mean, line=dict(color="gray", dash="dot", width=1.2),
                  opacity=0.6)
    fig.add_annotation(
        x=time_scaled[len(time_scaled) // 3], y=mean,
        text=f"Mean = {_format_eng(mean, nut_unit)}",
        showarrow=False, font=dict(color="gray", size=10),
        yshift=-12,
    )

    # Info box
    info_text = (
        f"RMS: {_format_eng(rms, nut_unit)}<br>"
        f"Mean: {_format_eng(mean, nut_unit)}<br>"
        f"Peak: {_format_eng(peak, nut_unit)}<br>"
        f"Crest Factor: {crest:.2f}"
    )
    fig.add_annotation(
        x=0.02, y=0.02, xref="paper", yref="paper",
        text=info_text, showarrow=False,
        font=dict(color="gray", size=10, family="monospace"),
        xanchor="left", yanchor="bottom", align="left",
    )

    subtitle = f"Measurement: rms | Actual: {_format_eng(rms, nut_unit)}"
    return _finalize_plot(fig, req.get_name(), subtitle, time_scaled, path)


def _plot_frequency(
    result: RequirementResult,
    tran_data: TransientResult,
    path: Path,
) -> Path:
    """Plot for Frequency measurement: signal waveform with cycle markers."""
    import plotly.graph_objects as go

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()

    fig, time_scaled, nut_signal, nut_unit, scale, t_unit, has_sec = (
        _setup_common_plot(result, tran_data)
    )

    actual = result.actual  # Hz

    # Frequency pass band (horizontal lines in Hz don't apply to time-domain Y,
    # so we annotate with vertical markers and an info box instead)

    # Mark a few rising-edge crossings on the waveform
    sig_min = min(nut_signal)
    sig_max = max(nut_signal)
    threshold = (sig_min + sig_max) / 2.0

    crossing_times: list[float] = []
    crossing_vals: list[float] = []
    for i in range(len(nut_signal) - 1):
        if nut_signal[i] <= threshold < nut_signal[i + 1]:
            frac = (threshold - nut_signal[i]) / (
                nut_signal[i + 1] - nut_signal[i]
            )
            t_cross = time_scaled[i] + frac * (time_scaled[i + 1] - time_scaled[i])
            crossing_times.append(t_cross)
            crossing_vals.append(threshold)

    # Threshold line
    fig.add_hline(
        y=threshold,
        line=dict(color="gray", dash="dot", width=1),
        opacity=0.4,
    )

    marker_color = "#2ecc71" if result.passed else "#e74c3c"

    # Highlight one cycle: two consecutive rising edges with a
    # double-arrow showing the measured period.
    # Pick a pair near the middle of the data for a representative sample.
    if len(crossing_times) >= 2:
        mid = len(crossing_times) // 2
        t0 = crossing_times[mid - 1]
        t1 = crossing_times[mid]
        period = (t1 - t0) / scale  # back to seconds for formatting

        # Markers on the two edges
        fig.add_trace(go.Scatter(
            x=[t0, t1],
            y=[threshold, threshold],
            mode="markers",
            marker=dict(color=marker_color, size=10, symbol="circle",
                        line=dict(color="white", width=2)),
            name="Measured edges",
            showlegend=True,
        ))

        # Double-arrow between the two edges (at the peak for visibility)
        arrow_y = sig_max * 0.95
        fig.add_shape(
            type="line",
            x0=t0, x1=t1, y0=arrow_y, y1=arrow_y,
            line=dict(color="black", width=1.5),
        )
        # Vertical drop-lines from arrow to crossing points
        fig.add_shape(
            type="line",
            x0=t0, x1=t0, y0=threshold, y1=arrow_y,
            line=dict(color="black", width=1, dash="dot"),
        )
        fig.add_shape(
            type="line",
            x0=t1, x1=t1, y0=threshold, y1=arrow_y,
            line=dict(color="black", width=1, dash="dot"),
        )

        # Period label at the midpoint of the arrow
        fig.add_annotation(
            x=(t0 + t1) / 2, y=arrow_y,
            text=f"T = {_format_eng(period, 's')}",
            showarrow=False,
            font=dict(color="black", size=11),
            yshift=12,
        )

    # Info box with frequency result
    info_text = (
        f"Frequency: {_format_eng(actual, 'Hz')}<br>"
        f"Limit: [{_format_eng(min_val, 'Hz')}, "
        f"{_format_eng(max_val, 'Hz')}]<br>"
        f"Cycles counted: {len(crossing_times)}"
    )
    fig.add_annotation(
        x=0.02, y=0.02, xref="paper", yref="paper",
        text=info_text, showarrow=False,
        font=dict(color=marker_color, size=11, family="monospace"),
        xanchor="left", yanchor="bottom", align="left",
        bgcolor="rgba(255,255,255,0.85)", bordercolor=marker_color,
        borderwidth=1, borderpad=4,
    )

    subtitle = f"Measurement: frequency | Actual: {_format_eng(actual, 'Hz')}"
    return _finalize_plot(fig, req.get_name(), subtitle, time_scaled, path)


# ---------------------------------------------------------------------------
# AC / Bode plot functions
# ---------------------------------------------------------------------------


def _finalize_ac_plot(
    fig: "go.Figure",
    title: str,
    subtitle: str,
    path: Path,
) -> Path:
    """Apply layout and save an AC plot as HTML."""
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b><br><span style='font-size:12px;color:gray'>"
                 f"{subtitle}</span>",
            x=0.5,
        ),
        width=900,
        height=600,
        template="plotly_white",
        showlegend=True,
        legend=dict(font=dict(size=10), x=0.01, y=0.99, xanchor="left", yanchor="top"),
    )
    fig.write_html(str(path))
    return path


def _plot_ac_gain_db(
    result: RequirementResult,
    ac_data: ACResult,
    path: Path,
) -> Path:
    """Bode plot for GainDB measurement: gain + phase subplots."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()
    net = _result_net(result)
    ref_net = req.get_ac_ref_net()
    measure_freq = req.get_ac_measure_freq()
    diff_ref = _result_diff_ref(result)

    # Compute differential signal if diff_ref_net is set
    if diff_ref:
        sig_key = ac_data.compute_diff(net, diff_ref)
    else:
        sig_key = net

    if ref_net:
        gain = ac_data.gain_db_relative(sig_key, ref_net)
        phase = ac_data.phase_deg_relative(sig_key, ref_net)
    else:
        gain = ac_data.gain_db(sig_key)
        phase = ac_data.phase_deg(sig_key)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Gain (dB)", "Phase (deg)"),
        vertical_spacing=0.08,
    )

    # Gain trace
    fig.add_trace(
        go.Scatter(
            x=ac_data.freq, y=gain, mode="lines",
            name="Gain", line=dict(color="royalblue", width=2),
        ),
        row=1, col=1,
    )

    # Pass band shading on gain
    fig.add_hrect(
        y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
        line_width=0, row=1, col=1,
    )
    fig.add_hline(y=min_val, line=dict(color="red", dash="dot", width=1.5), row=1, col=1)
    fig.add_hline(y=max_val, line=dict(color="red", dash="dot", width=1.5), row=1, col=1)

    # Marker at measure_freq
    if measure_freq:
        actual = result.actual
        marker_color = "#2ecc71" if result.passed else "#e74c3c"
        fig.add_trace(
            go.Scatter(
                x=[measure_freq], y=[actual], mode="markers+text",
                marker=dict(color=marker_color, size=10),
                text=[f"{actual:.2f} dB @ {measure_freq:.3g} Hz"],
                textposition="top right",
                textfont=dict(color=marker_color, size=11),
                showlegend=False,
            ),
            row=1, col=1,
        )
        fig.add_vline(
            x=measure_freq, line=dict(color="gray", dash="dashdot", width=1),
            opacity=0.5, row=1, col=1,
        )
        fig.add_vline(
            x=measure_freq, line=dict(color="gray", dash="dashdot", width=1),
            opacity=0.5, row=2, col=1,
        )

    # Phase trace
    fig.add_trace(
        go.Scatter(
            x=ac_data.freq, y=phase, mode="lines",
            name="Phase", line=dict(color="orange", width=2),
        ),
        row=2, col=1,
    )

    fig.update_xaxes(type="log", title_text="Frequency (Hz)", row=2, col=1)
    fig.update_xaxes(type="log", row=1, col=1)
    fig.update_yaxes(title_text="Gain (dB)", row=1, col=1)
    fig.update_yaxes(title_text="Phase (deg)", row=2, col=1)

    subtitle = f"Measurement: gain_db | Actual: {result.actual:.2f} dB"
    return _finalize_ac_plot(fig, req.get_name(), subtitle, path)


def _plot_ac_phase_deg(
    result: RequirementResult,
    ac_data: ACResult,
    path: Path,
) -> Path:
    """Bode plot for PhaseDeg measurement: gain + phase subplots."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()
    net = _result_net(result)
    ref_net = req.get_ac_ref_net()
    measure_freq = req.get_ac_measure_freq()
    diff_ref = _result_diff_ref(result)

    # Compute differential signal if diff_ref_net is set
    if diff_ref:
        sig_key = ac_data.compute_diff(net, diff_ref)
    else:
        sig_key = net

    if ref_net:
        gain = ac_data.gain_db_relative(sig_key, ref_net)
        phase = ac_data.phase_deg_relative(sig_key, ref_net)
    else:
        gain = ac_data.gain_db(sig_key)
        phase = ac_data.phase_deg(sig_key)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Gain (dB)", "Phase (deg)"),
        vertical_spacing=0.08,
    )

    # Gain trace
    fig.add_trace(
        go.Scatter(
            x=ac_data.freq, y=gain, mode="lines",
            name="Gain", line=dict(color="royalblue", width=2),
        ),
        row=1, col=1,
    )

    # Phase trace
    fig.add_trace(
        go.Scatter(
            x=ac_data.freq, y=phase, mode="lines",
            name="Phase", line=dict(color="orange", width=2),
        ),
        row=2, col=1,
    )

    # Pass band shading on phase
    fig.add_hrect(
        y0=min_val, y1=max_val, fillcolor="green", opacity=0.08,
        line_width=0, row=2, col=1,
    )
    fig.add_hline(y=min_val, line=dict(color="red", dash="dot", width=1.5), row=2, col=1)
    fig.add_hline(y=max_val, line=dict(color="red", dash="dot", width=1.5), row=2, col=1)

    # Marker at measure_freq
    if measure_freq:
        actual = result.actual
        marker_color = "#2ecc71" if result.passed else "#e74c3c"
        fig.add_trace(
            go.Scatter(
                x=[measure_freq], y=[actual], mode="markers+text",
                marker=dict(color=marker_color, size=10),
                text=[f"{actual:.1f} deg @ {measure_freq:.3g} Hz"],
                textposition="top right",
                textfont=dict(color=marker_color, size=11),
                showlegend=False,
            ),
            row=2, col=1,
        )
        fig.add_vline(
            x=measure_freq, line=dict(color="gray", dash="dashdot", width=1),
            opacity=0.5, row=1, col=1,
        )
        fig.add_vline(
            x=measure_freq, line=dict(color="gray", dash="dashdot", width=1),
            opacity=0.5, row=2, col=1,
        )

    fig.update_xaxes(type="log", title_text="Frequency (Hz)", row=2, col=1)
    fig.update_xaxes(type="log", row=1, col=1)
    fig.update_yaxes(title_text="Gain (dB)", row=1, col=1)
    fig.update_yaxes(title_text="Phase (deg)", row=2, col=1)

    subtitle = f"Measurement: phase_deg | Actual: {result.actual:.1f} deg"
    return _finalize_ac_plot(fig, req.get_name(), subtitle, path)


def _plot_ac_bandwidth_3db(
    result: RequirementResult,
    ac_data: ACResult,
    path: Path,
) -> Path:
    """Gain vs frequency with labeled -3dB crossing point."""
    import plotly.graph_objects as go

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()
    net = _result_net(result)
    ref_net = req.get_ac_ref_net()
    diff_ref = _result_diff_ref(result)

    # Compute differential signal if diff_ref_net is set
    if diff_ref:
        sig_key = ac_data.compute_diff(net, diff_ref)
    else:
        sig_key = net

    if ref_net:
        gain = ac_data.gain_db_relative(sig_key, ref_net)
    else:
        gain = ac_data.gain_db(sig_key)

    dc_gain = gain[0] if gain else 0.0
    max_gain = max(gain) if gain else 0.0
    is_highpass = (max_gain - dc_gain) > 3.0

    if is_highpass:
        ref_gain = max_gain
        threshold = max_gain - 3.0
        ref_label = "Passband Gain"
    else:
        ref_gain = dc_gain
        threshold = dc_gain - 3.0
        ref_label = "DC Gain"

    actual = result.actual

    fig = go.Figure()

    # Gain trace
    fig.add_trace(
        go.Scatter(
            x=ac_data.freq, y=gain, mode="lines",
            name="Gain", line=dict(color="royalblue", width=2.5),
        )
    )

    # Reference gain line
    fig.add_hline(
        y=ref_gain, line=dict(color="gray", dash="dash", width=1.2), opacity=0.5,
    )
    fig.add_annotation(
        x=0.02, y=ref_gain, xref="paper", yref="y",
        text=f"{ref_label} = {ref_gain:.2f} dB",
        showarrow=False, font=dict(color="gray", size=10),
        xanchor="left", yanchor="bottom",
    )

    # -3dB threshold line
    fig.add_hline(
        y=threshold, line=dict(color="#e74c3c", dash="dot", width=1.5), opacity=0.6,
    )

    # -3dB crossing point — the main feature
    if not math.isnan(actual) and actual > 0:
        bw_gain = _interpolate_at_freq(ac_data.freq, gain, actual)
        marker_color = "#2ecc71" if result.passed else "#e74c3c"

        # Large labeled data point at the crossing
        fig.add_trace(
            go.Scatter(
                x=[actual], y=[bw_gain], mode="markers",
                marker=dict(
                    color=marker_color, size=14, symbol="circle",
                    line=dict(color="white", width=2),
                ),
                name=f"-3 dB @ {actual:.3g} Hz",
                showlegend=True,
            )
        )

        # Annotation with both -3dB and frequency
        fig.add_annotation(
            x=actual, y=bw_gain,
            text=(
                f"<b>-3 dB point</b><br>"
                f"f = {actual:.3g} Hz<br>"
                f"Gain = {bw_gain:.2f} dB"
            ),
            showarrow=True, arrowhead=2, arrowsize=1.2,
            arrowcolor=marker_color, arrowwidth=2,
            ax=60, ay=-50,
            font=dict(color=marker_color, size=11),
            align="left",
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=marker_color, borderwidth=1, borderpad=4,
        )

        # Vertical drop-line from crossing point to x-axis
        fig.add_shape(
            type="line",
            x0=actual, x1=actual, y0=bw_gain, y1=threshold,
            line=dict(color=marker_color, dash="dashdot", width=1.5),
            opacity=0.5,
        )

    # BW limits (vertical lines for pass/fail bounds)
    if min_val > 0:
        fig.add_vline(
            x=min_val, line=dict(color="red", dash="dot", width=1.5),
        )
        fig.add_annotation(
            x=min_val, y=0.02, xref="x", yref="paper",
            text=f"LSL = {min_val:.3g} Hz",
            showarrow=False, font=dict(color="red", size=9),
            xanchor="left", yanchor="bottom", textangle=-90,
        )
    if max_val > 0:
        fig.add_vline(
            x=max_val, line=dict(color="red", dash="dot", width=1.5),
        )
        fig.add_annotation(
            x=max_val, y=0.02, xref="x", yref="paper",
            text=f"USL = {max_val:.3g} Hz",
            showarrow=False, font=dict(color="red", size=9),
            xanchor="left", yanchor="bottom", textangle=-90,
        )

    fig.update_xaxes(type="log", title_text="Frequency (Hz)")
    fig.update_yaxes(title_text="Gain (dB)")

    subtitle = f"Measurement: bandwidth_3db | -3dB BW = {actual:.3g} Hz"
    return _finalize_ac_plot(fig, req.get_name(), subtitle, path)


def _plot_ac_bode_plot(
    result: RequirementResult,
    ac_data: ACResult,
    path: Path,
) -> Path:
    """Classic Bode plot: gain (dB) vs frequency on top, phase (deg) vs frequency
    on bottom. Both use log-scale frequency axis. Shows the full sweep as a line."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    req = result.requirement
    net = _result_net(result)
    ref_net = req.get_ac_ref_net()
    diff_ref = _result_diff_ref(result)

    # Compute differential signal if diff_ref_net is set
    if diff_ref:
        sig_key = ac_data.compute_diff(net, diff_ref)
    else:
        sig_key = net

    if ref_net:
        gain = ac_data.gain_db_relative(sig_key, ref_net)
        phase = ac_data.phase_deg_relative(sig_key, ref_net)
    else:
        gain = ac_data.gain_db(sig_key)
        phase = ac_data.phase_deg(sig_key)

    dc_gain = gain[0] if gain else 0.0

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.08,
    )

    # Gain vs frequency
    fig.add_trace(
        go.Scatter(
            x=ac_data.freq, y=gain, mode="lines",
            name="Gain (dB)", line=dict(color="royalblue", width=2),
        ),
        row=1, col=1,
    )

    # Phase vs frequency
    fig.add_trace(
        go.Scatter(
            x=ac_data.freq, y=phase, mode="lines",
            name="Phase (deg)", line=dict(color="orange", width=2),
        ),
        row=2, col=1,
    )

    # -3dB crossing point
    threshold = dc_gain - 3.0
    bw_freq = None
    for i in range(len(gain) - 1):
        if gain[i] >= threshold and gain[i + 1] < threshold:
            log_f0 = math.log10(ac_data.freq[i])
            log_f1 = math.log10(ac_data.freq[i + 1])
            if gain[i] != gain[i + 1]:
                t = (threshold - gain[i]) / (gain[i + 1] - gain[i])
                bw_freq = 10 ** (log_f0 + t * (log_f1 - log_f0))
            else:
                bw_freq = ac_data.freq[i]
            break

    if bw_freq is not None:
        bw_gain_val = _interpolate_at_freq(ac_data.freq, gain, bw_freq)
        fig.add_trace(
            go.Scatter(
                x=[bw_freq], y=[bw_gain_val], mode="markers",
                marker=dict(color="#e74c3c", size=10, symbol="circle",
                            line=dict(color="white", width=2)),
                name=f"-3 dB @ {bw_freq:.3g} Hz",
                showlegend=True,
            ),
            row=1, col=1,
        )
        fig.add_annotation(
            x=bw_freq, y=bw_gain_val, xref="x", yref="y",
            text=f"-3 dB | {bw_freq:.3g} Hz",
            showarrow=True, arrowhead=2, arrowcolor="#e74c3c",
            ax=50, ay=-30,
            font=dict(color="#e74c3c", size=11),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#e74c3c", borderwidth=1, borderpad=3,
        )

    fig.update_xaxes(type="log", row=1, col=1)
    fig.update_xaxes(type="log", title_text="Frequency (Hz)", row=2, col=1)
    fig.update_yaxes(title_text="Gain (dB)", row=1, col=1)
    fig.update_yaxes(title_text="Phase (deg)", row=2, col=1)

    subtitle = f"DC Gain: {dc_gain:.2f} dB"
    if bw_freq is not None:
        subtitle += f" | -3 dB BW: {bw_freq:.3g} Hz"
    return _finalize_ac_plot(fig, req.get_name(), subtitle, path)


def _plot_sweep(
    result: RequirementResult,
    tran_data: TransientResult,
    path: Path,
) -> Path:
    """Plot for Sweep measurement: X = swept variable, Y = measured variable."""
    import plotly.graph_objects as go

    req = result.requirement
    min_val = req.get_min_val()
    max_val = req.get_max_val()
    net = _result_net(result)
    context_nets = _result_ctx_nets(result)

    net_key = f"v({net})" if not net.startswith(("v(", "i(")) else net
    nut_unit = _signal_unit(net_key)
    nut_signal = tran_data[net_key]

    # X-axis: first context net (the swept variable)
    if not context_nets:
        return _plot_final_value(result, tran_data, path)

    sweep_net = context_nets[0]
    sweep_key = (
        f"v({sweep_net})" if not sweep_net.startswith(("v(", "i(")) else sweep_net
    )
    sweep_signal = tran_data[sweep_key]
    sweep_unit = _signal_unit(sweep_key)

    fig = go.Figure()

    # Main sweep trace
    fig.add_trace(go.Scatter(
        x=list(sweep_signal), y=list(nut_signal),
        mode="lines",
        name=f"{net_key} vs {sweep_key}",
        line=dict(color="royalblue", width=2.5),
    ))

    # Pass band shading
    fig.add_hrect(
        y0=min_val, y1=max_val, fillcolor="green", opacity=0.08, line_width=0,
    )

    # Limit lines
    _add_limit_labels(fig, min_val, max_val, nut_unit)

    # Start marker
    fig.add_trace(go.Scatter(
        x=[sweep_signal[0]], y=[nut_signal[0]],
        mode="markers+text",
        marker=dict(color="gray", size=8, symbol="circle"),
        text=["Start"],
        textposition="top right",
        showlegend=False,
    ))

    # End marker with actual value
    actual = result.actual
    marker_color = "#2ecc71" if result.passed else "#e74c3c"
    fig.add_trace(go.Scatter(
        x=[sweep_signal[-1]], y=[nut_signal[-1]],
        mode="markers+text",
        marker=dict(color=marker_color, size=10, symbol="circle"),
        text=[f"End = {_format_eng(actual, nut_unit)}"],
        textposition="top left",
        textfont=dict(color=marker_color, size=11),
        showlegend=False,
    ))

    # Axis labels
    sweep_label = (
        f"Voltage ({sweep_unit})" if sweep_unit == "V"
        else f"Current ({sweep_unit})"
    )
    nut_label = (
        f"Voltage ({nut_unit})" if nut_unit == "V"
        else f"Current ({nut_unit})"
    )
    fig.update_xaxes(title_text=f"{sweep_key} — {sweep_label}")
    fig.update_yaxes(title_text=f"{net_key} — {nut_label}")

    subtitle = f"Measurement: sweep | Final: {_format_eng(actual, nut_unit)}"
    return _finalize_ac_plot(fig, req.get_name(), subtitle, path)


# ---------------------------------------------------------------------------
# Dispatch table and public API
# ---------------------------------------------------------------------------

_PLOT_DISPATCH: dict[str, callable] = {
    "final_value": _plot_final_value,
    "average": _plot_average_value,
    "settling_time": _plot_settling_time,
    "peak_to_peak": _plot_peak_to_peak,
    "overshoot": _plot_overshoot,
    "rms": _plot_rms,
    "frequency": _plot_frequency,
    "sweep": _plot_sweep,
}

_AC_PLOT_DISPATCH: dict[str, callable] = {
    "gain_db": _plot_ac_gain_db,
    "phase_deg": _plot_ac_phase_deg,
    "bandwidth_3db": _plot_ac_bandwidth_3db,
    "bode_plot": _plot_ac_bode_plot,
}


def plot_requirement(
    result: RequirementResult,
    tran_data: TransientResult | None,
    path: str | Path,
    ac_data: ACResult | None = None,
) -> Path | None:
    """Generate a per-requirement plot.

    Dispatches to a measurement-specific plot function based on the
    requirement's measurement type. Each measurement gets a tailored
    visualization.

    For AC requirements, pass ac_data instead of tran_data.
    """
    try:
        import plotly  # noqa: F401
    except ImportError:
        logger.info("plotly not installed — skipping plot")
        return None

    path = Path(path)
    req = result.requirement
    measurement = req.get_measurement()

    # AC plots
    ac_plot_fn = _AC_PLOT_DISPATCH.get(measurement)
    if ac_plot_fn is not None:
        if ac_data is None:
            return None
        net = _result_net(result)
        # For differential signals, check the positive net exists
        if net not in ac_data and f"v({net})" not in ac_data:
            # May be a differential pair — check if diff_ref_net is set
            # and both component nets exist
            diff_ref = _result_diff_ref(result)
            if not diff_ref:
                return None
        return ac_plot_fn(result, ac_data, path)

    # Transient plots
    if tran_data is None:
        return None

    net = _result_net(result)
    net_key = f"v({net})" if not net.startswith(("v(", "i(")) else net
    if net_key not in tran_data:
        return None

    plot_fn = _PLOT_DISPATCH.get(measurement)
    if plot_fn is None:
        logger.warning(f"No plot function for measurement '{measurement}'")
        return None

    return plot_fn(result, tran_data, path)


# ---------------------------------------------------------------------------
# Scoped verification (entry point for build step)
# ---------------------------------------------------------------------------


@dataclass
class _ResolvedNets:
    """Resolved net names for a single requirement."""

    net: str  # canonical SPICE net name
    display_net: str  # original ato address for plot labels
    diff_ref_net: str | None
    context_nets: list[str]


def _build_net_overrides(
    requirements: list[F.Requirement],
    net_aliases: dict[str, str],
) -> dict[int, _ResolvedNets]:
    """Build a mapping from requirement id → resolved net names.

    Instead of mutating graph parameters (which is fragile), this builds a
    pure-data lookup that callers thread through to ``verify_requirements``.
    """
    overrides: dict[int, _ResolvedNets] = {}

    for req in requirements:
        raw_addr = req.net.get().try_extract_singleton() or ""
        raw_net = req.get_net()  # sanitized
        resolved_net = net_aliases.get(raw_net, raw_net)
        if resolved_net != raw_net:
            logger.debug(f"Resolving net alias: {raw_net} -> {resolved_net}")

        # diff_ref_net
        raw_diff = req.get_diff_ref_net()
        resolved_diff = None
        if raw_diff:
            resolved_diff = net_aliases.get(raw_diff, raw_diff)

        # context nets
        resolved_ctx: list[str] = []
        for ctx_net in req.get_context_nets():
            resolved_ctx.append(net_aliases.get(ctx_net, ctx_net))

        overrides[id(req)] = _ResolvedNets(
            net=resolved_net,
            display_net=raw_addr,
            diff_ref_net=resolved_diff,
            context_nets=resolved_ctx,
        )

    return overrides


def verify_requirements_scoped(
    app,
    solver,
    output_dir: Path,
) -> tuple[list[RequirementResult], dict[tuple, TransientResult], dict[tuple, ACResult]]:
    """Find all requirements, group by parent scope, run scoped simulations.

    For each scope:
      1. Generate a scoped SPICE netlist (only components in that subtree)
      2. Run simulations (DCOP + transient + AC)
      3. Generate per-requirement plots

    Args:
        app: Application root node.
        solver: Parameter solver.
        output_dir: Directory for .spice files and plot outputs.

    Returns:
        (all_results, all_tran_data, all_ac_data) aggregated across all scopes.
    """
    from collections import defaultdict

    import faebryk.core.node as fabll
    from faebryk.exporters.simulation.ngspice import generate_spice_netlist

    reqs = app.get_children(direct_only=False, types=F.Requirement)
    if not reqs:
        return [], {}, {}

    def _find_simulation_scope(node: fabll.Node) -> fabll.Node:
        """Walk up from a node to find the nearest ancestor with Electrical children."""
        current = node
        while current is not None:
            if current.get_children(direct_only=False, types=F.Electrical):
                return current
            parent_info = current.get_parent()
            current = parent_info[0] if parent_info is not None else None
        return app

    # Group requirements by simulation scope
    # get_parent() returns (parent_node, child_name) tuple
    scope_groups: dict[fabll.Node, list[F.Requirement]] = defaultdict(list)
    for req in reqs:
        parent_info = req.get_parent()
        parent = parent_info[0] if parent_info is not None else app
        scope = _find_simulation_scope(parent)
        scope_groups[scope].append(req)

    all_results: list[RequirementResult] = []
    all_tran_data: dict[tuple, TransientResult] = {}
    all_ac_data: dict[tuple, ACResult] = {}

    for scope, group_reqs in scope_groups.items():
        scope_name = scope.get_full_name(include_uuid=False) or "circuit"
        scope_slug = scope_name.replace(".", "_").replace(" ", "_")
        logger.info(
            f"Generating scoped SPICE netlist for {scope_name} "
            f"({len(group_reqs)} requirements)"
        )

        try:
            netlist, net_aliases = generate_spice_netlist(app, solver, scope=scope)
            spice_path = output_dir / f"{scope_slug}.spice"
            netlist.write(spice_path)

            # Build net overrides (ato addresses → canonical SPICE names)
            net_overrides = _build_net_overrides(list(group_reqs), net_aliases)

            circuit = Circuit.load(spice_path)
            results, tran_data, ac_data = verify_requirements(
                circuit, list(group_reqs), uic=True,
                net_overrides=net_overrides,
            )

            # Stamp resolved net info onto results for plot functions
            for r in results:
                ov = net_overrides.get(id(r.requirement))
                if ov:
                    r.display_net = ov.display_net
                    r.resolved_net = ov.net
                    r.resolved_diff_ref = ov.diff_ref_net
                    r.resolved_ctx_nets = ov.context_nets

            all_results.extend(results)
            all_tran_data.update(tran_data)
            all_ac_data.update(ac_data)

            # Generate per-requirement plots
            for r in results:
                capture = r.requirement.get_capture()
                if capture not in ("transient", "ac"):
                    continue
                name_slug = (
                    r.requirement.get_name()
                    .replace(" ", "_")
                    .replace(":", "")
                )
                plot_path = output_dir / f"req_{name_slug}.html"
                if capture == "transient":
                    key = _tran_group_key(r.requirement)
                    plot_requirement(r, tran_data.get(key), plot_path)
                elif capture == "ac":
                    key = _ac_group_key(r.requirement)
                    plot_requirement(
                        r, None, plot_path, ac_data=ac_data.get(key)
                    )
        except Exception as e:
            logger.warning(
                f"Simulation for scope '{scope_name}' failed — skipping: {e}",
                exc_info=True,
            )

    return all_results, all_tran_data, all_ac_data
