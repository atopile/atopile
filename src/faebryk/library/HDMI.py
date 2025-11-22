# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

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
    # ----------------------------------------
    #                WIP
    # ----------------------------------------

    # @staticmethod
    # def define_max_frequency_capability(mode: SpeedMode):
    #     return F.Range(I2C.SpeedMode.low_speed, mode)

    def __preinit__(self) -> None:
        pass

    def on_obj_set(self):
        for i, data in enumerate(self.data):
            net_name = f"HDMI_D{i}"
            fabll.Traits.create_and_add_instance_to(
                node=data.get().p.get(), trait=F.has_net_name
            ).setup(name=net_name, level=F.has_net_name.Level.SUGGESTED)
            fabll.Traits.create_and_add_instance_to(
                node=data.get().n.get(), trait=F.has_net_name
            ).setup(name=net_name, level=F.has_net_name.Level.SUGGESTED)
