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
    """Parse 'V1 node+ node- SPEC' and call circuit.set_source(name, spec)."""
    parts = spice_line.strip().split(None, 3)
    if len(parts) >= 4:
        circuit.set_source(parts[0], parts[3])
    elif len(parts) >= 2:
        circuit.set_source(parts[0], parts[1])


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

    result = circuit.tran(step=step, stop=stop, start=start, signals=None, uic=True, tmax=30e-9)
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
        parts = resolved.strip().split(None, 3)
        source_name = parts[0] if len(parts) >= 1 else None
        if source_name:
            existing_spec = circuit.get_source_spec(source_name)
            if existing_spec and "AC" not in existing_spec.upper():
                circuit.set_source(source_name, f"{existing_spec} AC 1")
            elif not existing_spec:
                circuit.set_source(source_name, "DC 0 AC 1")

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

        result = circuit.tran(step=step, stop=stop, start=start, signals=None, uic=True, tmax=30e-9)
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

    # 2. Group by simulation scope
    scope_groups: dict[fabll.Node, list[fabll.Node]] = defaultdict(list)
    for sim_node in sim_nodes:
        parent_info = sim_node.get_parent()
        parent = parent_info[0] if parent_info is not None else app
        scope = _find_simulation_scope(parent, app)
        scope_groups[scope].append(sim_node)

    results_registry: dict[str, tuple[object, dict[str, str]]] = {}
    all_stats: list[SimStats] = []

    # 3. For each scope: generate netlist, run simulations in parallel
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
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

                circuit = Circuit.load(spice_path)

                # --- Submit all simulations concurrently ---
                # future → (sim_node, sim_name, trait, sim_type)
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
