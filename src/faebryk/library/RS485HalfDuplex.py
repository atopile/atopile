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

    baudrate = F.Parameters.NumericParameter.MakeChild(unit=F.Units.BitsPerSecond)

    impedance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)
    impedance_constraint = F.Literals.Numbers.MakeChild_ConstrainToLiteral(
        [impedance], min=110.0, max=130.0, unit=F.Units.Ohm
    )

    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.diff_pair.get().p.get(), trait=F.has_net_name_affix
        ).setup(suffix="_A")

        fabll.Traits.create_and_add_instance_to(
            node=self.diff_pair.get().n.get(), trait=F.has_net_name_affix
        ).setup(suffix="_B")

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
