# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class Powered_Relay(Module):
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
        from faebryk.core.util import connect_module_mifs_by_name

        connect_module_mifs_by_name(self, self.relay, allow_partial=True)

        self.relay_driver.power_in.connect(self.power)
        self.relay_driver.logic_in.connect(self.enable)
        self.relay_driver.switched_power_out.lv.connect(self.relay.coil_n)
        self.relay_driver.switched_power_out.hv.connect(self.relay.coil_p)

        self.relay.coil_n.connect_via(self.flyback_diode, self.relay.coil_p)
        self.indicator.power.connect(self.relay_driver.switched_power_out)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        )
