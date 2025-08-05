# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L


class PFET(F.MOSFET):
    def __preinit__(self) -> None:
        self.channel_type.alias_is(F.MOSFET.ChannelType.P_CHANNEL)

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import PFET, ElectricLogic, ElectricPower

        pfet = new PFET
        pfet.gate_source_threshold_voltage = -2.5V +/- 10%
        pfet.max_drain_source_voltage = 30V
        pfet.max_continuous_drain_current = 20A
        pfet.on_resistance = 10mohm +/- 20%
        pfet.package = "SOT-23"

        # Use as high-side switch
        gate_control = new ElectricLogic
        power_supply = new ElectricPower
        load = new ElectricLogic

        pfet.gate ~ gate_control.line
        pfet.source ~ power_supply.hv  # Connect to positive supply for high-side
        pfet.drain ~ load.line

        # When gate_control is LOW, PFET conducts (load connected to Vcc)
        # Note: For P-channel, gate needs to be pulled low to turn on
        """,
        language=F.has_usage_example.Language.ato,
    )
