# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.DifferentialPair import DifferentialPair
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.I2C import I2C
from faebryk.library.TBD import TBD
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class USB2514B(Module):
    class InterfaceConfiguration(Enum):
        DEFAULT = auto()
        SMBUS = auto()
        BUS_POWERED = auto()
        EEPROM = auto()

    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            VDD33 = ElectricPower()
            VDDA33 = ElectricPower()

            PLLFILT = ElectricPower()
            CRFILT = ElectricPower()

            VBUS_DET = Electrical()

            usb_downstream = times(4, DifferentialPair)
            usb_upstream = DifferentialPair()

            XTALIN = Electrical()
            XTALOUT = Electrical()

            TEST = Electrical()
            SUSP_IND = ElectricLogic()
            RESET_N = Electrical()
            RBIAS = Electrical()
            NON_REM = times(2, ElectricLogic)
            LOCAL_PWR = Electrical()
            CLKIN = Electrical()
            CFG_SEL = times(2, ElectricLogic)

            HS_IND = ElectricLogic()

            PRTPWR = times(4, ElectricLogic)
            PRT_DIS_P = times(4, ElectricLogic)
            PRT_DIS_M = times(4, ElectricLogic)
            OCS_N = times(4, ElectricLogic)
            BC_EN = times(4, ElectricLogic)

            i2c = I2C()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            interface_configuration = TBD[USB2514B.InterfaceConfiguration]()

        self.PARAMs = _PARAMs(self)

        self.add_trait(has_designator_prefix_defined("U"))

        if (
            self.PARAMs.interface_configuration
            == USB2514B.InterfaceConfiguration.DEFAULT
        ):
            self.IFs.CFG_SEL[0].get_trait(ElectricLogic.can_be_pulled).pull(up=False)
            self.IFs.CFG_SEL[1].get_trait(ElectricLogic.can_be_pulled).pull(up=False)
        elif (
            self.PARAMs.interface_configuration == USB2514B.InterfaceConfiguration.SMBUS
        ):
            self.IFs.CFG_SEL[0].get_trait(ElectricLogic.can_be_pulled).pull(up=True)
            self.IFs.CFG_SEL[1].get_trait(ElectricLogic.can_be_pulled).pull(up=False)
        elif (
            self.PARAMs.interface_configuration
            == USB2514B.InterfaceConfiguration.BUS_POWERED
        ):
            self.IFs.CFG_SEL[0].get_trait(ElectricLogic.can_be_pulled).pull(up=False)
            self.IFs.CFG_SEL[1].get_trait(ElectricLogic.can_be_pulled).pull(up=True)
        elif (
            self.PARAMs.interface_configuration
            == USB2514B.InterfaceConfiguration.EEPROM
        ):
            self.IFs.CFG_SEL[0].get_trait(ElectricLogic.can_be_pulled).pull(up=True)
            self.IFs.CFG_SEL[1].get_trait(ElectricLogic.can_be_pulled).pull(up=True)

        gnd = Electrical()

        # Add decoupling capacitors to power pins and connect all lv to gnd
        # TODO: decouple with 1.0uF and 0.1uF and maybe 4.7uF
        for g in self.IFs.get_all():
            if isinstance(g, ElectricPower):
                g.get_trait(can_be_decoupled).decouple()
                g.IFs.lv.connect(gnd)

        x = self.IFs

        x.CFG_SEL[0].connect(x.i2c.IFs.scl)
        x.CFG_SEL[1].connect(x.HS_IND)
        x.NON_REM[0].connect(x.SUSP_IND)
        x.NON_REM[1].connect(x.i2c.IFs.sda)

        x.RESET_N.connect(gnd)

        self.add_trait(
            has_datasheet_defined(
                "https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/DataSheets/00001692C.pdf"
            )
        )
