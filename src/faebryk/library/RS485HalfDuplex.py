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

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricSignal.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.diff_pair.p.line.add(F.has_net_name_affix.suffix("_A"))
        self.diff_pair.n.line.add(F.has_net_name_affix.suffix("_B"))

    usage_example = L.f_field(F.has_usage_example)(
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
    )
