# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class CAN(fabll.Node):
    """
    CAN bus interface
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    diff_pair = F.DifferentialPair.MakeChild()

    baudrate = F.Parameters.NumericParameter.MakeChild(unit=F.Units.BitsPerSecond)
    # TODO constrain CAN baudrate between 10kbps to 1Mbps
    # F.Expressions.Is.MakeChild_Constrain()

    impedance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)
    impedance_constraint = F.Literals.Numbers.MakeChild_ConstrainToLiteral(
        [impedance], min=120.0, max=120.0, unit=F.Units.Ohm
    )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="CAN_H", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[diff_pair, "p"],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="CAN_L", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[diff_pair, "n"],
        ),
    ]

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
        ).put_on_type()
    )
