# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L


class NFET(F.MOSFET):
    def __preinit__(self) -> None:
        self.channel_type.alias_is(F.MOSFET.ChannelType.N_CHANNEL)

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import NFET, ElectricLogic, ElectricPower

        nfet = new NFET
        nfet.gate_source_threshold_voltage = 2.5V +/- 10%
        nfet.max_drain_source_voltage = 60V
        nfet.max_continuous_drain_current = 30A
        nfet.on_resistance = 5mohm +/- 20%
        nfet.package = "SOT-23"

        # Use as low-side switch
        gate_control = new ElectricLogic
        power_supply = new ElectricPower
        load = new ElectricLogic

        nfet.gate ~ gate_control.line
        nfet.source ~ power_supply.lv  # Connect to ground for low-side
        nfet.drain ~ load.line

        # When gate_control is HIGH, NFET conducts (load connected to ground)
        """,
        language=F.has_usage_example.Language.ato,
    )
