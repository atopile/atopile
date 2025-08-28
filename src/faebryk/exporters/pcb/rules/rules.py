from __future__ import annotations

import logging
from pathlib import Path

from more_itertools import first

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.libs.kicad.fileformats_latest import C_kicad_pcb_file, C_kicad_dru_file
from typing import Any, cast
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint

from .collect import collect_net_currents

logger = logging.getLogger(__name__)


def _rules_cfg(name: str, default):
    """Best-effort fetch of a rules config value from atopile config.

    Looks under config.build.rules, then config.rules, then top-level config.
    Falls back to provided default if any access fails or key not present.
    """
    try:
        from atopile.config import config  # type: ignore

        # config.build.rules (mapping or attribute)
        try:
            build = getattr(config, "build", None)
            rules = getattr(build, "rules", None)
            if isinstance(rules, dict) and name in rules:
                return rules[name]
            if rules is not None and hasattr(rules, name):
                return getattr(rules, name)
        except Exception:
            pass

        # config.rules (mapping or attribute)
        try:
            rules2 = getattr(config, "rules", None)
            if isinstance(rules2, dict) and name in rules2:
                return rules2[name]
            if rules2 is not None and hasattr(rules2, name):
                return getattr(rules2, name)
        except Exception:
            pass

        # direct attribute
        try:
            if hasattr(config, name):
                return getattr(config, name)
        except Exception:
            pass
    except Exception:
        pass
    return default


def _write_rules_file_dataclass(dru: C_kicad_dru_file, path: Path) -> None:
    """Serialize the DRU dataclass to file using SEXP serializer."""
    path.parent.mkdir(parents=True, exist_ok=True)
    dru.dumps(path)


# New: render exact KiCad DRU s-exprs from the dataclass
def _write_rules_file_kicad(dru: C_kicad_dru_file, path: Path) -> None:
    def _mm_str(v: float) -> str:
        return f"{v:.2f}mm"

    lines: list[str] = ["(version 1)"]
    for cr in getattr(dru, "rules", []) or []:
        r = cr.rule
        name = r.name if isinstance(r.name, str) else str(r.name)
        clauses: list[str] = []
        if r.layer:
            clauses.append(f'(layer "{r.layer}")')
        if r.condition:
            cond = (
                r.condition.expression
                if hasattr(r.condition, "expression")
                else r.condition
            )
            clauses.append(f'(condition "{cond}")')
        for c in getattr(r, "constraints", []) or []:
            cname = c.__class__.__name__
            if cname == "TrackWidth":
                segs_tw: list[str] = []
                if getattr(c, "min", None) is not None:
                    segs_tw.append(f"(min {_mm_str(c.min)})")
                if getattr(c, "opt", None) is not None:
                    segs_tw.append(f"(opt {_mm_str(c.opt)})")
                if getattr(c, "max", None) is not None:
                    segs_tw.append(f"(max {_mm_str(c.max)})")
                clauses.append(f"(constraint track_width {' '.join(segs_tw)})")
            elif cname == "DiffPairGap":
                segs_dpg: list[str] = []
                if getattr(c, "min", None) is not None:
                    segs_dpg.append(f"(min {_mm_str(c.min)})")
                if getattr(c, "opt", None) is not None:
                    segs_dpg.append(f"(opt {_mm_str(c.opt)})")
                if getattr(c, "max", None) is not None:
                    segs_dpg.append(f"(max {_mm_str(c.max)})")
                clauses.append(f"(constraint diff_pair_gap {' '.join(segs_dpg)})")
            elif cname == "Skew":
                segs_sk: list[str] = []
                if getattr(c, "min", None) is not None:
                    segs_sk.append(f"(min {_mm_str(c.min)})")
                if getattr(c, "opt", None) is not None:
                    segs_sk.append(f"(opt {_mm_str(c.opt)})")
                if getattr(c, "max", None) is not None:
                    segs_sk.append(f"(max {_mm_str(c.max)})")
                clauses.append(f"(constraint skew {' '.join(segs_sk)})")
        rule = f"(rule {name}\n  " + "\n  ".join(clauses) + "\n)"
        lines.append(rule)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


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


def _default_copper_thickness_mm() -> float:
    return float(_rules_cfg("default_copper_thickness_mm", 0.035))


def _stackup_copper_layers(stackup: F.Stackup) -> list[tuple[int, float]]:
    from faebryk.libs.units import Quantity as _Q

    coppers: list[tuple[int, float]] = []

    for idx, layer in enumerate(stackup.layers):
        try:
            material = layer.material.get_literal()
        except Exception:
            material = None
        if isinstance(material, str) and material.lower() == "copper":
            thickness_mm = _default_copper_thickness_mm()  # default
            try:
                t_um = layer.thickness.get_literal()

                # The value should already be in micrometers from p_field(units=P.um)
                # Convert to mm
                if isinstance(t_um, _Q):
                    thickness_mm = float(t_um.to("millimeter").m)
                elif isinstance(t_um, (int, float)):
                    # Plain number, assumed to be in micrometers
                    thickness_mm = float(t_um) / 1000.0
                elif isinstance(t_um, str):
                    # String like "15.2um" - parse it
                    try:
                        q = _Q(t_um)
                        thickness_mm = float(q.to("millimeter").m)
                    except Exception:
                        # Try to extract number assuming um
                        import re

                        match = re.match(r"([\d.]+)", t_um)
                        if match:
                            thickness_mm = float(match.group(1)) / 1000.0
                        else:
                            raise ValueError(f"Cannot parse thickness: {t_um}")
                else:
                    raise ValueError(f"Unexpected thickness type: {type(t_um)}")

            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                default_t = _default_copper_thickness_mm()
                logger.warning(
                    ("Layer %d: failed to get thickness, using default %.3fmm: %s"),
                    idx,
                    default_t,
                    e,
                )
                thickness_mm = _default_copper_thickness_mm()

            coppers.append((idx, thickness_mm))
    return coppers


def _fallback_copper_layers() -> list[tuple[int, float]]:
    t = _default_copper_thickness_mm()
    return [(0, t), (1, t)]


def _copper_layers_from_kicad_board() -> list[tuple[int, float]]:
    """Read copper layer thicknesses directly from the KiCad board stackup.

    Returns list of (stackup_index, thickness_mm) in top-to-bottom order.
    """
    try:
        from atopile.config import config

        pcb_path = config.build.paths.layout
        if not pcb_path:
            return []
        pcb = C_kicad_pcb_file.loads(pcb_path)
        setup = pcb.kicad_pcb.setup
        if setup is None or setup.stackup is None:
            return []
        coppers: list[tuple[int, float]] = []
        for idx, layer in enumerate(setup.stackup.layers):
            try:
                if getattr(layer, "type", None) == "copper":
                    t = getattr(layer, "thickness", None)
                    thickness_mm = (
                        float(t) if t is not None else _default_copper_thickness_mm()
                    )
                    coppers.append((idx, thickness_mm))
            except Exception:
                continue
        return coppers
    except Exception:
        return []


def _kicad_stackup_layers() -> (
    list[C_kicad_pcb_file.C_kicad_pcb.C_setup.C_stackup.C_layer] | None
):
    try:
        from atopile.config import config

        pcb_path = config.build.paths.layout
        if not pcb_path:
            return None
        pcb = C_kicad_pcb_file.loads(pcb_path)
        setup = pcb.kicad_pcb.setup
        if setup is None or setup.stackup is None:
            return None
        return setup.stackup.layers
    except Exception:
        return None


def _compute_min_width_from_current(
    current_a: float,
    copper_thickness_mm: float,
    is_outer: bool,
    min_track_mm: float,
    delta_t_c: float | None = None,
) -> float:
    if current_a <= 0:
        return min_track_mm
    j_outer = float(_rules_cfg("j_limit_outer_A_per_mm2", 20.0))
    j_inner = float(_rules_cfg("j_limit_inner_A_per_mm2", 10.0))
    j_limit = j_outer if is_outer else j_inner  # A/mm^2 baseline
    if delta_t_c is not None:
        j_limit *= max(0.5, min(1.5, 10.0 / max(1.0, delta_t_c)))
    width_mm = current_a / (j_limit * max(1e-6, copper_thickness_mm))
    return max(min_track_mm, width_mm)


def export_rules(app: Module, solver: Solver) -> None:
    rules_file = _determine_rules_path()

    stackups = app.get_children_modules(direct_only=False, types=F.Stackup)
    if len(stackups) > 1:
        raise NotImplementedError("Multiple Stackup modules not yet supported")

    ato_stackup: F.Stackup | None = None
    kicad_layers = None
    if len(stackups) == 1:
        ato_stackup = first(stackups)
        copper_layers = _stackup_copper_layers(ato_stackup)
    else:
        copper_layers = []

    # If no Ato stackup or only outer layers detected, fall back to KiCad board
    if not copper_layers or len(copper_layers) < 3:
        kicad_coppers = _copper_layers_from_kicad_board()
        if kicad_coppers:
            copper_layers = kicad_coppers
            kicad_layers = _kicad_stackup_layers()
    if not copper_layers:
        copper_layers = _fallback_copper_layers()

    layer_names = _kicad_cu_layer_names(len(copper_layers))

    min_track_mm = float(_rules_cfg("min_track_width_mm", 0.1))

    net_currents = collect_net_currents(app, solver)
    # Dataclass-based DRU assembly
    dru = C_kicad_dru_file()
    rules_dataclass: list[C_kicad_dru_file.C_commented_rule] = []

    if not net_currents:
        for i, (_stack_idx, _t_mm) in enumerate(copper_layers):
            layer_name = layer_names[i] if i < len(layer_names) else f"In{i}.Cu"

            # Build rule with TrackWidth(min=opt=min_track_mm)
            rule = C_kicad_dru_file.C_commented_rule.C_rule(
                name=f"current_width_default_{layer_name.replace('.', '_')}",
                layer=layer_name,
                constraints=cast(
                    Any,
                    [
                        C_kicad_dru_file.C_commented_rule.C_rule.C_constraint.TrackWidth(
                            min=min_track_mm, opt=min_track_mm, max=None
                        )
                    ],
                ),
            )
            rules_dataclass.append(C_kicad_dru_file.C_commented_rule(rule=rule))
        dru.rules = rules_dataclass
        _write_rules_file_dataclass(dru, rules_file)
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

            constraints: list[Any] = [
                C_kicad_dru_file.C_commented_rule.C_rule.C_constraint.TrackWidth(
                    min=width_mm, opt=width_mm, max=None
                )
            ]
            condition = None
            if is_named:
                condition = C_kicad_dru_file.C_commented_rule.C_rule.C_expression(
                    expression=f"A.NetName == '{net_name}'"
                )
            rule = C_kicad_dru_file.C_commented_rule.C_rule(
                name=f"current_width_{tag}_{layer_name.replace('.', '_')}",
                layer=layer_name,
                condition=condition,
                constraints=cast(Any, constraints),
            )
            rules_dataclass.append(C_kicad_dru_file.C_commented_rule(rule=rule))

    # ------ Differential Pair Rules ------
    def _get_ohms(param) -> float | None:
        try:
            from faebryk.libs.units import Quantity as _Q

            # Try literal first
            lit = param.get_literal()
            if isinstance(lit, _Q):
                return float(lit.to("ohm").m)
            elif lit is not None:
                return float(lit)
        except Exception:
            pass

        # Try solver superset
        try:
            sup = solver.inspect_get_known_supersets(param)
            if isinstance(sup, Quantity_Interval_Disjoint):
                if sup.is_single_element() and sup.min_elem is not None:
                    val = sup.min_elem
                    if isinstance(val, _Q):
                        return float(val.to("ohm").m)
                    return float(val)
                # Use midpoint if both bounds exist
                if sup.min_elem is not None and sup.max_elem is not None:
                    min_val = sup.min_elem
                    max_val = sup.max_elem
                    if isinstance(min_val, _Q):
                        min_ohm = float(min_val.to("ohm").m)
                        max_ohm = float(max_val.to("ohm").m)
                        return (min_ohm + max_ohm) / 2.0
                    return (float(min_val) + float(max_val)) / 2.0
                # Fallback to max or min
                for val in [sup.max_elem, sup.min_elem]:
                    if val is not None:
                        if isinstance(val, _Q):
                            return float(val.to("ohm").m)
                        return float(val)
            else:
                # Best effort
                try:
                    val = sup.any()
                    if isinstance(val, _Q):
                        return float(val.to("ohm").m)
                    return float(val)
                except Exception:
                    return None
        except Exception:
            return None
        return None

    def _get_time_ps(param) -> float | None:
        """Extract time value in picoseconds from a parameter."""
        try:
            from faebryk.libs.units import Quantity as _Q

            # Try literal first
            lit = param.get_literal()
            if isinstance(lit, _Q):
                # Convert to picoseconds
                return float(lit.to("picosecond").m)
            elif lit is not None:
                # Assume nanoseconds if no unit
                return float(lit) * 1000.0
        except Exception:
            pass

        # Try solver superset
        try:
            sup = solver.inspect_get_known_supersets(param)
            if isinstance(sup, Quantity_Interval_Disjoint):
                if sup.is_single_element() and sup.min_elem is not None:
                    val = sup.min_elem
                    if isinstance(val, _Q):
                        return float(val.to("picosecond").m)
                    # Assume nanoseconds if no unit
                    return float(val) * 1000.0
                # Use max value for skew (worst case)
                if sup.max_elem is not None:
                    val = sup.max_elem
                    if isinstance(val, _Q):
                        return float(val.to("picosecond").m)
                    return float(val) * 1000.0
                # Fallback to min
                if sup.min_elem is not None:
                    val = sup.min_elem
                    if isinstance(val, _Q):
                        return float(val.to("picosecond").m)
                    return float(val) * 1000.0
            else:
                # Best effort
                try:
                    val = sup.any()
                    if isinstance(val, _Q):
                        return float(val.to("picosecond").m)
                    return float(val) * 1000.0
                except Exception:
                    return None
        except Exception:
            return None
        return None

    def _time_ps_to_length_mm(ps: float, er: float) -> float:
        """Convert time in picoseconds to length in millimeters.

        Args:
            ps: Time delay in picoseconds
            er: Relative permittivity of the dielectric

        Returns:
            Length in millimeters
        """
        # Speed of light in vacuum (mm/ps)
        c0_mm_ps = 299.792458  # mm/ps (speed of light in vacuum)

        # Propagation velocity in the medium
        # For PCB traces: v = c0 / sqrt(er_eff)
        # For microstrip, er_eff is between 1 and er (typically ~0.6*er
        # for typical geometries)
        # For stripline, er_eff ≈ er
        # Use conservative estimate with full er for now
        v_mm_ps = c0_mm_ps / math.sqrt(er)

        # Convert time to length
        return ps * v_mm_ps

    # Simple microstrip single-ended width solver (Hammerstad approx, robust)
    import math

    def _microstrip_Z0(w_mm: float, h_mm: float, t_mm: float, er: float) -> float:
        h = max(h_mm, 1e-6)
        t = max(t_mm, 1e-6)
        w = max(w_mm, 1e-6)
        u = w / h
        a = (
            1
            + (1 / 49) * math.log((u**4 + (u / 52) ** 2) / (u**4 + 0.432))
            + (1 / 18.7) * math.log(1 + (u / 18.1) ** 3)
        )
        b = 0.564 * ((er - 0.9) / (er + 3)) ** 0.053
        eeff = (er + 1) / 2 + (er - 1) / 2 * (1 + 10 / u) ** (-a * b)
        du = t / math.pi / h * (1 + 1 / eeff) * math.log(1 + 4 * math.e / t * (h / w))
        u_eff = u + du
        if u_eff <= 1:
            return 60 / math.sqrt(eeff) * math.log(8 / u_eff + 0.25 * u_eff)
        return (
            120
            * math.pi
            / math.sqrt(eeff)
            / (u_eff + 1.393 + 0.667 * math.log(u_eff + 1.444))
        )

    def _microstrip_w_for_z0(z0: float, h_mm: float, t_mm: float, er: float) -> float:
        # Bisection over width
        w_min = 1e-3
        w_max = max(10 * h_mm, 1e-3)
        z_min = _microstrip_Z0(w_min, h_mm, t_mm, er)
        z_max = _microstrip_Z0(w_max, h_mm, t_mm, er)
        tries = 0
        while (z_min - z0) * (z_max - z0) > 0 and tries < 6:
            w_max *= 2
            z_max = _microstrip_Z0(w_max, h_mm, t_mm, er)
            tries += 1
        w = (w_min + w_max) / 2
        for _ in range(60):
            z = _microstrip_Z0(w, h_mm, t_mm, er)
            if abs(z - z0) < 0.1:
                break
            if z > z0:
                w_min = w
            else:
                w_max = w
            w = (w_min + w_max) / 2
        return max(w, w_min)

    # Symmetric stripline characteristic impedance (Wheeler approx)
    def _stripline_Z0(w_mm: float, h_mm: float, t_mm: float, er: float) -> float:
        h = max(h_mm, 1e-6)
        t = max(t_mm, 1e-6)
        w = max(w_mm, 1e-6)
        return 60.0 / math.sqrt(er) * math.log(1.9 * (4.0 * h / (0.8 * w + t)))

    def _stripline_w_for_z0(z0: float, h_mm: float, t_mm: float, er: float) -> float:
        w_min = 1e-3
        w_max = max(10 * h_mm, 1e-3)
        z_min = _stripline_Z0(w_min, h_mm, t_mm, er)
        z_max = _stripline_Z0(w_max, h_mm, t_mm, er)
        tries = 0
        while (z_min - z0) * (z_max - z0) > 0 and tries < 6:
            w_max *= 2
            z_max = _stripline_Z0(w_max, h_mm, t_mm, er)
            tries += 1
        w = (w_min + w_max) / 2
        for _ in range(60):
            z = _stripline_Z0(w, h_mm, t_mm, er)
            if abs(z - z0) < 0.1:
                break
            if z > z0:
                w_min = w
            else:
                w_max = w
            w = (w_min + w_max) / 2
        return max(w, w_min)

    # Gap heuristics:
    # - Microstrip: use ~2x width as a reasonable default toward 100 ohm diff
    # - Stripline: tighter coupling typical; use ~1.2x width as a starting point
    def _gap_default(is_outer: bool, w_mm: float) -> float:
        return (2.0 * w_mm) if is_outer else (1.2 * w_mm)

    # Store copper layer indices for outer layer detection
    copper_indices = [idx for idx, _ in copper_layers]
    first_copper = copper_indices[0] if copper_indices else None
    last_copper = copper_indices[-1] if copper_indices else None

    logger.info(
        ("rules: copper_layers=%s, first=%s, last=%s, ato_stackup=%s"),
        copper_layers,
        first_copper,
        last_copper,
        "YES" if ato_stackup else "NO",
    )

    # Resolve dielectric thickness to nearest reference plane and epsilon_r
    def _nearest_dielectric_props(stack_index: int) -> tuple[float, float]:
        # returns (h_mm to nearest copper reference, er)
        default_er = float(_rules_cfg("default_epsilon_r", 4.2))
        # Ato context
        if ato_stackup is not None:
            layers = ato_stackup.layers

            # helper to_mm
            def _to_mm_any(val) -> float | None:
                try:
                    from faebryk.libs.units import Quantity as _Q

                    if isinstance(val, _Q):
                        return float(val.to("millimeter").m)
                    if val is None:
                        return None
                    # Handle string values like "210um" or "1.065mm"
                    if isinstance(val, str):
                        # Try to parse as Quantity string
                        try:
                            q = _Q(val)
                            return float(q.to("millimeter").m)
                        except Exception:
                            pass
                    # Assume micrometers if plain number
                    return float(val) / 1000.0
                except Exception:
                    return None

            # First check if current layer is copper
            try:
                current_mat = layers[stack_index].material.get_literal()
            except Exception:
                return (0.2, default_er)

            if not (isinstance(current_mat, str) and current_mat.lower() == "copper"):
                return (0.2, default_er)

            # Find distance to nearest copper reference plane
            best_h = None
            best_er = None

            # Determine if this is an outer layer
            is_outer = stack_index == first_copper or stack_index == last_copper

            if is_outer:
                # Outer copper layers - find distance to next copper through dielectrics
                # Look inward only (away from the board edge)
                dir_ = 1 if stack_index == first_copper else -1
                total_h = 0.0
                dielectric_count = 0
                er_sum = 0.0

                logger.info(
                    "rules: outer layer at stack_index=%s, searching dir=%s",
                    stack_index,
                    dir_,
                )

                j = stack_index + dir_
                while 0 <= j < len(layers):
                    try:
                        mat = layers[j].material.get_literal()
                    except Exception as e:
                        logger.info("rules:   index %s no material: %s", j, e)
                        mat = None

                    logger.info("rules:   index %s material=%s", j, mat)

                    if isinstance(mat, str):
                        mat_lower = mat.lower()

                        # If we hit another copper layer, we've found our reference
                        if mat_lower == "copper":
                            if dielectric_count > 0:
                                # Average epsilon_r of dielectrics between coppers
                                avg_er = (
                                    er_sum / dielectric_count
                                    if dielectric_count > 0
                                    else default_er
                                )
                                best_h = total_h
                                best_er = avg_er
                            logger.info(
                                "rules:   found copper at %s, total_h=%.3fmm",
                                j,
                                total_h,
                            )
                            break

                        # Accumulate dielectric thickness (including prepreg, core, FR4)
                        elif mat_lower in {"fr4", "dielectric", "prepreg", "core"}:
                            try:
                                thickness_val = layers[j].thickness.get_literal()
                                h = _to_mm_any(thickness_val)
                                if h is not None:
                                    total_h += h
                                    dielectric_count += 1
                                    logger.info(
                                        "rules:   added dielectric %.3fmm, total now"
                                        " %.3fmm",
                                        h,
                                        total_h,
                                    )
                                    try:
                                        er = float(layers[j].epsilon_r.get_literal())
                                    except Exception:
                                        er = default_er
                                    er_sum += er
                            except Exception as e:
                                logger.info("rules:   failed to get thickness: %s", e)
                                pass
                    j += dir_
            else:
                # Inner copper layers - find distance to nearest copper
                for dir_ in (-1, 1):
                    total_h = 0.0
                    dielectric_count = 0
                    er_sum = 0.0

                    j = stack_index + dir_
                    while 0 <= j < len(layers):
                        try:
                            mat = layers[j].material.get_literal()
                        except Exception:
                            mat = None

                        if isinstance(mat, str):
                            mat_lower = mat.lower()

                            # If we hit another copper layer, we've found our reference
                            if mat_lower == "copper":
                                if dielectric_count > 0:
                                    # Average epsilon_r of dielectrics between coppers
                                    avg_er = (
                                        er_sum / dielectric_count
                                        if dielectric_count > 0
                                        else default_er
                                    )
                                    if best_h is None or total_h < best_h:
                                        best_h = total_h
                                        best_er = avg_er
                                break

                            # Accumulate dielectric thickness
                            elif mat_lower in {"fr4", "dielectric", "prepreg", "core"}:
                                try:
                                    thickness_val = layers[j].thickness.get_literal()
                                    h = _to_mm_any(thickness_val)
                                    if h is not None:
                                        total_h += h
                                        dielectric_count += 1
                                        try:
                                            er = float(
                                                layers[j].epsilon_r.get_literal()
                                            )
                                        except Exception:
                                            er = default_er
                                        er_sum += er
                                except Exception:
                                    pass
                        j += dir_

            return (
                best_h if best_h is not None else 0.2,
                best_er if best_er is not None else default_er,
            )

        # KiCad context
        if kicad_layers is not None:
            best_h = None
            best_er = None

            # Check both directions for inner layers, find closest copper reference
            for dir_ in (-1, 1):
                total_h = 0.0
                dielectric_count = 0
                er_sum = 0.0

                j = stack_index + dir_
                while 0 <= j < len(kicad_layers):
                    lyr = kicad_layers[j]
                    typ = getattr(lyr, "type", "") or ""

                    if typ == "copper":
                        # Found reference copper plane
                        if dielectric_count > 0:
                            avg_er = (
                                er_sum / dielectric_count
                                if dielectric_count > 0
                                else default_er
                            )
                            # Keep the shortest distance
                            if best_h is None or total_h < best_h:
                                best_h = total_h
                                best_er = avg_er
                        break
                    elif (
                        typ.lower() in {"dielectric", "prepreg", "core"}
                        or "FR4" in (getattr(lyr, "material", "") or "").upper()
                    ):
                        # Accumulate dielectric thickness
                        h = getattr(lyr, "thickness", None)
                        er = getattr(lyr, "epsilon_r", None)
                        try:
                            h_val = float(h) if h is not None else 0.0
                            if h_val > 0:
                                total_h += h_val
                                dielectric_count += 1
                                try:
                                    er_val = float(er) if er is not None else default_er
                                except Exception:
                                    er_val = default_er
                                er_sum += er_val
                        except Exception:
                            pass
                    # Skip non-dielectric layers like solder mask
                    j += dir_
            return (best_h if best_h is not None else 0.2, best_er or default_er)

        # Fallback
        return (0.2, default_er)

    # Collect diff pairs and group by impedance
    diff_pairs = app.get_children(direct_only=False, types=F.DifferentialPair)

    # Group differential pairs by their impedance
    dp_by_impedance: dict[float, list[F.DifferentialPair]] = {}
    for dp in diff_pairs:
        zdiff = _get_ohms(dp.impedance)
        if zdiff is None:
            zdiff = 100.0  # Default differential impedance
        if zdiff not in dp_by_impedance:
            dp_by_impedance[zdiff] = []
        dp_by_impedance[zdiff].append(dp)

    # If no diff pairs found, use default 100 ohm rule
    if not dp_by_impedance:
        dp_by_impedance[100.0] = []

    # Generate rules for each impedance group
    for zdiff, dps in dp_by_impedance.items():
        # For differential pairs, the odd-mode impedance is approximately zdiff/2
        # This is a simplification; actual odd-mode depends on coupling
        zodd = zdiff / 2.0

        # Generate per-layer rules for this impedance group
        for i, (stack_idx, t_mm) in enumerate(copper_layers):
            is_outer = i == 0 or i == len(copper_layers) - 1
            h_mm, er = _nearest_dielectric_props(stack_idx)

            # Calculate trace width for the odd-mode impedance
            if is_outer:
                w_mm = _microstrip_w_for_z0(zodd, h_mm, t_mm, er)
            else:
                w_mm = _stripline_w_for_z0(zodd, h_mm, t_mm, er)

            # Calculate gap based on layer type and width
            s_mm = _gap_default(is_outer, w_mm)

            layer_name = layer_names[i] if i < len(layer_names) else f"In{i}.Cu"
            logger.info(
                f"rules: diff_pair {layer_name}: zdiff={zdiff:.0f}Ω zodd={zodd:.0f}Ω "
                f"h={h_mm:.3f}mm t={t_mm:.4f}mm er={er:.1f} "
                f"-> w={w_mm:.3f}mm s={s_mm:.3f}mm (outer={is_outer})"
            )

            # Clamp to minimal manufacturable defaults
            w_mm = max(min_track_mm, w_mm)
            s_mm = max(min_track_mm, s_mm)

            # Build condition based on actual net names if we have specific pairs
            if dps:
                # Try to get net names from the differential pairs
                net_conditions = []
                for dp in dps:
                    try:
                        # Look for nets connected to p and n lines
                        p_nets = F.Net.find_nets_for_mif(dp.p.line)
                        n_nets = F.Net.find_nets_for_mif(dp.n.line)
                        if p_nets and n_nets:
                            # Get base name by removing _P/_N suffix
                            for p_net in p_nets:
                                if p_net.has_trait(F.has_net_name):
                                    p_name = p_net.get_trait(F.has_net_name).name
                                    # Remove _P suffix to get base name
                                    if p_name.endswith("_P"):
                                        base_name = p_name[:-2]
                                        net_conditions.append(
                                            f"A.inDiffPair('{base_name}')"
                                        )
                                        break
                    except Exception:
                        pass

                # Build condition string
                if net_conditions:
                    condition_expr = " || ".join(net_conditions)
                else:
                    # Fallback to generic condition
                    condition_expr = "A.inDiffPair('*')"
            else:
                # Generic rule for all diff pairs
                condition_expr = "A.inDiffPair('*')"

            rule = C_kicad_dru_file.C_commented_rule.C_rule(
                name=f"diff_pair_Z{int(zdiff)}_{layer_name.replace('.', '_')}",
                layer=layer_name,
                condition=C_kicad_dru_file.C_commented_rule.C_rule.C_expression(
                    expression=condition_expr
                ),
                constraints=cast(
                    Any,
                    [
                        C_kicad_dru_file.C_commented_rule.C_rule.C_constraint.TrackWidth(
                            min=None, opt=w_mm, max=None
                        ),
                        C_kicad_dru_file.C_commented_rule.C_rule.C_constraint.DiffPairGap(
                            min=None, opt=s_mm, max=None
                        ),
                    ],
                ),
            )
            rules_dataclass.append(C_kicad_dru_file.C_commented_rule(rule=rule))

    # ------ Differential Pair Skew Rules ------
    # Generate skew rules for each differential pair with a skew constraint
    for dp in diff_pairs:
        # Try to get skew value
        skew_ps = _get_time_ps(dp.skew)
        if skew_ps is None or skew_ps <= 0:
            continue  # Skip if no skew constraint or invalid value

        # Try to get net names for this differential pair
        try:
            p_nets = F.Net.find_nets_for_mif(dp.p.line)
            n_nets = F.Net.find_nets_for_mif(dp.n.line)

            base_name = None
            if p_nets and n_nets:
                # Get base name by removing _P/_N suffix
                for p_net in p_nets:
                    if p_net.has_trait(F.has_net_name):
                        p_name = p_net.get_trait(F.has_net_name).name
                        # Remove _P suffix to get base name
                        if p_name.endswith("_P"):
                            base_name = p_name[:-2]
                            break

            if not base_name:
                continue  # Skip if we can't determine the net names

            # Calculate maximum skew length for each layer
            # We'll use the worst-case (smallest) length across all layers
            min_skew_mm = None
            for i, (stack_idx, _) in enumerate(copper_layers):
                _, er = _nearest_dielectric_props(stack_idx)
                skew_mm = _time_ps_to_length_mm(skew_ps, er)
                if min_skew_mm is None or skew_mm < min_skew_mm:
                    min_skew_mm = skew_mm

            if min_skew_mm is not None:
                # Generate skew rule for this differential pair
                rule = C_kicad_dru_file.C_commented_rule.C_rule(
                    name=f"diff_pair_skew_{base_name.replace('/', '_')}",
                    condition=C_kicad_dru_file.C_commented_rule.C_rule.C_expression(
                        expression=f"A.inDiffPair('{base_name}')"
                    ),
                    constraints=cast(
                        Any,
                        [
                            C_kicad_dru_file.C_commented_rule.C_rule.C_constraint.Skew(
                                min=None, opt=None, max=min_skew_mm
                            )
                        ],
                    ),
                )
                rules_dataclass.append(C_kicad_dru_file.C_commented_rule(rule=rule))

                logger.info(
                    "rules: diff_pair_skew %s: %.1fps -> %.3fmm",
                    base_name,
                    skew_ps,
                    min_skew_mm,
                )

        except Exception as e:
            logger.warning("Failed to generate skew rule for differential pair: %s", e)
            continue

    dru.rules = rules_dataclass
    _write_rules_file_kicad(dru, rules_file)
