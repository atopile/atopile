# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import once


class MultiSPI(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    clock = F.ElectricLogic.MakeChild()
    chip_select = F.ElectricLogic.MakeChild()
    # Note: data lines are created dynamically in factory() with names data[0], data[1]

    # Mark base class as abstract - must use MakeChild with data_lane_count parameter
    is_abstract = fabll.Traits.MakeEdge(fabll.is_abstract.MakeChild()).put_on_type()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    @classmethod
    @once
    def factory(cls, data_lane_count: int) -> type[Self]:
        """
        Create a concrete MultiSPI type with the specified number of data lanes.

        This creates:
        1. A PointerSequence named `data` for for-loop iteration in ato
        2. ElectricLogic children named `data[0]`, `data[1]`, etc.
           for direct indexed access
        3. MakeLink edges from the PointerSequence to each data element
        """
        if data_lane_count <= 0:
            raise ValueError("At least one data lane is required")

        ConcreteMultiSPI = fabll.Node._copy_type(
            cls, name=f"MultiSPI<data_lane_count={data_lane_count}>"
        )

        # 1. Create the PointerSequence for for-loop iteration (replaces data_)
        data_seq = F.Collections.PointerSequence.MakeChild()
        ConcreteMultiSPI._handle_cls_attr("data", data_seq)

        # 2. Create data line children with array-indexed names
        for i in range(data_lane_count):
            data_line = F.ElectricLogic.MakeChild()
            ConcreteMultiSPI._handle_cls_attr(f"data[{i}]", data_line)

            # Add net name suggestion trait
            data_line.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name=f"DATA_{i}",
                        level=F.has_net_name_suggestion.Level.SUGGESTED,
                    ),
                    owner=[data_line],
                )
            )

            # 3. Create link from PointerSequence to element for iteration
            edge = F.Collections.PointerSequence.MakeEdge(
                seq_ref=[data_seq],
                elem_ref=[data_line],
                index=i,
            )
            ConcreteMultiSPI._handle_cls_attr(f"_data_link_{i}", edge)

        return ConcreteMultiSPI

    @classmethod
    def MakeChild(cls, data_lane_count: int) -> fabll._ChildField[Self]:
        """
        Create a MultiSPI child field with the specified number of data lanes.

        Uses factory() to create a concrete type with data lines as proper
        indexed children accessible as data[0], data[1], etc.
        """
        ConcreteMultiSPI = cls.factory(data_lane_count)
        return fabll._ChildField(ConcreteMultiSPI)

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
            qspi = new MultiSPI<data_lane_count=4>

            # Connect the buses
            mcu_spi ~ qspi

            # Access individual data lines
            qspi.data[0].line ~ some_pin
            qspi.data[1].line ~ another_pin
            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )


def test_multispi_factory():
    """Test MultiSPI factory creates correct number of data lanes."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create unique App type per test run
    AppType = fabll.Node._copy_type(fabll.Node, name="App_multispi_factory")
    AppType._handle_cls_attr("multispi", MultiSPI.MakeChild(data_lane_count=4))

    app = AppType.bind_typegraph(tg=tg).create_instance(g=g)
    multispi = app.multispi.get()

    # data is a PointerSequence pointing to ElectricLogic children
    data_lines = multispi.data.get().as_list()
    assert len(data_lines) == 4

    for index, data_node in enumerate(data_lines):
        data_line = F.ElectricLogic.bind_instance(data_node.instance)
        suggested_name_trait = data_line.try_get_trait(F.has_net_name_suggestion)
        assert suggested_name_trait is not None
        assert suggested_name_trait.name == f"DATA_{index}"
