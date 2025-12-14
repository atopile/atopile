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
    data_ = F.Collections.PointerSet.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    @property
    def data(self) -> list[F.ElectricLogic]:
        return [
            F.ElectricLogic.bind_instance(line.instance)
            for line in self.data_.get().as_list()
        ]

    @classmethod
    def MakeChild(cls, data_lane_count: int):
        out = fabll._ChildField(cls)
        for i in range(data_lane_count):
            data_line = F.ElectricLogic.MakeChild()
            out.add_dependant(data_line)
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge([out, cls.data_], [data_line])
            )
        return out

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.clock.get(), trait=F.has_net_name_suggestion
        ).setup(name="CLOCK", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.chip_select.get(), trait=F.has_net_name_suggestion
        ).setup(name="CHIP_SELECT", level=F.has_net_name_suggestion.Level.SUGGESTED)
        for i, line in enumerate(self.data_.get().as_list()):
            fabll.Traits.create_and_add_instance_to(
                node=line, trait=F.has_net_name_suggestion
            ).setup(name=f"DATA_{i}", level=F.has_net_name_suggestion.Level.SUGGESTED)

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
