# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class Powered_Relay(Module):
    """
    A relay with MOSFET driver, flyback diode and LED indicator.
    """

    relay: F.Relay
    indicator: F.PoweredLED
    flyback_diode: F.Diode
    relay_driver = L.f_field(F.PowerSwitchMOSFET)(lowside=True, normally_closed=False)

    switch_a_nc: F.Electrical
    switch_a_common: F.Electrical
    switch_a_no: F.Electrical
    switch_b_no: F.Electrical
    switch_b_common: F.Electrical
    switch_b_nc: F.Electrical
    enable: F.ElectricLogic
    power: F.ElectricPower

    def __preinit__(self):
        self.connect_interfaces_by_name(self.relay, allow_partial=True)

        self.relay_driver.power_in.connect(self.power)
        self.relay_driver.logic_in.connect(self.enable)
        self.relay_driver.switched_power_out.connect(self.relay.coil_power)

        self.relay.coil_power.lv.connect_via(
            self.flyback_diode, self.relay.coil_power.hv
        )
        self.indicator.power.connect(self.relay_driver.switched_power_out)
