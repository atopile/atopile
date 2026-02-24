"""Phase 1: Run simulations and cache results.

Discovers all nodes with ``is_spice_simulation`` trait, groups them by
simulation scope (nearest ancestor with Electrical children), generates
scoped SPICE netlists, and runs each simulation — caching ALL signal
data on the trait instance for downstream requirement verification.

Simulations within a scope and sweep points within a sweep are executed
in parallel using a thread pool.  Each thread gets its own ``Circuit``
copy so there is no shared mutable state; the actual work is
subprocess-bound (ngspice runs as a child process) so the GIL is not a
bottleneck.
"""

from __future__ import annotations

import logging
import os
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.exporters.simulation.ngspice import Circuit, generate_spice_netlist

logger = logging.getLogger(__name__)

# Number of parallel ngspice processes.  Defaults to CPU count; override
# with the ``ATO_SIM_WORKERS`` environment variable.
_MAX_WORKERS = int(os.environ.get("ATO_SIM_WORKERS", 0)) or os.cpu_count() or 4
TMAX = 25e-9


@dataclass
class SimStats:
    """Per-simulation profiling data for the performance report."""

    name: str
    sim_type: str  # "transient", "sweep", "ac", "dcop"
    elapsed_s: float
    data_points: int  # total number of numeric values in the result


def _count_data_points(result: object) -> int:
    """Count total numeric data points in a simulation result."""
    from faebryk.exporters.simulation.ngspice import ACResult, TransientResult

    if isinstance(result, TransientResult):
        # time vector + all signal vectors
        n = len(result.time)
        return n + sum(len(v) for v in result.signals.values())
    elif isinstance(result, ACResult):
        n = len(result.freq)
        return n + sum(len(v) for v in result.signals_real.values()) + sum(
            len(v) for v in result.signals_imag.values()
        )
    elif isinstance(result, dict):
        # Sweep: dict[float, TransientResult]
        return sum(_count_data_points(v) for v in result.values())
    else:
        return 0


def _apply_spice_source(circuit: Circuit, spice_line: str) -> None:
    """Add voltage/current source element(s) to the circuit.

    Supports pipe-separated multi-source strings (e.g.
    ``"V1 n1 0 DC 12|Iload n2 0 PULSE(...)"``) where each segment
    is a separate SPICE element line.
    """
    for part in spice_line.split("|"):
        part = part.strip()
        if part:
            circuit.add_element(part)


def _resolve_net_aliases(text: str, net_aliases: dict[str, str]) -> str:
    """Replace alias net names in SPICE text with their canonical names.

    This allows users to write readable hierarchy names (e.g.
    ``dut_power_in_hv``) in their .ato simulation definitions, even though
    the SPICE netlist uses the shorter canonical name (e.g. ``dut_package_2``).
    """
    if not net_aliases or not text:
        return text
    for alias in sorted(net_aliases, key=len, reverse=True):
        if alias in text:
            text = re.sub(
                r"\b" + re.escape(alias) + r"\b", net_aliases[alias], text
            )
    return text


def _find_simulation_scope(node: fabll.Node, app: fabll.Node) -> fabll.Node:
    """Walk up from a node to find the nearest ancestor with Electrical children."""
    current = node
    while current is not None:
        if current.get_children(direct_only=False, types=F.Electrical):
            return current
        parent_info = current.get_parent()
        current = parent_info[0] if parent_info is not None else None
    return app


# ---------------------------------------------------------------------------
# Parallel-safe simulation runners
#
# Each function receives a *copy* of the base circuit so it can freely
# mutate netlist lines without affecting other threads.
# ---------------------------------------------------------------------------


def _run_transient_parallel(
    base_circuit: Circuit,
    sim_node,
    net_aliases: dict[str, str],
) -> tuple[float, object]:
    """Run a single transient simulation on an independent circuit copy.

    Returns ``(elapsed_seconds, result)``.
    """
    t0 = time.monotonic()
    circuit = base_circuit.copy()

    spice = sim_node.get_spice()
    if spice:
        _apply_spice_source(circuit, _resolve_net_aliases(spice, net_aliases))

    for name in sim_node.get_remove_elements():
        circuit.remove_element(name)
    for line in sim_node.get_extra_spice():
        circuit.add_element(_resolve_net_aliases(line, net_aliases))

    step = sim_node.get_time_step()
    stop = sim_node.get_time_stop()
    start = sim_node.get_time_start() or 0
    if step is None or stop is None:
        raise ValueError(
            f"Transient simulation missing time_step or time_stop "
            f"(step={step}, stop={stop})"
        )

    result = circuit.tran(step=step, stop=stop, start=start, signals=None, uic=True, tmax=TMAX)
    return (time.monotonic() - t0, result)


def _run_ac_parallel(
    base_circuit: Circuit,
    sim_node,
    net_aliases: dict[str, str],
) -> tuple[float, object]:
    """Run a single AC analysis on an independent circuit copy.

    Returns ``(elapsed_seconds, result)``.
    """
    t0 = time.monotonic()
    circuit = base_circuit.copy()

    for name in sim_node.get_remove_elements():
        circuit.remove_element(name)
    for line in sim_node.get_extra_spice():
        circuit.add_element(_resolve_net_aliases(line, net_aliases))

    spice = sim_node.get_spice()
    if spice:
        resolved = _resolve_net_aliases(spice, net_aliases)
        # Add all source elements
        source_name = None
        for part in resolved.split("|"):
            part = part.strip()
            if part:
                circuit.add_element(part)
                if source_name is None:
                    source_name = part.split(None, 1)[0]
        # Append AC stimulus to the first source
        if source_name:
            existing_spec = circuit.get_source_spec(source_name)
            if existing_spec and "AC" not in existing_spec.upper():
                circuit.set_source(source_name, f"{existing_spec} AC 1")

    start = sim_node.get_start_freq()
    stop = sim_node.get_stop_freq()
    ppd = sim_node.get_points_per_dec() or 100
    if start is None or stop is None:
        raise ValueError("AC simulation missing start_freq or stop_freq")

    result = circuit.ac(
        start_freq=start, stop_freq=stop, points_per_decade=ppd, signals=None
    )
    return (time.monotonic() - t0, result)


def _run_dcop_parallel(
    base_circuit: Circuit,
    sim_node,
    net_aliases: dict[str, str],
) -> tuple[float, object]:
    """Run a DC operating point analysis on an independent circuit copy.

    Returns ``(elapsed_seconds, result)``.
    """
    t0 = time.monotonic()
    circuit = base_circuit.copy()

    spice = sim_node.get_spice()
    if spice:
        _apply_spice_source(circuit, _resolve_net_aliases(spice, net_aliases))

    for name in sim_node.get_remove_elements():
        circuit.remove_element(name)
    for line in sim_node.get_extra_spice():
        circuit.add_element(_resolve_net_aliases(line, net_aliases))

    result = circuit.op()
    return (time.monotonic() - t0, result)


def _run_single_sweep_point(
    base_circuit: Circuit,
    sim_node,
    pval: float,
    step: float,
    stop: float,
    start: float,
    net_aliases: dict[str, str] | None = None,
) -> tuple[float, object | None]:
    """Run one sweep point on an independent circuit copy.

    Returns ``(param_value, result)`` or ``(param_value, None)`` on failure.
    """
    aliases = net_aliases or {}
    circuit = base_circuit.copy()
    try:
        spice_line = sim_node.resolve_spice(pval)
        if spice_line:
            _apply_spice_source(circuit, _resolve_net_aliases(spice_line, aliases))

        for name in sim_node.get_remove_elements():
            circuit.remove_element(name)
        for line in sim_node.resolve_extra_spice(pval):
            circuit.add_element(_resolve_net_aliases(line, aliases))

        result = circuit.tran(step=step, stop=stop, start=start, signals=None, uic=True, tmax=TMAX)
        return (pval, result)
    except Exception:
        logger.warning(f"Sweep point {pval} failed — skipping", exc_info=True)
        return (pval, None)


def _run_sweep_sequential(
    base_circuit: Circuit,
    sim_node,
    net_aliases: dict[str, str],
) -> tuple[float, dict[float, object]]:
    """Run a parametric sweep with points executed sequentially.

    Sweep points run sequentially within a single worker thread to avoid
    thread-pool starvation (submitting sub-tasks to a shared executor that
    is already saturated with top-level simulations).  The outer executor
    already provides parallelism across simulations.

    Returns ``(elapsed_seconds, {param_value: result})``.
    """
    t0 = time.monotonic()
    param_values = sim_node.get_param_values()
    if not param_values:
        return (time.monotonic() - t0, {})

    step = sim_node.get_time_step()
    stop = sim_node.get_time_stop()
    start = sim_node.get_time_start() or 0
    if step is None or stop is None:
        raise ValueError("Sweep simulation missing time_step or time_stop")

    sweep_results: dict[float, object] = {}
    for pval in param_values:
        _pval, result = _run_single_sweep_point(
            base_circuit, sim_node, pval, step, stop, start,
            net_aliases=net_aliases,
        )
        if result is not None:
            sweep_results[pval] = result

    return (time.monotonic() - t0, sweep_results)


# ---------------------------------------------------------------------------
# Multi-DUT support
# ---------------------------------------------------------------------------


@dataclass
class MultiDutResult:
    """Result container for multi-DUT simulations.

    Each DUT gets its own simulation result and net aliases (since each
    DUT has its own scoped netlist).
    """

    results: dict[str, tuple[object, dict[str, str]]]
    # {dut_name: (sim_result, net_aliases)}
    dut_params: dict[str, dict[str, float]]
    # {dut_name: {"power_in.voltage": 12.0, "power_out.voltage": 5.0, ...}}
    sweep_param_name: str = ""
    sweep_param_unit: str = ""


def _find_child_by_name(parent: fabll.Node, name: str) -> fabll.Node | None:
    """Find a direct child node by its attribute name."""
    for child in parent.get_children(direct_only=True, types=fabll.Node):
        info = child.get_parent()
        if info and info[1] == name:
            return child
    return None


def _resolve_dut_params(dut_node: fabll.Node) -> dict[str, float]:
    """Extract parameter values from a DUT node.

    Extracts:
    1. Voltages and max_current from ElectricPower interfaces
       (e.g. ``power_in.voltage``, ``power_out.max_current``).
    2. Direct NumericParameter children (e.g. ``switching_frequency``).

    Returns a mapping like ``{"power_in.voltage": 12.0, "switching_frequency": 400000.0}``.
    """
    from faebryk.exporters.simulation.ngspice import _get_nominal_value

    params: dict[str, float] = {}

    # --- ElectricPower parameters (voltage, max_current) ---
    power_interfaces = dut_node.get_children(
        direct_only=False, types=F.ElectricPower
    )
    for power in power_interfaces:
        # Build relative path from DUT to this interface
        parts: list[str] = []
        current = power
        while current is not None and current != dut_node:
            info = current.get_parent()
            if info is None:
                break
            parts.append(info[1])
            current = info[0]
        if current != dut_node:
            continue
        parts.reverse()
        rel_path = ".".join(parts)

        try:
            voltage = _get_nominal_value(power.voltage.get())
            if voltage is not None:
                params[f"{rel_path}.voltage"] = voltage
        except Exception:
            pass

        try:
            max_current = _get_nominal_value(power.max_current.get())
            if max_current is not None:
                params[f"{rel_path}.max_current"] = max_current
        except Exception:
            pass

    # --- Direct NumericParameter children (e.g. switching_frequency) ---
    for child in dut_node.get_children(
        direct_only=True, types=F.Parameters.NumericParameter
    ):
        info = child.get_parent()
        if info is None:
            continue
        name = info[1]
        try:
            value = _get_nominal_value(child)
            if value is not None:
                params[name] = value
        except Exception:
            pass

    return params


def _resolve_sweep_param_binding(
    dut_node: fabll.Node, ato_param_name: str
) -> str | None:
    """Find the SPICE parameter name that binds to an ato parameter.

    Scans ``has_spice_model`` traits on the DUT and its descendants for
    ``param_bindings`` entries whose ato-side name matches *ato_param_name*.

    Returns the SPICE param name (e.g. ``"FS"``) or ``None``.
    """
    for node in dut_node.get_children(
        direct_only=False,
        types=fabll.Node,
        include_root=True,
        required_trait=F.has_spice_model,
    ):
        trait = node.get_trait(F.has_spice_model)
        bindings = trait.get_param_bindings()
        for spice_param, ato_name in bindings.items():
            if ato_name == ato_param_name:
                return spice_param
    return None


def _resolve_dut_references(
    text: str,
    dut_name: str,
    dut_params: dict[str, float],
) -> str:
    """Resolve ``dut.path.to.thing`` references in SPICE text.

    Two types of references:
    1. **Parameter** — e.g. ``dut.power_in.voltage`` → ``12.0``
       Matched against pre-computed ``dut_params`` dict.
    2. **Net** — e.g. ``dut.power_in.hv`` → ``dut12_power_in_hv``
       Converted to underscore format for subsequent net-alias resolution.

    The ``dut.`` prefix is always replaced with ``{dut_name}.`` first,
    then parameters are substituted. Unresolved references are sanitized
    to underscore format (net names).
    """

    def _replace_braced(match: re.Match) -> str:
        """Replace {dut.X.Y} — always a parameter reference."""
        ref = match.group(1)  # e.g., "dut.power_in.voltage"
        rel_path = ref[4:]  # everything after "dut."
        if rel_path in dut_params:
            return str(dut_params[rel_path])
        # Unknown param — leave as underscore net name (shouldn't happen)
        return f"{dut_name}_{rel_path.replace('.', '_')}"

    def _replace_bare(match: re.Match) -> str:
        """Replace bare dut.X.Y — param or net reference."""
        ref = match.group(0)
        rel_path = ref[4:]
        if rel_path in dut_params:
            return str(dut_params[rel_path])
        return f"{dut_name}_{rel_path.replace('.', '_')}"

    # First pass: resolve {dut.X.Y} patterns (remove braces)
    text = re.sub(r"\{(dut(?:\.\w+)+)\}", _replace_braced, text)
    # Second pass: resolve bare dut.X.Y patterns
    return re.sub(r"\bdut(?:\.\w+)+", _replace_bare, text)


def _run_single_dut_transient_task(
    base_circuit: Circuit,
    sim_node,
    dut_name: str,
    dut_params: dict[str, float],
    net_aliases: dict[str, str],
) -> object:
    """Run a single DUT transient simulation (thread-safe).

    Copies the base circuit so each thread works on independent state.
    The actual work is subprocess-bound (ngspice) so the GIL is not
    a bottleneck.
    """
    circuit = base_circuit.copy()

    spice = sim_node.get_spice()
    if spice:
        resolved = _resolve_dut_references(spice, dut_name, dut_params)
        _apply_spice_source(circuit, _resolve_net_aliases(resolved, net_aliases))

    for name in sim_node.get_remove_elements():
        circuit.remove_element(name)

    for line in sim_node.get_extra_spice():
        resolved = _resolve_dut_references(line, dut_name, dut_params)
        circuit.add_element(_resolve_net_aliases(resolved, net_aliases))

    step = sim_node.get_time_step()
    stop = sim_node.get_time_stop()
    start = sim_node.get_time_start() or 0
    if step is None or stop is None:
        raise ValueError(
            f"Multi-DUT transient missing time_step or time_stop "
            f"(step={step}, stop={stop})"
        )

    return circuit.tran(
        step=step, stop=stop, start=start,
        signals=None, uic=True, tmax=TMAX,
    )


def _run_single_dut_sweep_point_task(
    base_circuit: Circuit,
    sim_node,
    dut_name: str,
    dut_params: dict[str, float],
    net_aliases: dict[str, str],
    pval: float,
    step: float,
    stop: float,
    start: float,
    spice_param_override: str | None = None,
) -> tuple[float, object | None]:
    """Run one sweep point for one DUT (thread-safe).

    Returns ``(param_value, result)`` or ``(param_value, None)`` on failure.

    When *spice_param_override* is set (e.g. ``"FS"``), the circuit's
    subcircuit instance parameter is updated to *pval* before running.
    This supports sweeping DUT-level parameters like switching_frequency
    that are resolved via ``param_bindings`` at netlist generation time.
    """
    circuit = base_circuit.copy()
    try:
        # Apply subcircuit param override for DUT parameter sweeps
        if spice_param_override:
            circuit.modify_instance_param(spice_param_override, pval)

        spice_line = sim_node.resolve_spice(pval)
        if spice_line:
            resolved = _resolve_dut_references(spice_line, dut_name, dut_params)
            _apply_spice_source(
                circuit, _resolve_net_aliases(resolved, net_aliases)
            )

        for name in sim_node.get_remove_elements():
            circuit.remove_element(name)
        for line in sim_node.resolve_extra_spice(pval):
            resolved = _resolve_dut_references(line, dut_name, dut_params)
            circuit.add_element(_resolve_net_aliases(resolved, net_aliases))

        result = circuit.tran(
            step=step, stop=stop, start=start,
            signals=None, uic=True, tmax=TMAX,
        )
        return (pval, result)
    except Exception:
        logger.warning(
            f"Sweep point {pval} for DUT '{dut_name}' failed — skipping",
            exc_info=True,
        )
        return (pval, None)


def _run_multi_dut_transient(
    app: fabll.Node,
    solver,
    sim_node,
    output_dir: Path,
    executor: ThreadPoolExecutor,
) -> tuple[float, MultiDutResult]:
    """Run a transient simulation for each DUT in parallel.

    Phase 1 (sequential): Generate scoped netlists for each DUT.
    Netlist generation uses the solver which may not be thread-safe.

    Phase 2 (parallel): Submit all DUT simulations to the thread pool.
    Each thread copies its circuit and runs an independent ngspice subprocess.
    """
    t0 = time.monotonic()
    dut_names = sim_node.get_duts()
    parent_info = sim_node.get_parent()
    parent = parent_info[0] if parent_info is not None else app

    all_dut_params: dict[str, dict[str, float]] = {}

    # Phase 1: Generate netlists sequentially (solver may not be thread-safe)
    dut_circuits: dict[str, tuple[Circuit, dict[str, str]]] = {}
    for dut_name in dut_names:
        dut_node = _find_child_by_name(parent, dut_name)
        if dut_node is None:
            logger.warning(f"Multi-DUT: child '{dut_name}' not found in parent")
            continue

        try:
            netlist, net_aliases = generate_spice_netlist(
                app, solver, scope=dut_node
            )
            spice_path = output_dir / f"multidut_{dut_name}.spice"
            netlist.write(spice_path)

            alias_path = output_dir / f"multidut_{dut_name}.aliases.txt"
            with open(alias_path, "w") as af:
                af.write(f"dut_name: {dut_name}\n")
                af.write(f"netlist_lines: {len(netlist._lines)}\n\n")
                af.write("=== Net Aliases ===\n")
                for alias, canon in sorted(net_aliases.items()):
                    af.write(f"  {alias} -> {canon}\n")

            circuit = Circuit.load(spice_path)
            dut_params = _resolve_dut_params(dut_node)
            all_dut_params[dut_name] = dut_params
            logger.info(f"  Multi-DUT '{dut_name}' params: {dut_params}")
            dut_circuits[dut_name] = (circuit, net_aliases)
        except Exception:
            logger.warning(
                f"  Multi-DUT '{dut_name}' netlist generation failed — skipping",
                exc_info=True,
            )

    # Phase 2: Submit all DUT simulations to thread pool
    results: dict[str, tuple[object, dict[str, str]]] = {}
    future_map: dict = {}
    for dut_name, (circuit, net_aliases) in dut_circuits.items():
        fut = executor.submit(
            _run_single_dut_transient_task,
            circuit, sim_node, dut_name,
            all_dut_params[dut_name], net_aliases,
        )
        future_map[fut] = (dut_name, net_aliases)

    # Phase 3: Collect results as they complete
    for fut in as_completed(future_map):
        dut_name, net_aliases = future_map[fut]
        try:
            result = fut.result()
            results[dut_name] = (result, net_aliases)
            logger.info(f"  Multi-DUT '{dut_name}' simulation complete")
        except Exception:
            logger.warning(
                f"  Multi-DUT '{dut_name}' failed — skipping",
                exc_info=True,
            )

    elapsed = time.monotonic() - t0
    return (elapsed, MultiDutResult(results=results, dut_params=all_dut_params))


def _run_multi_dut_sweep(
    app: fabll.Node,
    solver,
    sim_node,
    output_dir: Path,
    executor: ThreadPoolExecutor,
) -> tuple[float, MultiDutResult]:
    """Run a parametric sweep for each DUT with sweep points in parallel.

    Phase 1 (sequential): Generate scoped netlists for each DUT.
    Phase 2 (parallel): Submit all (DUT x sweep-point) combinations to
    the thread pool for maximum parallelism.
    """
    t0 = time.monotonic()
    dut_names = sim_node.get_duts()
    parent_info = sim_node.get_parent()
    parent = parent_info[0] if parent_info is not None else app

    all_dut_params: dict[str, dict[str, float]] = {}

    # Phase 1: Generate netlists sequentially
    dut_circuits: dict[str, tuple[Circuit, dict[str, str]]] = {}
    for dut_name in dut_names:
        dut_node = _find_child_by_name(parent, dut_name)
        if dut_node is None:
            logger.warning(f"Multi-DUT sweep: child '{dut_name}' not found")
            continue

        try:
            netlist, net_aliases = generate_spice_netlist(
                app, solver, scope=dut_node
            )
            spice_path = output_dir / f"multidut_{dut_name}.spice"
            netlist.write(spice_path)
            circuit = Circuit.load(spice_path)
            dut_params = _resolve_dut_params(dut_node)
            all_dut_params[dut_name] = dut_params
            dut_circuits[dut_name] = (circuit, net_aliases)
        except Exception:
            logger.warning(
                f"Multi-DUT sweep '{dut_name}' netlist gen failed — skipping",
                exc_info=True,
            )

    param_values = sim_node.get_param_values()
    step = sim_node.get_time_step()
    stop = sim_node.get_time_stop()
    start = sim_node.get_time_start() or 0
    if step is None or stop is None:
        raise ValueError("Sweep simulation missing time_step or time_stop")

    # Resolve subcircuit param override for DUT parameter sweeps
    # (e.g. param_name="dut.switching_frequency" → SPICE param "FS")
    spice_param_override: str | None = None
    param_name = sim_node.get_param_name() or ""
    if param_name.startswith("dut."):
        ato_param = param_name[4:]  # e.g. "switching_frequency"
        for dut_name_check in dut_names:
            dut_node = _find_child_by_name(parent, dut_name_check)
            if dut_node is not None:
                spice_param_override = _resolve_sweep_param_binding(
                    dut_node, ato_param
                )
                if spice_param_override:
                    logger.info(
                        f"Sweep '{param_name}' → SPICE param "
                        f"'{spice_param_override}' override"
                    )
                    break

    # Phase 2: Submit all (DUT x sweep-point) combinations to thread pool
    # fut -> (dut_name, pval)
    future_map: dict = {}
    for dut_name, (circuit, net_aliases) in dut_circuits.items():
        for pval in param_values:
            fut = executor.submit(
                _run_single_dut_sweep_point_task,
                circuit, sim_node, dut_name,
                all_dut_params[dut_name], net_aliases,
                pval, step, stop, start,
                spice_param_override,
            )
            future_map[fut] = (dut_name, pval)

    # Phase 3: Collect results grouped by DUT
    dut_sweep_results: dict[str, dict[float, object]] = defaultdict(dict)
    for fut in as_completed(future_map):
        dut_name, pval = future_map[fut]
        try:
            _pval, result = fut.result()
            if result is not None:
                dut_sweep_results[dut_name][_pval] = result
        except Exception:
            logger.warning(
                f"Sweep point {pval} for DUT '{dut_name}' failed",
                exc_info=True,
            )

    results: dict[str, tuple[object, dict[str, str]]] = {}
    for dut_name, (_, net_aliases) in dut_circuits.items():
        results[dut_name] = (dut_sweep_results.get(dut_name, {}), net_aliases)

    elapsed = time.monotonic() - t0
    return (elapsed, MultiDutResult(
        results=results,
        dut_params=all_dut_params,
        sweep_param_name=sim_node.get_param_name() or "",
        sweep_param_unit=sim_node.get_param_unit(),
    ))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_simulations_scoped(
    app: fabll.Node,
    solver,
    output_dir: Path,
) -> tuple[dict[str, object], list[SimStats]]:
    """Discover simulation nodes, run them, cache results.

    Simulations within each scope are executed in parallel using a thread
    pool (``ATO_SIM_WORKERS`` env var controls the pool size; defaults to
    CPU count).

    Returns ``(results_registry, sim_stats)`` where:
    - ``results_registry`` maps ``simulation_node_name → result``
    - ``sim_stats`` is a list of per-simulation profiling data
    """
    from faebryk.library.Simulations import (
        SimulationAC,
        SimulationDCOP,
        SimulationSweep,
        SimulationTransient,
    )

    # 1. Discover all simulation nodes (properly typed for isinstance checks)
    sim_nodes = app.get_children(
        direct_only=False,
        types=(SimulationTransient, SimulationSweep, SimulationAC, SimulationDCOP),
    )
    if not sim_nodes:
        return {}, []

    # 1.5 Separate multi-DUT sims from regular sims
    multi_dut_sims: list[fabll.Node] = []
    regular_sims: list[fabll.Node] = []
    for sim_node in sim_nodes:
        duts = sim_node.get_duts()
        if duts:
            multi_dut_sims.append(sim_node)
        else:
            regular_sims.append(sim_node)

    # 2. Group regular sims by simulation scope
    scope_groups: dict[fabll.Node, list[fabll.Node]] = defaultdict(list)
    for sim_node in regular_sims:
        parent_info = sim_node.get_parent()
        parent = parent_info[0] if parent_info is not None else app
        scope = _find_simulation_scope(parent, app)
        scope_groups[scope].append(sim_node)

    results_registry: dict[str, tuple[object, dict[str, str]]] = {}
    all_stats: list[SimStats] = []

    # Single shared thread pool for all simulations (multi-DUT + regular)
    logger.info(f"Simulation thread pool: {_MAX_WORKERS} workers")

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        # 2.5 Multi-DUT simulations: pre-generate netlists (sequential),
        # then submit ALL sim jobs across ALL sims to the thread pool.
        #
        # Phase A: Sequentially generate all netlists (solver not thread-safe)
        # Cache base netlists per DUT — multiple sims sharing the same DUT
        # only need one netlist generation.
        _dut_cache: dict[str, tuple[Circuit, dict[str, str], dict[str, float]]] = {}
        _prepared: list[dict] = []
        for sim_node in multi_dut_sims:
            sim_parent_info = sim_node.get_parent()
            sim_name = sim_parent_info[1] if sim_parent_info else None
            dut_names = sim_node.get_duts()
            parent = sim_parent_info[0] if sim_parent_info is not None else app
            is_sweep = isinstance(sim_node, SimulationSweep)
            sim_type = "sweep" if is_sweep else "transient"

            logger.info(
                f"Preparing multi-DUT {sim_type} '{sim_name}' "
                f"for DUTs: {dut_names}"
            )

            dut_circuits: dict[str, tuple[Circuit, dict[str, str]]] = {}
            all_dut_params: dict[str, dict[str, float]] = {}
            for dut_name in dut_names:
                if dut_name in _dut_cache:
                    base_circuit, net_aliases, dut_params = _dut_cache[dut_name]
                    all_dut_params[dut_name] = dut_params
                    dut_circuits[dut_name] = (base_circuit, net_aliases)
                    continue

                dut_node = _find_child_by_name(parent, dut_name)
                if dut_node is None:
                    logger.warning(
                        f"Multi-DUT: child '{dut_name}' not found in parent"
                    )
                    continue
                try:
                    netlist, net_aliases = generate_spice_netlist(
                        app, solver, scope=dut_node
                    )
                    spice_path = output_dir / f"multidut_{dut_name}.spice"
                    netlist.write(spice_path)
                    circuit = Circuit.load(spice_path)
                    dut_params = _resolve_dut_params(dut_node)
                    all_dut_params[dut_name] = dut_params
                    dut_circuits[dut_name] = (circuit, net_aliases)
                    _dut_cache[dut_name] = (circuit, net_aliases, dut_params)
                except Exception:
                    logger.warning(
                        f"  Multi-DUT '{dut_name}' netlist gen failed — skipping",
                        exc_info=True,
                    )

            # Resolve sweep-specific metadata
            spice_param_override: str | None = None
            param_values: list[float] = []
            step = stop = start = 0.0
            if is_sweep:
                param_values = sim_node.get_param_values()
                step = sim_node.get_time_step() or 0
                stop = sim_node.get_time_stop() or 0
                start = sim_node.get_time_start() or 0
                param_name = sim_node.get_param_name() or ""
                if param_name.startswith("dut."):
                    ato_param = param_name[4:]
                    for dn in dut_names:
                        dn_node = _find_child_by_name(parent, dn)
                        if dn_node is not None:
                            spice_param_override = _resolve_sweep_param_binding(
                                dn_node, ato_param
                            )
                            if spice_param_override:
                                logger.info(
                                    f"  Sweep '{param_name}' → SPICE param "
                                    f"'{spice_param_override}' override"
                                )
                                break

            _prepared.append(dict(
                sim_node=sim_node, sim_name=sim_name, sim_type=sim_type,
                dut_circuits=dut_circuits, all_dut_params=all_dut_params,
                is_sweep=is_sweep, spice_param_override=spice_param_override,
                param_values=param_values, step=step, stop=stop, start=start,
            ))

        logger.info(
            f"Prepared {len(_prepared)} multi-DUT sim(s), "
            f"submitting all jobs to thread pool"
        )

        # Phase B: Submit ALL jobs from ALL multi-DUT sims to the pool
        # Map: future -> (sim_index, dut_name, pval_or_None)
        mdut_future_map: dict = {}
        sim_submit_times: dict[int, float] = {}

        for sim_idx, prep in enumerate(_prepared):
            sim_submit_times[sim_idx] = time.monotonic()
            if prep["is_sweep"]:
                for dut_name, (circuit, _) in prep["dut_circuits"].items():
                    for pval in prep["param_values"]:
                        fut = executor.submit(
                            _run_single_dut_sweep_point_task,
                            circuit, prep["sim_node"], dut_name,
                            prep["all_dut_params"][dut_name],
                            prep["dut_circuits"][dut_name][1],
                            pval, prep["step"], prep["stop"], prep["start"],
                            prep["spice_param_override"],
                        )
                        mdut_future_map[fut] = (sim_idx, dut_name, pval)
            else:
                for dut_name, (circuit, net_aliases) in (
                    prep["dut_circuits"].items()
                ):
                    fut = executor.submit(
                        _run_single_dut_transient_task,
                        circuit, prep["sim_node"], dut_name,
                        prep["all_dut_params"][dut_name], net_aliases,
                    )
                    mdut_future_map[fut] = (sim_idx, dut_name, None)

        # Phase C: Collect results as they complete
        sim_last_complete: dict[int, float] = {}
        sweep_results: dict[int, dict[str, dict[float, object]]] = (
            defaultdict(lambda: defaultdict(dict))
        )
        tran_results: dict[int, dict[str, tuple[object, dict[str, str]]]] = (
            defaultdict(dict)
        )

        for fut in as_completed(mdut_future_map):
            sim_idx, dut_name, pval = mdut_future_map[fut]
            sim_last_complete[sim_idx] = time.monotonic()
            prep = _prepared[sim_idx]
            try:
                if pval is not None:
                    _pval, result = fut.result()
                    if result is not None:
                        sweep_results[sim_idx][dut_name][_pval] = result
                else:
                    result = fut.result()
                    net_aliases = prep["dut_circuits"][dut_name][1]
                    tran_results[sim_idx][dut_name] = (result, net_aliases)
            except Exception:
                logger.warning(
                    f"  Multi-DUT '{prep['sim_name']}' DUT '{dut_name}' "
                    f"(pval={pval}) failed — skipping",
                    exc_info=True,
                )

        # Phase D: Assemble MultiDutResults and record stats
        for sim_idx, prep in enumerate(_prepared):
            sim_name = prep["sim_name"]
            elapsed = (
                sim_last_complete.get(sim_idx, time.monotonic())
                - sim_submit_times[sim_idx]
            )

            if prep["is_sweep"]:
                results: dict[str, tuple[object, dict[str, str]]] = {}
                for dut_name, (_, net_aliases) in prep["dut_circuits"].items():
                    results[dut_name] = (
                        sweep_results[sim_idx].get(dut_name, {}),
                        net_aliases,
                    )
                multi_result = MultiDutResult(
                    results=results,
                    dut_params=prep["all_dut_params"],
                    sweep_param_name=(
                        prep["sim_node"].get_param_name() or ""
                    ),
                    sweep_param_unit=prep["sim_node"].get_param_unit(),
                )
            else:
                multi_result = MultiDutResult(
                    results=tran_results.get(sim_idx, {}),
                    dut_params=prep["all_dut_params"],
                )

            if sim_name:
                results_registry[sim_name] = (multi_result, {})
                logger.info(
                    f"  Cached multi-DUT result for '{sim_name}' "
                    f"({len(multi_result.results)} DUTs, {elapsed:.1f}s)"
                )

            all_stats.append(
                SimStats(
                    name=sim_name or "?",
                    sim_type=f"multi_dut_{prep['sim_type']}",
                    elapsed_s=elapsed,
                    data_points=sum(
                        _count_data_points(r)
                        for r, _ in multi_result.results.values()
                    ),
                )
            )

        # 3. For each scope: generate netlist, run simulations in parallel
        for scope, sim_nodes_in_scope in scope_groups.items():
            scope_name = scope.get_full_name(include_uuid=False) or "circuit"
            scope_slug = scope_name.replace(".", "_").replace(" ", "_")
            logger.info(
                f"Running {len(sim_nodes_in_scope)} simulation(s) "
                f"for scope {scope_name} "
                f"(workers={_MAX_WORKERS})"
            )

            try:
                netlist, net_aliases = generate_spice_netlist(
                    app, solver, scope=scope
                )
                spice_path = output_dir / f"{scope_slug}.spice"
                netlist.write(spice_path)

                # Dump net aliases to file for debugging
                alias_path = output_dir / f"{scope_slug}.aliases.txt"
                with open(alias_path, "w") as af:
                    af.write(f"scope_name: {scope_name}\n")
                    af.write(f"scope_type: {type(scope).__name__}\n")
                    af.write(f"sim_nodes: {len(sim_nodes_in_scope)}\n")
                    af.write(f"subckt_defs: {len(netlist._subcircuit_defs)}\n")
                    af.write(f"netlist_lines: {len(netlist._lines)}\n\n")
                    af.write("=== Net Aliases ===\n")
                    for alias, canon in sorted(net_aliases.items()):
                        af.write(f"  {alias} -> {canon}\n")

                circuit = Circuit.load(spice_path)

                # --- Submit all simulations concurrently ---
                future_map: dict = {}

                for sim_node in sim_nodes_in_scope:
                    trait = sim_node.get_trait(F.is_spice_simulation)
                    sim_parent_info = sim_node.get_parent()
                    sim_name = sim_parent_info[1] if sim_parent_info else None

                    if isinstance(sim_node, SimulationSweep):
                        fut = executor.submit(
                            _run_sweep_sequential,
                            circuit,
                            sim_node,
                            net_aliases,
                        )
                        sim_type = "sweep"
                    elif isinstance(sim_node, SimulationAC):
                        fut = executor.submit(
                            _run_ac_parallel, circuit, sim_node, net_aliases
                        )
                        sim_type = "ac"
                    elif isinstance(sim_node, SimulationDCOP):
                        fut = executor.submit(
                            _run_dcop_parallel, circuit, sim_node, net_aliases
                        )
                        sim_type = "dcop"
                    else:
                        fut = executor.submit(
                            _run_transient_parallel,
                            circuit,
                            sim_node,
                            net_aliases,
                        )
                        sim_type = "transient"

                    future_map[fut] = (sim_node, sim_name, trait, sim_type)

                # --- Collect results as they complete ---
                for fut in as_completed(future_map):
                    sim_node, sim_name, trait, sim_type = future_map[fut]
                    try:
                        elapsed, result = fut.result()
                        trait.store_result(result, net_aliases=net_aliases)

                        data_pts = _count_data_points(result)
                        all_stats.append(
                            SimStats(
                                name=sim_name or "?",
                                sim_type=sim_type,
                                elapsed_s=elapsed,
                                data_points=data_pts,
                            )
                        )

                        if sim_name:
                            results_registry[sim_name] = (result, net_aliases)
                            logger.info(
                                f"  Cached result for simulation '{sim_name}' "
                                f"(type={type(sim_node).__name__}, "
                                f"{elapsed:.1f}s, {data_pts:,} pts)"
                            )
                    except Exception as e:
                        logger.warning(
                            f"  Simulation '{sim_name or '?'}' failed "
                            f"— skipping: {e}",
                            exc_info=True,
                        )

            except Exception:
                logger.warning(
                    f"Netlist generation for scope '{scope_name}' failed "
                    f"— skipping",
                    exc_info=True,
                )

    return results_registry, all_stats
