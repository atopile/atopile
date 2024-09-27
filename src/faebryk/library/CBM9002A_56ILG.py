# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class CBM9002A_56ILG(Module):
    """
    USB 2.0 peripheral controller with 16K RAM, 40 GPIOs, and serial debugging

    Cypress Semicon CY7C68013A-56L Clone
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    PA = L.list_field(8, F.ElectricLogic)
    PB = L.list_field(8, F.ElectricLogic)
    PD = L.list_field(8, F.ElectricLogic)
    usb: F.USB2_0
    i2c: F.I2C

    avcc: F.ElectricPower
    vcc: F.ElectricPower

    rdy = L.list_field(2, F.ElectricLogic)
    ctl = L.list_field(3, F.ElectricLogic)
    reset: F.ElectricLogic
    wakeup: F.ElectricLogic

    ifclk: F.ElectricLogic
    clkout: F.ElectricLogic
    xtalin: F.Electrical
    xtalout: F.Electrical

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://corebai.com/Data/corebai/upload/file/20240201/CBM9002A.pdf"
    )

    # ----------------------------------------
    #                connections
    # ----------------------------------------
    def __preinit__(self):
        self.avcc.decoupled.decouple()  # TODO: decouple all pins
        self.vcc.decoupled.decouple()  # TODO: decouple all pins

        F.ElectricLogic.connect_all_node_references(
            self.get_children(direct_only=True, types=ModuleInterface).difference(
                {self.avcc}
            )
        )
