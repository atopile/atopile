# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.app.erc import ERCPowerSourcesShortedError, simple_erc


class ElectricPower(fabll.Node):
    """
    ElectricPower is a class that represents a power rail. Power rails have a
    higher potential (hv), and lower potential (lv) Electrical.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    hv = F.Electrical.MakeChild()
    lv = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt,
    )
    max_current = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ampere,
    )

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.hv.get(), trait=F.has_net_name
        ).setup(name="hv", level=F.has_net_name.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.lv.get(), trait=F.has_net_name
        ).setup(name="lv", level=F.has_net_name.Level.SUGGESTED)

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import ElectricPower

        power_5v = new ElectricPower
        assert power_5v.voltage within 5V +/- 5%
        assert power_5v.max_current <= 1A

        # Connect 2 ElectricPowers together
        power_5v ~ ic.power_input

        # Connect an example bypass capacitor
        power_5v.hv ~> example_capacitor ~> power_5v.lv
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )

    def make_source(self):
        fabll.Traits.create_and_add_instance_to(node=self, trait=F.is_source).setup()

    def make_sink(self):
        fabll.Traits.create_and_add_instance_to(node=self, trait=F.is_sink).setup()


def test_power_source_short():
    """
    Test that a power source is shorted when connected to another power source
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    power_out_1 = ElectricPower.bind_typegraph(tg).create_instance(g=g)
    power_out_2 = ElectricPower.bind_typegraph(tg).create_instance(g=g)

    power_out_1._is_interface.get().connect_to(power_out_2)
    power_out_2._is_interface.get().connect_to(power_out_1)

    power_out_1.make_source()
    power_out_2.make_source()

    with pytest.raises(ERCPowerSourcesShortedError):
        simple_erc(tg)


def test_power_source_no_short():
    """
    Test that a power source is not shorted when connected to another non-power source
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    power_out_1 = ElectricPower.bind_typegraph(tg).create_instance(g=g)
    power_out_2 = ElectricPower.bind_typegraph(tg).create_instance(g=g)

    power_out_1.make_source()

    power_out_1._is_interface.get().connect_to(power_out_2)

    simple_erc(tg)
