# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import pytest

from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.library import L
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint
from faebryk.libs.sets.sets import BoolSet
from faebryk.libs.util import pairwise, times


@pytest.mark.xfail(reason="Solver not smart enough")
def test_fused_power():
    import faebryk.library._F as F
    from faebryk.libs.units import P

    power_in = F.ElectricPower()
    power_out = F.ElectricPower()

    power_in.voltage.constrain_subset(10 * P.V)
    power_in.max_current.constrain_subset(500 * P.mA)

    power_in_fused = power_in.fused()
    power_in_fused.connect(power_out)

    fuse = next(iter(power_in_fused.get_children(direct_only=False, types=F.Fuse)))
    F.is_bus_parameter.resolve_bus_parameters(fuse.get_graph())

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(fuse.trip_current).is_subset_of(
        L.Range.from_center_rel(500 * P.mA, 0.1)
    )
    assert solver.inspect_get_known_supersets(power_out.voltage).is_subset_of(
        L.Single(10 * P.V)
    )
    cur = solver.inspect_get_known_supersets(power_out.max_current)
    assert isinstance(cur, Quantity_Interval_Disjoint)
    assert (cur <= L.Single(500 * P.mA)) == BoolSet(True)


def test_voltage_propagation():
    import faebryk.library._F as F
    from faebryk.libs.units import P

    powers = times(4, F.ElectricPower)

    powers[0].voltage.constrain_subset(L.Range(10 * P.V, 15 * P.V))

    for p1, p2 in pairwise(powers):
        p1.connect(p2)

    F.is_bus_parameter.resolve_bus_parameters(powers[0].get_graph())
    assert (
        DefaultSolver()
        .inspect_get_known_supersets(powers[-1].voltage)
        .is_subset_of(L.Range(10 * P.V, 15 * P.V))
    )

    powers[3].voltage.constrain_subset(10 * P.V)
    assert (
        DefaultSolver()
        .inspect_get_known_supersets(powers[0].voltage)
        .is_subset_of(L.Single(10 * P.V))
    )


@pytest.mark.xfail(reason="Solver not smart enough")
def test_current_consumption_sum_zero():
    import faebryk.library._F as F
    from faebryk.libs.units import P

    class Test(Module):
        p1: F.ElectricPower
        p2: F.ElectricPower
        p3: F.ElectricPower

    test = Test()
    p1 = test.p1
    p2 = test.p2
    p3 = test.p3

    p1.connect(p2)
    p2.connect(p3)

    p1.max_current.alias_is(100 * P.mA)
    p2.max_current.alias_is(200 * P.mA)
    p3.max_current.alias_is(-300 * P.mA)

    p1.bus_max_current_consumption_sum.constrain_le(0 * P.mA)

    F.is_bus_parameter.resolve_bus_parameters(p1.get_graph())
    solver = DefaultSolver()
    out = solver.inspect_get_known_supersets(p1.bus_max_current_consumption_sum)
    assert out.is_subset_of(L.Single(0 * P.mA))


@pytest.mark.xfail(reason="Solver not smart enough")
def test_current_consumption_sum_negative():
    import faebryk.library._F as F
    from faebryk.libs.units import P

    class Test(Module):
        p1: F.ElectricPower
        p2: F.ElectricPower
        p3: F.ElectricPower

    test = Test()
    p1 = test.p1
    p2 = test.p2
    p3 = test.p3

    p1.connect(p2)
    p2.connect(p3)

    p1.max_current.alias_is(300 * P.mA)
    p2.max_current.alias_is(200 * P.mA)
    p3.max_current.alias_is(-300 * P.mA)

    p1.bus_max_current_consumption_sum.constrain_le(0 * P.mA)

    F.is_bus_parameter.resolve_bus_parameters(p1.get_graph())
    solver = DefaultSolver()

    with pytest.raises(Contradiction):
        solver.inspect_get_known_supersets(p1.bus_max_current_consumption_sum)
