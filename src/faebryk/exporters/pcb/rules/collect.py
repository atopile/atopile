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
    net = F.Net.find_named_net_for_mif(mif)
    if net is None:
        return None
    if net.has_trait(F.has_overriden_name):
        return net.get_trait(F.has_overriden_name).get_name()
    return None


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

    return currents
