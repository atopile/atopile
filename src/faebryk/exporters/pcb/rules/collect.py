from __future__ import annotations

import logging
import math
import shutil
import subprocess
import tempfile
from pathlib import Path as _Path

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.libs.units import Quantity as _Q

logger = logging.getLogger(__name__)


def _to_unit_scalar(value, unit: str) -> float | None:
    try:
        if isinstance(value, _Q):
            return float(value.to(unit).m)
        return float(value)
    except Exception:
        return None


def _find_net_name(mif: F.Electrical) -> str | None:
    # Prefer the name on the interface, then any explicit overridden net name
    try:
        if mif.has_trait(F.has_net_name):
            return mif.get_trait(F.has_net_name).name
    except Exception:
        pass
    try:
        net = F.Net.find_named_net_for_mif(mif)
        if net and net.has_trait(F.has_overriden_name):
            return net.get_trait(F.has_overriden_name).get_name()
    except Exception:
        pass
    return None


def _get_value_in_units(solver: Solver, param, unit: str) -> float | None:
    try:
        val = solver.get_any_single(param, lock=False)
        out = _to_unit_scalar(val, unit)
        if out is not None and math.isfinite(out):
            return out
    except Exception:
        pass
    # Fallback to literal
    try:
        lit = param.get_literal()
        out = _to_unit_scalar(lit, unit)
        if out is not None and math.isfinite(out):
            return out
    except Exception:
        pass
    return None


def run_ngspice_op(
    lines_in: list[str], ng_path: str, vcount: int, rcount: int
) -> str | None:
    """Write an OP deck to a temp dir, run ngspice, and return log text."""
    try:
        with tempfile.TemporaryDirectory() as td:
            deck = _Path(td) / "dc.cir"
            log = _Path(td) / "out.log"
            logger.info("rules: DC sim SPICE deck:\n%s", "\n".join(lines_in))
            deck.write_text("\n".join(lines_in), encoding="utf-8")

            logger.info(
                "rules: running DC sim with %d sources and %d resistors",
                vcount,
                rcount,
            )
            subprocess.run(
                [ng_path, "-b", "-o", str(log), str(deck)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return log.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def _solve_dc_with_spice(app: Module, solver: Solver) -> dict[str, float] | None:
    """Use ngspice to compute DC operating point currents.

    Elements:
      - Vx: ElectricPower.hv to lv (DC voltage if known)
      - Rx: Resistors (R)
    We parse resistor currents and accumulate per-net currents.
    """
    ng = shutil.which("ngspice")
    if not ng:
        logger.info("rules: ngspice not found; skipping DC current solve")
        return None

    lines: list[str] = ["* atopile dc solver"]

    def net_id(mif: F.Electrical) -> str:
        name = _find_net_name(mif)
        return name if name is not None else mif.get_full_name()

    # Voltage sources
    vcount = 0
    src_nodes: list[tuple[str, str]] = []
    for p in app.get_children(direct_only=False, types=F.ElectricPower):
        vn = _get_value_in_units(solver, p.voltage, "volt")
        if vn is None:
            continue
        vcount += 1
        a = net_id(p.hv)
        b = net_id(p.lv)
        lines.append(f"V{vcount} {a} {b} DC {vn}")
        src_nodes.append((a, b))

    # Resistors (preserve order in a list for stable mapping back from results)
    rcount = 0
    res_list: list[F.Resistor] = []
    res_nodes: list[tuple[str, str]] = []
    res_ids: list[str] = []

    for r in app.get_children_modules(direct_only=False, types=F.Resistor):
        R = _get_value_in_units(solver, r.resistance, "ohm")
        if R is None or R <= 0:
            continue
        a = net_id(r.unnamed[0])
        b = net_id(r.unnamed[1])
        rcount += 1
        res_list.append(r)
        res_nodes.append((a, b))
        # Use sequential SPICE-friendly IDs and add Ato name as a comment
        rid = f"R{rcount}"
        try:
            ato_name = r.get_full_name()
        except Exception:
            ato_name = f"Resistor_{rcount}"
        lines.append(f"* {rid} ato={ato_name}")
        res_ids.append(rid)
        lines.append(f"{rid} {a} {b} {R}")

    if rcount == 0 or vcount == 0:
        logger.info("rules: DC sim skipped (rcount=%d, vcount=%d)", rcount, vcount)
        return None

    # Control: print resistor currents
    # ngspice convention: current flows from first to second node; we take abs
    prints = " ".join(
        [f"@V{idx}[i]" for idx in range(1, vcount + 1)]
        + [f"@{rid}[i]" for rid in res_ids]
    )
    lines += [
        ".op",
        f".print OP {prints}",
        ".end",
    ]

    txt = run_ngspice_op(lines, ng, vcount, rcount)
    if txt is None:
        logger.warning("rules: DC sim failed to run; skipping")
        return None

    # Parse @-print tables to extract currents in a deterministic way
    vals: list[float] = []
    src_vals: list[float] | None = None
    try:
        all_currents: dict[str, float] = {}
        lines_list = txt.splitlines()
        for idx, line in enumerate(lines_list):
            if "@" in line and "[i]" in line:
                header_vars: list[str] = []
                for p in line.split():
                    if "@" in p and "[i]" in p.lower():
                        header_vars.append(
                            p.upper().replace("@", "").replace("[I]", "")
                        )
                if not header_vars:
                    continue
                # Find first data row after header
                for j in range(idx + 1, min(idx + 5, len(lines_list))):
                    row = lines_list[j].strip()
                    if not row or row.startswith("-") or row.startswith("*"):
                        continue
                    parts = row.split()
                    if len(parts) > len(header_vars):
                        parts = parts[1:]
                    if len(parts) == len(header_vars):
                        for var, val_str in zip(header_vars, parts):
                            try:
                                all_currents[var] = abs(float(val_str))
                            except Exception:
                                pass
                        break

        if all_currents:
            src_vals = [all_currents.get(f"V{i}", 0.0) for i in range(1, vcount + 1)]
            vals = [all_currents.get(rid, 0.0) for rid in res_ids]
            logger.info(
                "rules: DC sim parsed currents: %s",
                ", ".join(f"{k}={v:.6g}A" for k, v in all_currents.items()),
            )
    except Exception:
        return None

    if len(vals) != rcount:
        return None

    # Map currents back to nets: for each resistor, attribute its current to both nets
    per_net: dict[str, float] = {}
    for idx_i, (r, current, rid) in enumerate(zip(res_list, vals, res_ids), start=1):
        a_name = _find_net_name(r.unnamed[0]) or net_id(r.unnamed[0])
        b_name = _find_net_name(r.unnamed[1]) or net_id(r.unnamed[1])
        per_net[a_name] = max(per_net.get(a_name, 0.0), current)
        per_net[b_name] = max(per_net.get(b_name, 0.0), current)
        try:
            try:
                ato_name = r.get_full_name()
            except Exception:
                ato_name = None
            label = f"{rid} ({ato_name})" if ato_name else rid
            logger.info(
                "rules: %s %s-%s current=%.6g A",
                label,
                a_name,
                b_name,
                current,
            )
        except Exception:
            pass

    # Attribute source branch current to its terminal nets (VCC/GND, etc.)
    if src_vals is not None:
        for (a_id, b_id), cur in zip(src_nodes, src_vals):
            per_net[a_id] = max(per_net.get(a_id, 0.0), cur)
            per_net[b_id] = max(per_net.get(b_id, 0.0), cur)

    # Names are already stable via _find_net_name() or deterministic N# fallback

    # Log a concise summary of DC sim currents
    items = list(per_net.items())
    preview = ", ".join([f"{k}: {v:.4g} A" for k, v in items[:10]])
    more = "" if len(items) <= 10 else f", ... (+{len(items) - 10} more)"
    logger.info("rules: DC sim currents: %s%s", preview, more)

    return per_net if per_net else None


def collect_net_currents(app: Module, solver: Solver) -> dict[str | None, float]:
    """Return mapping of net name (or None) -> max current seen on that net."""
    currents: dict[str | None, float] = {}

    for mif in app.get_children(direct_only=False, types=F.Electrical):
        current_A = _get_value_in_units(solver, mif.current, "ampere")

        if current_A is None:
            continue

        name = _find_net_name(mif)
        currents[name] = max(currents.get(name, 0.0), current_A)

    # Propagate currents across simple series components (e.g., Resistor):
    # both sides should inherit the maximum of the two sides.
    try:
        for r in app.get_children_modules(direct_only=False, types=F.Resistor):
            a = _find_net_name(r.unnamed[0])
            b = _find_net_name(r.unnamed[1])
            if a is None and b is None:
                continue
            combined = max(currents.get(a, 0.0), currents.get(b, 0.0))
            if combined > 0:
                if a is not None:
                    currents[a] = max(currents.get(a, 0.0), combined)
                if b is not None:
                    currents[b] = max(currents.get(b, 0.0), combined)
    except Exception:
        # If for any reason resistor introspection fails, skip propagation
        pass

    # DC solve using only resistors and power rails (if possible)
    try:
        dc = _solve_dc_with_spice(app, solver)
        if dc:
            for n, i in dc.items():
                currents[n] = max(currents.get(n, 0.0), i)
        else:
            logger.info("rules: no DC sim results; using literal/solver currents only")
    except Exception:
        logger.info("rules: DC sim step encountered an error; using non-sim currents")
        pass

    # Final summary: concise debug-only summary
    total = len(currents)
    if currents:
        top_net, top_i = max(currents.items(), key=lambda kv: kv[1])
        logger.debug(
            "rules: net currents summary: total=%d, max=%s=%.4g A",
            total,
            top_net,
            top_i,
        )
    else:
        logger.debug("rules: net currents summary: total=0")

    return currents
