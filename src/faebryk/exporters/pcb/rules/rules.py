from __future__ import annotations

from pathlib import Path
from typing import Iterable

from more_itertools import first

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver


def _mm_str(value_mm: float) -> str:
    return f"{value_mm:.2f}mm"


def _kicad_cu_layer_names(num_coppers: int) -> list[str]:
    if num_coppers <= 0:
        return []
    if num_coppers == 1:
        return ["F.Cu"]
    names: list[str] = ["F.Cu"]
    for i in range(1, num_coppers - 1):
        names.append(f"In{i}.Cu")
    names.append("B.Cu")
    return names


def _stackup_copper_layers(stackup: F.Stackup) -> list[tuple[int, float]]:
    """Return list of (layer_index_in_stackup, thickness_mm) for copper layers."""
    coppers: list[tuple[int, float]] = []
    for idx, layer in enumerate(stackup.layers):
        try:
            material = layer.material.get_literal()
        except Exception:
            material = None
        if isinstance(material, str) and material.lower() == "copper":
            try:
                t_um = layer.thickness.get_literal()
            except Exception:
                t_um = 35.0  # default 1 oz approx
            thickness_mm = float(t_um) / 1000.0
            coppers.append((idx, thickness_mm))
    return coppers


def _fallback_copper_layers() -> list[tuple[int, float]]:
    # 2-layer default, top/bottom 35um
    return [(0, 0.035), (1, 0.035)]


def _compute_min_width_from_current(
    current_a: float,
    copper_thickness_mm: float,
    is_outer: bool,
    min_track_mm: float,
    delta_t_c: float | None = None,
) -> float:
    """Simple placeholder for IPC-2152: width = I / (J_limit * t)."""
    if current_a <= 0:
        return min_track_mm
    j_limit = 20.0 if is_outer else 10.0  # A/mm^2
    if delta_t_c is not None:
        j_limit *= max(0.5, min(1.5, 10.0 / max(1.0, delta_t_c)))
    width_mm = current_a / (j_limit * max(1e-6, copper_thickness_mm))
    return max(min_track_mm, width_mm)


def _find_named_net_for_electrical(mif: F.Electrical) -> str | None:
    net = F.Net.find_named_net_for_mif(mif)
    if net is None:
        return None
    if net.has_trait(F.has_overriden_name):
        return net.get_trait(F.has_overriden_name).get_name()
    return None


def _collect_net_currents(app: Module, solver: Solver) -> dict[str | None, float]:
    """Return mapping of net name (or None) -> max current seen on that net.

    Tries fast-path literal extraction first; if unavailable, consults the solver
    for a single-element superset. Falls back to skipping interfaces without a
    resolvable current value.
    """
    from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint

    currents: dict[str | None, float] = {}

    def _as_amps(value) -> float | None:
        try:
            import math

            # Pint Quantity -> scalar in A
            from faebryk.libs.units import Quantity as _Q

            if isinstance(value, _Q):
                scalar = float(value.to("ampere").m)
                return scalar if math.isfinite(scalar) else None
            # Plain number
            scalar = float(value)
            return scalar if math.isfinite(scalar) else None
        except Exception:
            return None

    for mif in app.get_children(direct_only=False, types=F.Electrical):
        current_A: float | None = None

        # Fast path: directly constrained literal
        try:
            lit = mif.current.get_literal()
            current_A = _as_amps(lit)
        except Exception:
            current_A = None

        # Solver-assisted path
        if current_A is None:
            try:
                superset = solver.inspect_get_known_supersets(mif.current)
                # Prefer single-element; otherwise, take a conservative upper bound
                if isinstance(superset, Quantity_Interval_Disjoint):
                    if superset.is_single_element():
                        current_A = _as_amps(superset.min_elem)
                    else:
                        # Use max element if bounded; if unbounded, skip
                        if superset.max_elem is not None:
                            current_A = _as_amps(superset.max_elem)
                else:
                    # Some sets expose any(); best-effort extraction
                    try:
                        any_val = superset.any()
                        current_A = _as_amps(any_val)
                    except Exception:
                        pass
            except Exception:
                pass

        if current_A is None:
            continue

        name = _find_named_net_for_electrical(mif)
        currents[name] = max(currents.get(name, 0.0), current_A)

    return currents


def _emit_rule(name: str, clauses: Iterable[str]) -> str:
    inner = "\n  ".join(clauses)
    return f"(rule {name}\n  {inner}\n)"


def _determine_rules_path() -> Path:
    try:
        from atopile.config import config

        if config.build.paths.layout:
            layout = config.build.paths.layout
            return layout.parent / f"{layout.stem}.kicad_dru"
        return config.build.paths.output_base.with_suffix(".kicad_dru")
    except Exception:
        # Fallback to current directory
        return Path("rules.kicad_dru")


def export_rules(app: Module, solver: Solver) -> None:
    """Export KiCad rules (.kicad_dru). Current: current-based width rules per layer."""
    rules_file = _determine_rules_path()

    # Discover stackup
    stackups = app.get_children_modules(types=F.Stackup)
    if len(stackups) > 1:
        raise NotImplementedError("Multiple Stackup modules not yet supported")

    if len(stackups) == 1:
        stackup = first(stackups)
        copper_layers = _stackup_copper_layers(stackup)
    else:
        copper_layers = _fallback_copper_layers()

    layer_names = _kicad_cu_layer_names(len(copper_layers))

    # Fabrication defaults (until a fabrication module is present)
    min_track_mm = 0.15

    # Collect net currents
    net_currents = _collect_net_currents(app, solver)

    rules: list[str] = ["(version 1)"]

    if not net_currents:
        # Nothing annotated; emit a minimal per-layer default using fabrication min
        for i, (_stack_idx, _t_mm) in enumerate(copper_layers):
            layer_name = layer_names[i] if i < len(layer_names) else f"In{i}.Cu"
            clauses = [
                f'(layer "{layer_name}")',
                (
                    "(constraint track_width "
                    f"(min {_mm_str(min_track_mm)}) "
                    f"(opt {_mm_str(min_track_mm)}))"
                ),
            ]
            rules.append(
                _emit_rule(
                    f"current_width_default_{layer_name.replace('.', '_')}", clauses
                )
            )
        rules_file.parent.mkdir(parents=True, exist_ok=True)
        rules_file.write_text("\n".join(rules), encoding="utf-8")
        return

    # Determine global maximum for unnamed nets fallback
    global_max_current = max(net_currents.values())

    for net_name, current_a in net_currents.items():
        is_named = net_name is not None
        tag = net_name.replace("/", "_") if is_named else "GLOBAL"

        for i, (_stack_idx, t_mm) in enumerate(copper_layers):
            is_outer = i == 0 or i == len(copper_layers) - 1
            width_mm = _compute_min_width_from_current(
                current_a if is_named else global_max_current,
                t_mm,
                is_outer,
                min_track_mm,
            )
            layer_name = layer_names[i] if i < len(layer_names) else f"In{i}.Cu"

            clauses = [
                f'(layer "{layer_name}")',
                (
                    "(constraint track_width "
                    f"(min {_mm_str(width_mm)}) "
                    f"(opt {_mm_str(width_mm)}))"
                ),
            ]
            if is_named:
                # Use KiCad's net name attribute
                clauses.append(f"(condition \"A.NetName == '{net_name}'\")")
            rule_name = f"current_width_{tag}_{layer_name.replace('.', '_')}"
            rules.append(_emit_rule(rule_name, clauses))

    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("\n".join(rules), encoding="utf-8")
