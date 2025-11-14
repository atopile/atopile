# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class MultiSPI(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    clock = F.ElectricLogic.MakeChild()
    chip_select = F.ElectricLogic.MakeChild()
    data_lanes = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Natural)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    # self.clock.line.add(
    #     F.has_net_name("clock", level=F.has_net_name.Level.SUGGESTED)
    # )
    # self.chip_select.line.add(
    #     F.has_net_name("chip_select", level=F.has_net_name.Level.SUGGESTED)
    # )
    # for i, line in enumerate(self.data):
    #     line.add(F.has_net_name(f"data_{i}", level=F.has_net_name.Level.SUGGESTED))

    @classmethod
    def MakeChild(cls, data_lane_count: int):
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Numbers.MakeChild_ConstrainToLiteral(
                [out, cls.data_lanes], data_lane_count
            )
        )
        return out

    # ----------------------------------------
    #              usage example
    # ----------------------------------------
    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
    )
