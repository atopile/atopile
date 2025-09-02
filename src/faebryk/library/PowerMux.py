# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class PowerMux(Module):
    power_in = L.list_field(2, F.ElectricPower)
    power_out: F.ElectricPower
    select: F.ElectricSignal

    def __preinit__(self):
        # TODO: this will also connect the power_ins to each other
        # self.power_in[0].connect_shallow(self.power_out)
        # self.power_in[1].connect_shallow(self.power_out)
        ...

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import PowerMux, ElectricPower, ElectricSignal

        module UsageExample:
            # Two input power sources
            battery_power = new ElectricPower
            battery_power.voltage = 3.7V +/- 10%
            
            usb_power = new ElectricPower  
            usb_power.voltage = 5V +/- 5%
            
            # Output power
            system_power = new ElectricPower
            
            # Control signal
            select_signal = new ElectricSignal
            
            # Power multiplexer
            power_mux = new PowerMux
            power_mux.power_in[0] ~ battery_power
            power_mux.power_in[1] ~ usb_power
            power_mux.power_out ~ system_power
            power_mux.select ~ select_signal
        """,
        language=F.has_usage_example.Language.ato,
    )
