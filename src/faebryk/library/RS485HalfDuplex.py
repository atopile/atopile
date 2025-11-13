# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class RS485HalfDuplex(fabll.Node):
    """
    RS485 half-duplex interface.
    A = p
    B = n
    """

    diff_pair = F.DifferentialPair.MakeChild()

    baudrate = F.Parameters.NumericParameter.MakeChild(unit=F.Units.BitPerSecond)

    impedance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)
    impedance_constraint = F.Literals.Numbers.MakeChild_ConstrainToLiteral(
        [impedance], 120.0
    )

    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    # TODO: add trait
    # self.diff_pair.p.line.add(F.has_net_name_affix.suffix("_A"))
    # self.diff_pair.n.line.add(F.has_net_name_affix.suffix("_B"))

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
            import RS485HalfDuplex

            rs485_bus = new RS485HalfDuplex

            # Connect to rs485 transceiver
            rs485_transceiver.rs485 ~ rs485_bus

            # Connect to connector pins
            rs485_connector.1 ~ rs485_bus.diff_pair.p.line
            rs485_connector.2 ~ rs485_bus.diff_pair.n.line
            rs485_connector.3 ~ rs485_bus.reference_shim.lv
            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
