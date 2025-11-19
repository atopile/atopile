# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.app.erc import ERCPowerSourcesShortedError, simple_erc
from faebryk.libs.util import pairwise, times


def _make_graph_and_typegraph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


def test_power_source_short():
    """
    Test that a power source is shorted when connected to another power source
    """
    g, tg = _make_graph_and_typegraph()

    power_out_1 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
    power_out_2 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)

    power_out_1.get_trait(fabll.is_interface).connect_to(power_out_2)
    power_out_2.get_trait(fabll.is_interface).connect_to(power_out_1)

    power_out_1.make_source()
    power_out_2.make_source()

    with pytest.raises(ERCPowerSourcesShortedError):
        simple_erc(tg)


def test_power_source_no_short():
    """
    Test that a power source is not shorted when connected to another non-power source
    """
    g, tg = _make_graph_and_typegraph()

    power_out_1 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
    power_out_2 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)

    power_out_1.make_source()

    power_out_1.get_trait(fabll.is_interface).connect_to(power_out_2)

    simple_erc(tg)


def test_voltage_propagation():
    # Setup
    powers = times(4, F.ElectricPower)

    X = fabll.Range(10 * P.V, 15 * P.V)
    powers[0].voltage.constrain_subset(X)

    for p1, p2 in pairwise(powers):
        p1.connect(p2)

    F.is_bus_parameter.resolve_bus_parameters(powers[0].get_graph())

    # Test 1, propagate X from p[0] to p[-1]
    solver = DefaultSolver()
    solver.update_superset_cache(*powers)
    assert solver.inspect_get_known_supersets(powers[-1].voltage).is_subset_of(X)

    # Test 2, back propagate Y from p[-1] to p[0]
    Y = fabll.Single(10 * P.V)
    powers[-1].voltage.constrain_subset(Y)

    solver.update_superset_cache(*powers)
    y_back = solver.inspect_get_known_supersets(powers[0].voltage)
    assert y_back.is_subset_of(Y)


def test_current_consumption_sum_zero():
    class Test(fabll.Node):
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
    solver.update_superset_cache(test)
    out = solver.inspect_get_known_supersets(p1.bus_max_current_consumption_sum)
    assert out.is_subset_of(fabll.Single(0 * P.mA))


def test_current_consumption_sum_negative():
    class Test(fabll.Node):
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
        solver.update_superset_cache(test)
        solver.inspect_get_known_supersets(p1.bus_max_current_consumption_sum)
