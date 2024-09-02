# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class USB2514B(Module):
    class InterfaceConfiguration(Enum):
        DEFAULT = auto()
        SMBUS = auto()
        BUS_POWERED = auto()
        EEPROM = auto()

    class NonRemovablePortConfiguration(Enum):
        ALL_PORTS_REMOVABLE = auto()
        PORT_1_NOT_REMOVABLE = auto()
        PORT_1_2_NOT_REMOVABLE = auto()
        PORT_1_2_3_NOT_REMOVABLE = auto()

    VDD33: F.ElectricPower
    VDDA33: F.ElectricPower

    PLLFILT: F.ElectricPower
    CRFILT: F.ElectricPower

    VBUS_DET: F.Electrical

    usb_downstream = L.list_field(4, F.DifferentialPair)
    usb_upstream = F.DifferentialPair

    XTALIN: F.Electrical
    XTALOUT: F.Electrical

    TEST: F.Electrical
    SUSP_IND: F.ElectricLogic
    RESET_N: F.Electrical
    RBIAS: F.Electrical
    NON_REM = L.list_field(2, F.ElectricLogic)
    LOCAL_PWR: F.Electrical
    CLKIN: F.Electrical
    CFG_SEL = L.list_field(2, F.ElectricLogic)

    HS_IND: F.ElectricLogic

    PRTPWR = L.list_field(4, F.ElectricLogic)
    PRT_DIS_P = L.list_field(4, F.ElectricLogic)
    PRT_DIS_M = L.list_field(4, F.ElectricLogic)
    OCS_N = L.list_field(4, F.ElectricLogic)
    BC_EN = L.list_field(4, F.ElectricLogic)

    i2c: F.I2C
    gnd: F.Electrical

    interface_configuration: F.TBD[InterfaceConfiguration]
    non_removable_port_configuration: F.TBD[NonRemovablePortConfiguration]

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")

    def __preinit__(self):
        if self.interface_configuration == USB2514B.InterfaceConfiguration.DEFAULT:
            self.CFG_SEL[0].pulled.pull(up=False)
            self.CFG_SEL[1].pulled.pull(up=False)
        elif self.interface_configuration == USB2514B.InterfaceConfiguration.SMBUS:
            self.CFG_SEL[0].pulled.pull(up=True)
            self.CFG_SEL[1].pulled.pull(up=False)
        elif (
            self.interface_configuration == USB2514B.InterfaceConfiguration.BUS_POWERED
        ):
            self.CFG_SEL[0].pulled.pull(up=False)
            self.CFG_SEL[1].pulled.pull(up=True)
        elif self.interface_configuration == USB2514B.InterfaceConfiguration.EEPROM:
            self.CFG_SEL[0].pulled.pull(up=True)
            self.CFG_SEL[1].pulled.pull(up=True)

        # Add decoupling capacitors to power pins and connect all lv to gnd
        # TODO: decouple with 1.0uF and 0.1uF and maybe 4.7uF
        for g in self.get_children(direct_only=True, types=F.ElectricPower):
            g.decoupled.decouple()
            g.lv.connect(self.gnd)

        x = self

        x.CFG_SEL[0].connect(x.i2c.scl)
        x.CFG_SEL[1].connect(x.HS_IND)
        x.NON_REM[0].connect(x.SUSP_IND)
        x.NON_REM[1].connect(x.i2c.sda)

        x.RESET_N.connect(self.gnd)

        self.PLLFILT.voltage.merge(1.8 * P.V)
        self.CRFILT.voltage.merge(1.8 * P.V)

        if (
            self.non_removable_port_configuration
            == USB2514B.NonRemovablePortConfiguration.ALL_PORTS_REMOVABLE
        ):
            self.NON_REM[0].get_trait(F.ElectricLogic.can_be_pulled).pull(up=False)
            self.NON_REM[1].get_trait(F.ElectricLogic.can_be_pulled).pull(up=False)
        elif (
            self.non_removable_port_configuration
            == USB2514B.NonRemovablePortConfiguration.PORT_1_NOT_REMOVABLE
        ):
            self.NON_REM[0].get_trait(F.ElectricLogic.can_be_pulled).pull(up=True)
            self.NON_REM[1].get_trait(F.ElectricLogic.can_be_pulled).pull(up=False)
        elif (
            self.non_removable_port_configuration
            == USB2514B.NonRemovablePortConfiguration.PORT_1_2_NOT_REMOVABLE
        ):
            self.NON_REM[0].get_trait(F.ElectricLogic.can_be_pulled).pull(up=False)
            self.NON_REM[1].get_trait(F.ElectricLogic.can_be_pulled).pull(up=True)
        elif (
            self.non_removable_port_configuration
            == USB2514B.NonRemovablePortConfiguration.PORT_1_2_3_NOT_REMOVABLE
        ):
            self.NON_REM[0].get_trait(F.ElectricLogic.can_be_pulled).pull(up=True)
            self.NON_REM[1].get_trait(F.ElectricLogic.can_be_pulled).pull(up=True)

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB251xB-xBi-Data-Sheet-DS00001692.pdf"
    )
