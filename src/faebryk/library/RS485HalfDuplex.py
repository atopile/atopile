# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class RS485HalfDuplex(ModuleInterface):
    """
    Half-duplex RS485 interface
    A = p
    B = n
    """

    diff_pair: F.DifferentialPair

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.diff_pair.p.line.add(
            F.has_net_name("A", level=F.has_net_name.Level.SUGGESTED)
        )
        self.diff_pair.n.line.add(
            F.has_net_name("B", level=F.has_net_name.Level.SUGGESTED)
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import RS485HalfDuplex

        rs485_bus = new RS485HalfDuplex

        # Connect to rs485 transceiver
        rs485_transceiver.rs485 ~ rs485_bus

        # Connect to rs485 connector
        rs485_connector.rs485 ~ rs485_bus
        """,
        language=F.has_usage_example.Language.ato,
    )
