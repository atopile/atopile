# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import times


class MultiSPI(fabll.Node):
    def __init__(self, data_lane_count: int) -> None:
        super().__init__()
        self._data_lane_count = data_lane_count

    clock = F.ElectricLogic.MakeChild()
    chip_select = F.ElectricLogic.MakeChild()
    data_lanes = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Natural)

    def data(self):
        return times(self._data_lane_count, F.ElectricLogic)

    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.clock.line.add(
            F.has_net_name("clock", level=F.has_net_name.Level.SUGGESTED)
        )
        self.chip_select.line.add(
            F.has_net_name("chip_select", level=F.has_net_name.Level.SUGGESTED)
        )
        for i, line in enumerate(self.data):
            line.add(F.has_net_name(f"data_{i}", level=F.has_net_name.Level.SUGGESTED))

    @classmethod
    def MakeChild(cls, data_lane_count: int):
        out = fabll.ChildField(cls)
        out.add_dependant(
            fabll.ExpressionAliasIs.MakeChild_ToLiteral(
                [out, cls.data_lanes], data_lane_count
            )
        )
        return out

    # ----------------------------------------
    #              usage example
    # ----------------------------------------
    usage_example = F.has_usage_example.MakeChild(
        example="""
        import MultiSPI, SPI

        # Microcontroller SPI peripheral
        mcu_spi = new SPI

        # Quad-SPI flash interface (4 data lanes)
        qspi = new MultiSPI<int_=4>

        # Connect the buses
        mcu_spi ~ qspi
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
