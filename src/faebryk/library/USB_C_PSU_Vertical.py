# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.core.util import connect_all_interfaces
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Constant import Constant
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.Fuse import Fuse
from faebryk.library.Resistor import Resistor
from faebryk.library.USB2_0 import USB2_0
from faebryk.library.USB2_0_ESD_Protection import USB2_0_ESD_Protection
from faebryk.library.USB_Type_C_Receptacle_14_pin_Vertical import (
    USB_Type_C_Receptacle_14_pin_Vertical,
)
from faebryk.libs.units import M, k
from faebryk.libs.util import times


class USB_C_PSU_Vertical(Module):
    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            power_out = ElectricPower()
            usb = USB2_0()

        self.IFs = _IFs(self)

        # components
        class _NODEs(Module.NODES()):
            usb_connector = (
                USB_Type_C_Receptacle_14_pin_Vertical()
            )  # TODO: make generic
            configuration_resistors = times(2, Resistor)
            gnd_resistor = Resistor()
            gnd_capacitor = Capacitor()
            esd = USB2_0_ESD_Protection()
            fuse = Fuse()

        self.NODEs = _NODEs(self)

        self.NODEs.gnd_capacitor.PARAMs.capacitance.merge(100e-9)
        self.NODEs.gnd_capacitor.PARAMs.rated_voltage.merge(16)
        self.NODEs.gnd_resistor.PARAMs.resistance.merge(1 * M)
        for res in self.NODEs.configuration_resistors:
            res.PARAMs.resistance.merge(5.1 * k)
        self.NODEs.fuse.PARAMs.fuse_type.merge(Fuse.FuseType.RESETTABLE)
        self.NODEs.fuse.PARAMs.trip_current.merge(Constant(1))

        # alliases
        vcon = self.NODEs.usb_connector.IFs.vbus
        vusb = self.IFs.usb.IFs.buspower
        v5 = self.IFs.power_out
        gnd = v5.IFs.lv

        vcon.IFs.hv.connect_via(self.NODEs.fuse, v5.IFs.hv)
        vcon.IFs.lv.connect(gnd)
        vusb.IFs.lv.connect(gnd)
        v5.connect(self.NODEs.esd.IFs.usb[0].IFs.buspower)

        # connect usb data
        connect_all_interfaces(
            [
                self.NODEs.usb_connector.IFs.usb.IFs.d,
                self.IFs.usb.IFs.d,
                self.NODEs.esd.IFs.usb[0].IFs.d,
            ]
        )

        # configure as ufp with 5V@max3A
        self.NODEs.usb_connector.IFs.cc1.connect_via(
            self.NODEs.configuration_resistors[0], gnd
        )
        self.NODEs.usb_connector.IFs.cc2.connect_via(
            self.NODEs.configuration_resistors[1], gnd
        )

        # EMI shielding
        self.NODEs.usb_connector.IFs.shield.connect_via(self.NODEs.gnd_resistor, gnd)
        self.NODEs.usb_connector.IFs.shield.connect_via(self.NODEs.gnd_capacitor, gnd)
