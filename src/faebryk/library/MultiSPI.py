# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
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
            data_line.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name=f"DATA_{i}",
                        level=F.has_net_name_suggestion.Level.SUGGESTED,
                    ),
                    owner=[data_line],
                )
            )
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge([out, cls.data_], [data_line])
            )
        return out

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="CLOCK", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[clock],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="CHIP_SELECT", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[chip_select],
        ),
    ]

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


def test_multisp():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        multisp = MultiSPI.MakeChild(data_lane_count=4)

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    assert len(app.multisp.get().data) == 4
    for index, data_line in enumerate(app.multisp.get().data):
        suggested_name_trait = data_line.try_get_trait(F.has_net_name_suggestion)
        assert suggested_name_trait is not None
        assert suggested_name_trait.name == f"DATA_{index}"
