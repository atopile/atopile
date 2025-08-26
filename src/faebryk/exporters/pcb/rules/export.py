from __future__ import annotations

from pathlib import Path

from more_itertools import first

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver

from .collect import collect_net_currents
from .emit import _mm_str, emit_rule, write_rules_file  # type: ignore


def _determine_rules_path() -> Path:
    try:
        from atopile.config import config

        if config.build.paths.layout:
            layout = config.build.paths.layout
            return layout.parent / f"{layout.stem}.kicad_dru"
        return config.build.paths.output_base.with_suffix(".kicad_dru")
    except Exception:
        return Path("rules.kicad_dru")


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
                t_um = 35.0
            thickness_mm = float(t_um) / 1000.0
            coppers.append((idx, thickness_mm))
    return coppers


def _fallback_copper_layers() -> list[tuple[int, float]]:
    return [(0, 0.035), (1, 0.035)]


def _compute_min_width_from_current(
    current_a: float,
    copper_thickness_mm: float,
    is_outer: bool,
    min_track_mm: float,
    delta_t_c: float | None = None,
) -> float:
    if current_a <= 0:
        return min_track_mm
    j_limit = 20.0 if is_outer else 10.0  # A/mm^2 baseline
    if delta_t_c is not None:
        j_limit *= max(0.5, min(1.5, 10.0 / max(1.0, delta_t_c)))
    width_mm = current_a / (j_limit * max(1e-6, copper_thickness_mm))
    return max(min_track_mm, width_mm)


def export_rules(app: Module, solver: Solver) -> None:
    rules_file = _determine_rules_path()

    stackups = app.get_children_modules(types=F.Stackup)
    if len(stackups) > 1:
        raise NotImplementedError("Multiple Stackup modules not yet supported")

    if len(stackups) == 1:
        stackup = first(stackups)
        copper_layers = _stackup_copper_layers(stackup)
    else:
        copper_layers = _fallback_copper_layers()

    layer_names = _kicad_cu_layer_names(len(copper_layers))

    min_track_mm = 0.15

    net_currents = collect_net_currents(app, solver)

    rules: list[str] = []

    if not net_currents:
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
                emit_rule(
                    f"current_width_default_{layer_name.replace('.', '_')}", clauses
                )
            )
        write_rules_file(rules, rules_file)
        return

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
                clauses.append(f"(condition \"A.NetName == '{net_name}'\")")
            rule_name = f"current_width_{tag}_{layer_name.replace('.', '_')}"
            rules.append(emit_rule(rule_name, clauses))

    write_rules_file(rules, rules_file)
