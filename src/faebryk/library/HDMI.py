# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class HDMI(fabll.Node):
    """
    HDMI interface
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    power = F.ElectricPower.MakeChild()
    data = [F.DifferentialPair.MakeChild() for _ in range(3)]
    clock = F.DifferentialPair.MakeChild()
    i2c = F.I2C.MakeChild()
    cec = F.ElectricLogic.MakeChild()
    hotplug = F.ElectricLogic.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    # @staticmethod
    # def define_max_frequency_capability(mode: SpeedMode):
    #     return F.Range(I2C.SpeedMode.low_speed, mode)

    for i, diff_pair in enumerate(data):
        diff_pair.add_dependant(
            fabll.Traits.MakeEdge(
                F.has_net_name_suggestion.MakeChild(
                    name=f"HDMI_D{i}",
                    level=F.has_net_name_suggestion.Level.SUGGESTED,
                ),
                owner=[diff_pair, F.DifferentialPair.p],
            )
        )
        diff_pair.add_dependant(
            fabll.Traits.MakeEdge(
                F.has_net_name_suggestion.MakeChild(
                    name=f"HDMI_D{i}",
                    level=F.has_net_name_suggestion.Level.SUGGESTED,
                ),
                owner=[diff_pair, F.DifferentialPair.n],
            )
        )


def test_hdmi():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        hdmi = HDMI.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    datapairs = [p.get() for p in app.hdmi.get().data]
    assert len(datapairs) == 3
    for index, diff_pair in enumerate(datapairs):
        for line in [diff_pair.p.get(), diff_pair.n.get()]:
            suggested_name_trait = line.try_get_trait(F.has_net_name_suggestion)
            assert suggested_name_trait is not None
            assert suggested_name_trait.name == f"HDMI_D{index}"
