# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.app.parameters import resolve_dynamic_parameters
from faebryk.libs.library import L
from faebryk.libs.test.solver import solve_and_test
from faebryk.libs.util import pairwise, times


def test_fused_power():
    import faebryk.library._F as F
    from faebryk.libs.units import P

    power_in = F.ElectricPower()
    power_out = F.ElectricPower()

    power_in.voltage.constrain_subset(10 * P.V)
    power_in.max_node_current_consumption.constrain_subset(500 * P.mA)

    power_in_fused = power_in.fused()
    power_in_fused.connect(power_out)

    fuse = next(iter(power_in_fused.get_children(direct_only=False, types=F.Fuse)))
    resolve_dynamic_parameters(fuse.get_graph())

    solve_and_test(
        power_in,
        fuse.trip_current.operation_is_subset(L.Range.from_center_rel(500 * P.mA, 0.1)),
        power_out.voltage.operation_is_subset(10 * P.V),
        power_out.max_node_current_consumption.operation_is_le(500 * P.mA * 0.9),
    )


def test_voltage_propagation():
    import faebryk.library._F as F
    from faebryk.libs.units import P

    powers = times(4, F.ElectricPower)

    powers[0].voltage.alias_is(L.Range(10 * P.V, 15 * P.V))

    for p1, p2 in pairwise(powers):
        p1.connect(p2)

    resolve_dynamic_parameters(powers[0].get_graph())
    solve_and_test(
        powers[-1],
        powers[-1].voltage.operation_is_subset(L.Range(10 * P.V, 15 * P.V)),
    )

    powers[3].voltage.alias_is(10 * P.V)
    solve_and_test(
        powers[0],
        powers[0].voltage.operation_is_subset(10 * P.V),
    )


def test_current_consumption_sum():
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

    p1.max_node_current_consumption.alias_is(100 * P.mA)
    p2.max_node_current_consumption.alias_is(200 * P.mA)
    p3.max_node_current_consumption.alias_is(-300 * P.mA)

    resolve_dynamic_parameters(p1.get_graph())
    solver = DefaultSolver()
    out = solver.inspect_get_known_supersets(p1.bus_max_current_consumption_sum)
    assert out.is_subset_of(L.Single(0 * P.mA))
