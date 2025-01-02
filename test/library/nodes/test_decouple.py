# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import pytest
from pint import Quantity

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.sets.quantity_sets import Quantity_Interval
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert


@pytest.mark.parametrize(
    "capacitances",
    [
        [(1, 100 * P.uF, 0.2)],
        [(2, 100 * P.uF, 0.2)],
        [(1, 100 * P.uF, 0.2), (1, 200 * P.nF, 0.2)],
        [(2, 100 * P.uF, 0.2), (2, 200 * P.nF, 0.2)],
        [(3, 100 * P.uF, 0.2), (2, 200 * P.nF, 0.2), (2, 300 * P.nF, 0.2)],
    ],
)
def test_decouple(capacitances: list[tuple[int, Quantity, float]]):
    class App(Module):
        power: F.ElectricPower

    app = App()

    total_count = 0
    for count, capacitance, tolerance in capacitances:
        total_count += count
        app.power.decoupled.decouple(app, count=count).explicit(capacitance, tolerance)

    cap = app.power.get_trait(F.is_decoupled).capacitor

    caps = cap.get_children_modules(
        types=F.Capacitor, f_filter=lambda c: type(c) is F.Capacitor, include_root=True
    )

    expected = sorted(
        [
            L.Range.from_center_rel(capacitance, tolerance)
            for count, capacitance, tolerance in capacitances
            for _ in range(count)
        ],
        key=lambda x: x.min_elem,
    )

    # TODO remove, this is the alternative to the solver
    lits = [c.capacitance.try_get_literal_subset() for c in caps]
    lits = sorted(lits, key=lambda x: cast_assert(Quantity_Interval, x).min_elem)

    assert lits == expected
