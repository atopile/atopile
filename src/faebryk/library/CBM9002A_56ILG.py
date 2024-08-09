# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.I2C import I2C
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.util import times


class CBM9002A_56ILG(Module):
    """
    USB 2.0 peripheral controller with 16K RAM, 40 GPIOs, and serial debugging

    Cypress Semicon CY7C68013A-56L Clone
    """

    def __init__(self):
        super().__init__()

        # ----------------------------------------
        #     modules, interfaces, parameters
        # ----------------------------------------
        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        class _IFS(Module.IFS()):
            PA = times(8, ElectricLogic)
            PB = times(8, ElectricLogic)
            PD = times(8, ElectricLogic)
            usb = USB2_0()
            i2c = I2C()

            avcc = ElectricPower()
            vcc = ElectricPower()

            rdy = times(2, ElectricLogic)
            ctl = times(3, ElectricLogic)
            reset = ElectricLogic()
            wakeup = ElectricLogic()

            ifclk = ElectricLogic()
            clkout = ElectricLogic()
            xtalin = Electrical()
            xtalout = Electrical()

        self.IFs = _IFS(self)

        # ----------------------------------------
        #                traits
        # ----------------------------------------
        self.add_trait(has_designator_prefix_defined("U"))
        self.add_trait(
            has_datasheet_defined(
                "https://corebai.com/Data/corebai/upload/file/20240201/CBM9002A.pdf"
            )
        )
        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )

        # ----------------------------------------
        #                aliases
        # ----------------------------------------

        # ----------------------------------------
        #                connections
        # ----------------------------------------
        self.IFs.avcc.get_trait(can_be_decoupled).decouple()  # TODO: decouple all pins
        self.IFs.vcc.get_trait(can_be_decoupled).decouple()  # TODO: decouple all pins

        # ----------------------------------------
        #               Parameters
        # ----------------------------------------
