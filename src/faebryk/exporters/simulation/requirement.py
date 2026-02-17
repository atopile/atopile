"""Graph-paradigm simulation requirements.

Each Requirement is a data node carrying bounds (min/nominal/max),
referencing a net to check, labeling context nets for plotting,
and declaring which analysis to run.

Dataclass fields map 1:1 to future fabll.Node fields:
    net           -> F.Electrical.MakeChild()
    min/nom/max   -> F.Parameters.NumericParameter.MakeChild()
    justification -> F.Parameters.StringParameter.MakeChild()
    context_nets  -> Array of F.Electrical.MakeChild()
    analysis      -> Trait has_sim_config<analysis="op"> (templated)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from faebryk.exporters.simulation.ngspice import Circuit, TransientResult

logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    """A single simulation requirement — bounds + net + metadata."""

    name: str
    net: str
    min: float
    nominal: float
    max: float
    analysis: str = "op"
    justification: str = ""
    context_nets: list[str] = field(default_factory=list)


@dataclass
class TranConfig:
    """Shared transient-analysis configuration."""

    step: float
    stop: float
    source_override: tuple[str, str] | None = None


@dataclass
class RequirementResult:
    """Result of checking a single requirement."""

    requirement: Requirement
    actual: float
    passed: bool


def verify(
    circuit: Circuit,
    requirements: list[Requirement],
    tran: TranConfig | None = None,
) -> tuple[list[RequirementResult], TransientResult | None]:
    """Run simulations and check all requirements.

    1. Partition requirements by analysis type (op vs tran).
    2. Run .op() once, check each op requirement.
    3. If tran requirements exist, apply source override + run .tran(),
       check final value of each tran requirement.

    Returns (results, tran_data). tran_data is needed for plotting.
    """
    op_reqs = [r for r in requirements if r.analysis == "op"]
    tran_reqs = [r for r in requirements if r.analysis == "tran"]

    results: list[RequirementResult] = []

    # -- OP analysis --
    if op_reqs:
        op = circuit.op()
        for req in op_reqs:
            actual = op[req.net]
            passed = req.min <= actual <= req.max
            results.append(RequirementResult(requirement=req, actual=actual, passed=passed))

    # -- Transient analysis --
    tran_data: TransientResult | None = None
    if tran_reqs:
        if tran is None:
            raise ValueError("Transient requirements exist but no TranConfig provided")

        if tran.source_override is not None:
            name, spec = tran.source_override
            circuit.set_source(name, spec)

        # Collect all signals needed (required nets + context nets)
        signals: list[str] = []
        seen: set[str] = set()
        for req in tran_reqs:
            for net in [req.net, *req.context_nets]:
                key = f"v({net})" if not net.startswith(("v(", "i(")) else net
                if key not in seen:
                    signals.append(key)
                    seen.add(key)

        tran_data = circuit.tran(step=tran.step, stop=tran.stop, signals=signals)

        for req in tran_reqs:
            key = f"v({req.net})" if not req.net.startswith(("v(", "i(")) else req.net
            actual = tran_data[key][-1]  # final value
            passed = req.min <= actual <= req.max
            results.append(RequirementResult(requirement=req, actual=actual, passed=passed))

    return results, tran_data


def plot_results(
    results: list[RequirementResult],
    tran_data: TransientResult | None,
    path: str | Path,
) -> Path | None:
    """Plot transient signals with requirement bounds.

    Collects all unique signals from tran requirements (net + context_nets),
    draws dotted red horizontal lines for min/max of each requirement.

    Returns the saved path, or None if matplotlib is unavailable or
    there is no transient data.
    """
    if tran_data is None:
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.info("matplotlib not installed — skipping plot")
        return None

    path = Path(path)
    tran_reqs = [r.requirement for r in results if r.requirement.analysis == "tran"]

    if not tran_reqs:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot all signals referenced by tran requirements
    plotted: set[str] = set()
    for req in tran_reqs:
        for net in [req.net, *req.context_nets]:
            key = f"v({net})" if not net.startswith(("v(", "i(")) else net
            if key not in plotted and key in tran_data:
                ax.plot(tran_data.time, tran_data[key], linewidth=1.5, label=key)
                plotted.add(key)

    # Draw bound lines for each tran requirement
    for req in tran_reqs:
        ax.axhline(
            y=req.min, color="red", linestyle=":", linewidth=1,
            label=f"{req.name} min ({req.min})",
        )
        ax.axhline(
            y=req.max, color="red", linestyle=":", linewidth=1,
            label=f"{req.name} max ({req.max})",
        )

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Voltage / Current")
    ax.set_title("REQ verification — transient")
    ax.legend(fontsize=8, loc="best")
    ax.grid(True, alpha=0.3)

    if tran_data.time:
        t_span = tran_data.time[-1] - tran_data.time[0]
        ax.set_xlim(
            tran_data.time[0] - 0.05 * t_span,
            tran_data.time[-1] + 0.05 * t_span,
        )

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
