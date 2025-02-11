# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class WCHJiangsu_Qin_Heng_CH224K_ReferenceDesign(Module):
    """
    USB PD and Other Fast Charging Protocol Sink Controller Reference Design
    Design is ment for connecting to a female USB Type-C connector.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    controller: F.WCHJiangsu_Qin_Heng_CH224K

    vbus: F.ElectricPower
    usb_data: F.USB2_0_IF.Data
    cc = L.list_field(2, F.Electrical)
    vdd_resistor: F.Resistor

    power_good_indicator = L.f_field(F.LEDIndicator)(use_mosfet=False, active_low=True)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        self.controller.vbus_detect.set_weak(
            on=True, owner=self
        ).resistance.constrain_subset(L.Range.from_center_rel(10 * P.kohm, 0.01))
        self.controller.vbus_detect.reference.connect(self.vbus)

        self.controller.power.hv.connect_via(self.vdd_resistor, self.vbus.hv)
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)

        self.controller.cc1.line.connect(self.cc[0])
        self.controller.cc2.line.connect(self.cc[1])
        self.controller.usb.connect(self.usb_data)

        self.power_good_indicator.logic_in.connect(self.controller.power_good)
        self.power_good_indicator.logic_in.reference.connect(self.vbus)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.controller.power.decoupled.decouple(self).capacitance.constrain_subset(
            L.Range.from_center_rel(1 * P.uF, 0.1)
        )

        self.vdd_resistor.resistance.constrain_subset(
            L.Range.from_center_rel(1 * P.kohm, 0.01)
        )
