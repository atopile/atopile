# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.app.erc import ERCPowerSourcesShortedError, simple_erc


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
