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
    _is_interface = fabll.is_interface.MakeChild()

    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    # ----------------------------------------
    #                WIP
    # ----------------------------------------


    # @staticmethod
    # def define_max_frequency_capability(mode: SpeedMode):
    #     return F.Range(I2C.SpeedMode.low_speed, mode)

    def __preinit__(self) -> None:
        pass

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        for i in range(3):
            net_name = f"HDMI_D{i}"
            self.data[i].p.line.add(
                F.has_net_name(net_name, level=F.has_net_name.Level.SUGGESTED)
            )
            self.data[i].n.line.add(
                F.has_net_name(net_name, level=F.has_net_name.Level.SUGGESTED)
            )
