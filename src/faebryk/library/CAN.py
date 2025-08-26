# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P


class CAN(ModuleInterface):
    """
    CAN bus interface
    """

    diff_pair: F.DifferentialPair

    speed = L.p_field(units=P.bps)

    def __preinit__(self) -> None:
        self.speed.add(F.is_bus_parameter())

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.diff_pair.p.line.add(
            F.has_net_name("CAN_H", level=F.has_net_name.Level.SUGGESTED)
        )
        self.diff_pair.n.line.add(
            F.has_net_name("CAN_L", level=F.has_net_name.Level.SUGGESTED)
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import CAN, ElectricPower, Resistor

        can_bus = new CAN
        can_bus.speed = 250kbps  # Common CAN speeds: 125k, 250k, 500k, 1Mbps
        can_bus.diff_pair.impedance = 120ohm +/- 5%

        # Connect power reference for logic levels
        power_5v = new ElectricPower
        assert power_5v.voltage within 5V +/- 5%
        can_bus.diff_pair.p.reference ~ power_5v
        can_bus.diff_pair.n.reference ~ power_5v

        # Connect to CAN transceiver
        can_transceiver.can_bus ~ can_bus

        # Connect to microcontroller CAN peripheral
        microcontroller.can ~ can_transceiver.mcu_interface

        # CAN termination resistors (120 ohm at each end of bus)
        termination_resistor = new Resistor
        termination_resistor.resistance = 120ohm +/- 1%
        can_bus.diff_pair.p.line ~> termination_resistor ~> can_bus.diff_pair.n.line

        # Common applications: automotive, industrial automation, IoT
        """,
        language=F.has_usage_example.Language.ato,
    )
