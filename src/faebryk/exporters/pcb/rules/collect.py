from __future__ import annotations

import math

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint


def _as_amps(value) -> float | None:
    try:
        from faebryk.libs.units import Quantity as _Q

        if isinstance(value, _Q):
            scalar = float(value.to("ampere").m)
        else:
            scalar = float(value)
        return scalar if math.isfinite(scalar) else None
    except Exception:
        return None


def _find_net_name(mif: F.Electrical) -> str | None:
    # Prefer explicit overridden names on connected Net objects
    try:
        nets = F.Net.find_nets_for_mif(mif)
        if nets:
            # First check for overridden names
            for n in nets:
                if n.has_trait(F.has_overriden_name):
                    return n.get_trait(F.has_overriden_name).get_name()
            # Then check for suggested/expected names on Net
            for n in nets:
                if n.has_trait(F.has_net_name):
                    try:
                        return n.get_trait(F.has_net_name).name
                    except Exception:
                        pass
    except Exception:
        pass

    # Fallback to suggested names on the interface itself
    if mif.has_trait(F.has_net_name):
        try:
            return mif.get_trait(F.has_net_name).name
        except Exception:
            return None
    return None


def _as_volts(value) -> float | None:
    try:
        from faebryk.libs.units import Quantity as _Q

        if isinstance(value, _Q):
            scalar = float(value.to("volt").m)
        else:
            scalar = float(value)
        return scalar if math.isfinite(scalar) else None
    except Exception:
        return None


def _as_ohms(value) -> float | None:
    try:
        from faebryk.libs.units import Quantity as _Q

        if isinstance(value, _Q):
            scalar = float(value.to("ohm").m)
        else:
            scalar = float(value)
        return scalar if math.isfinite(scalar) else None
    except Exception:
        return None


def _try_get_single_value(solver: Solver, param, to_float_fn) -> float | None:
    # Try literal
    try:
        lit = param.get_literal()
        val = to_float_fn(lit)
        if val is not None:
            return val
    except Exception:
        pass
    # Try solver-known superset
    try:
        sup = solver.inspect_get_known_supersets(param)
        if isinstance(sup, Quantity_Interval_Disjoint):
            # Single element interval
            if sup.is_single_element():
                return to_float_fn(sup.min_elem)
            # Use midpoint if both bounds exist
            try:
                if sup.min_elem is not None and sup.max_elem is not None:
                    minf = to_float_fn(sup.min_elem)
                    maxf = to_float_fn(sup.max_elem)
                    if minf is not None and maxf is not None:
                        return (minf + maxf) / 2.0
                # Fallback to max if available
                if sup.max_elem is not None:
                    val = to_float_fn(sup.max_elem)
                    if val is not None:
                        return val
                # Fallback to min if available
                if sup.min_elem is not None:
                    val = to_float_fn(sup.min_elem)
                    if val is not None:
                        return val
            except Exception:
                pass
        else:
            # best effort
            try:
                return to_float_fn(sup.any())
            except Exception:
                return None
    except Exception:
        return None
    return None


def solve_dc_currents(app: Module, solver: Solver) -> dict[str, float] | None:
    """Compute DC per-net currents via ngspice (if available)."""
    return _solve_dc_with_spice(app, solver)


def _solve_dc_with_spice(app: Module, solver: Solver) -> dict[str, float] | None:
    """Use ngspice to compute DC operating point currents.

    Elements:
      - Vx: ElectricPower.hv to lv (DC voltage if known)
      - Rx: Resistors (R)
    We parse resistor currents and accumulate per-net currents.
    """
    import shutil
    import tempfile
    from pathlib import Path as _Path

    ng = shutil.which("ngspice")
    if not ng:
        return None

    lines: list[str] = ["* atopile dc solver"]
    # Map logical Net objects (preferred) or unique MIF keys to SPICE node names
    net_ids: dict[object, str] = {}

    def net_id(mif: F.Electrical) -> str:
        name = _find_net_name(mif)
        if name:
            return name
        # Prefer stable identity by underlying Net object
        try:
            net_obj = F.Net.find_from_part_of_mif(mif)
        except Exception:
            net_obj = None
        key = net_obj if net_obj is not None else ("mif:", mif.get_full_name())
        if key in net_ids:
            return net_ids[key]
        nid = f"N{len(net_ids) + 1}"
        net_ids[key] = nid
        return nid

    # Voltage sources
    vcount = 0
    src_nodes: list[tuple[str, str]] = []
    for p in app.get_children(direct_only=False, types=F.ElectricPower):
        vn = _try_get_single_value(solver, p.voltage, _as_volts)
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
    for r in app.get_children_modules(direct_only=False, types=F.Resistor):
        R = _try_get_single_value(solver, r.resistance, _as_ohms)
        if R is None or R <= 0:
            continue
        a = net_id(r.unnamed[0])
        b = net_id(r.unnamed[1])
        rcount += 1
        res_list.append(r)
        res_nodes.append((a, b))
        lines.append(f"R{rcount} {a} {b} {R}")

    if rcount == 0 or vcount == 0:
        return None

    # Control: print resistor currents
    # ngspice convention: current flows from first to second node; we take abs
    prints = " ".join(
        [f"@V{idx}[i]" for idx in range(1, vcount + 1)]
        + [f"@R{idx}[i]" for idx in range(1, rcount + 1)]
    )
    lines += [
        ".op",
        f".print OP {prints}",
        ".end",
    ]

    try:
        with tempfile.TemporaryDirectory() as td:
            deck = _Path(td) / "dc.cir"
            log = _Path(td) / "out.log"
            deck.write_text("\n".join(lines), encoding="utf-8")
            import subprocess

            subprocess.run(
                [ng, "-b", "-o", str(log), str(deck)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            txt = log.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    # First try structured blocks and @-prints to extract currents
    vals: list[float] = []
    src_vals: list[float] | None = None
    try:
        lines_iter = iter(txt.splitlines())
        device_order: list[str] = []
        device_currents: list[float] | None = None
        for line in lines_iter:
            if line.strip().lower().startswith("resistor: simple linear resistor"):
                # scan subsequent lines for 'device' and then 'i'
                for sub in lines_iter:
                    st = sub.strip()
                    if not st:
                        continue
                    toks = st.split()
                    if toks[0].lower() == "device":
                        # names like r2 r1
                        device_order = [t.upper() for t in toks[1:]]
                    if toks[0].lower() == "i" and device_order:
                        # currents aligned to device_order
                        vals = []
                        for t in toks[1 : 1 + len(device_order)]:
                            try:
                                vals.append(abs(float(t)))
                            except Exception:
                                vals.append(0.0)
                        device_currents = vals
                        break
                break
        if device_order and device_currents is not None:
            # Align to R1..Rrcount
            order_map = {name: cur for name, cur in zip(device_order, device_currents)}
            vals = []
            for idx_i in range(1, rcount + 1):
                vals.append(float(order_map.get(f"R{idx_i}", 0.0)))
        # Independently try parsing the @ print table for source and resistor currents
        for idx, line in enumerate(txt.splitlines()):
            if "@V1[" in line or "@v1[" in line or "@R1[" in line or "@r1[" in line:
                # Next non-empty line should be numeric row
                # Gather following lines until we find parsable floats
                for j in range(idx + 1, len(txt.splitlines())):
                    row = txt.splitlines()[j].strip()
                    if not row:
                        continue
                    parts = row.split()
                    floats: list[float] = []
                    ok = True
                    for p in parts:
                        try:
                            floats.append(float(p))
                        except Exception:
                            ok = False
                            break
                    if not ok:
                        continue
                    if len(floats) >= (vcount + rcount):
                        src_vals = [abs(x) for x in floats[:vcount]] if vcount else []
                        # Only replace vals if we didn't already get
                        # structured resistor values
                        if not vals:
                            vals = [abs(x) for x in floats[vcount : vcount + rcount]]
                        break
                break
        # As an additional robust path, parse Vsource device blocks for currents
        try:
            lines_iter2 = iter(txt.splitlines())
            v_currents: dict[str, float] = {}
            current_dev: str | None = None
            for line in lines_iter2:
                if (
                    line.strip()
                    .lower()
                    .startswith("vsource: independent voltage source")
                ):
                    # read subsequent lines until blank line
                    for sub in lines_iter2:
                        st = sub.strip()
                        if not st:
                            break
                        toks = st.split()
                        key = toks[0].lower()
                        if key == "device" and len(toks) > 1:
                            current_dev = toks[1].upper()
                        elif key == "i" and len(toks) > 1 and current_dev:
                            try:
                                v_currents[current_dev] = abs(float(toks[1]))
                            except Exception:
                                pass
                    # continue scanning (in case multiple sources)
            if v_currents and vcount:
                src_vals = [v_currents.get(f"V{i}", 0.0) for i in range(1, vcount + 1)]
        except Exception:
            pass
    except Exception:
        return None

    if len(vals) != rcount:
        return None

    # Map currents back to nets: for each resistor, attribute its current to both nets
    per_net: dict[str, float] = {}
    for r, current in zip(res_list, vals):
        for mif in (r.unnamed[0], r.unnamed[1]):
            # Prefer human/readable net names; fallback to SPICE net ids used in deck
            name = _find_net_name(mif) or net_id(mif)
            per_net[name] = max(per_net.get(name, 0.0), current)

    # Attribute source branch current to its terminal nets (VCC/GND, etc.)
    if src_vals is not None:
        for (a_id, b_id), cur in zip(src_nodes, src_vals):
            per_net[a_id] = max(per_net.get(a_id, 0.0), cur)
            per_net[b_id] = max(per_net.get(b_id, 0.0), cur)

    return per_net if per_net else None


def collect_net_currents(app: Module, solver: Solver) -> dict[str | None, float]:
    """Return mapping of net name (or None) -> max current seen on that net."""
    currents: dict[str | None, float] = {}

    for mif in app.get_children(direct_only=False, types=F.Electrical):
        current_A: float | None = None
        # Direct literal
        try:
            lit = mif.current.get_literal()
            current_A = _as_amps(lit)
        except Exception:
            current_A = None

        if current_A is None:
            # Solver superset
            try:
                superset = solver.inspect_get_known_supersets(mif.current)
                if isinstance(superset, Quantity_Interval_Disjoint):
                    if superset.is_single_element():
                        current_A = _as_amps(superset.min_elem)
                    elif superset.max_elem is not None:
                        current_A = _as_amps(superset.max_elem)
                else:
                    try:
                        any_val = superset.any()
                        current_A = _as_amps(any_val)
                    except Exception:
                        pass
            except Exception:
                pass

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
        dc = solve_dc_currents(app, solver)
        if dc:
            for n, i in dc.items():
                currents[n] = max(currents.get(n, 0.0), i)
    except Exception:
        pass

    return currents
