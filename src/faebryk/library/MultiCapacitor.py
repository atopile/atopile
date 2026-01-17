# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Self

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.util import once

logger = logging.getLogger(__name__)


class MultiCapacitor(fabll.Node):
    """
    MultiCapacitor acts as a single capacitor but contains multiple in parallel.

    All internal capacitors are connected in parallel between unnamed[0] and unnamed[1].
    Supports bridge-connect syntax: `power.hv ~> multicap ~> power.lv`

    Example usage in ato:
        multicapacitor = new MultiCapacitor<count=4>
        for c in multicapacitor.capacitors:
            c.capacitance = 100nF +/- 10%
            c.package = "0402"

        electrical1 ~> multicapacitor ~> electrical2
    """

    # Mark base class as abstract - must use MakeChild with count parameter
    is_abstract = fabll.Traits.MakeEdge(fabll.is_abstract.MakeChild()).put_on_type()

    # Interfaces for bridge connection (same as Capacitor)
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # Bridge-connect support: unnamed[0] ~> multicap ~> unnamed[1]
    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeChild(["unnamed[0]"], ["unnamed[1]"])
    )

    @classmethod
    @once
    def factory(cls, count: int) -> type[Self]:
        """
        Create a concrete MultiCapacitor type with a fixed number of capacitors.

        This creates:
        1. A PointerSequence named `capacitors` for for-loop iteration in ato
        2. Capacitor children named `capacitors[0]`, `capacitors[1]`, etc.
           for direct indexed access
        3. MakeLink edges from the PointerSequence to each Capacitor element
        4. Connection edges from each capacitor's terminals to unnamed[0]/[1]
        """
        if count <= 0:
            raise ValueError("At least one capacitor is required")

        ConcreteMultiCapacitor = fabll.Node._copy_type(
            cls, name=f"MultiCapacitor<count={count}>"
        )

        # 1. Create the PointerSequence for for-loop iteration
        capacitors_seq = F.Collections.PointerSequence.MakeChild()
        ConcreteMultiCapacitor._handle_cls_attr("capacitors", capacitors_seq)

        # 2. Create Capacitor children with indexed names and connect them
        for i in range(count):
            cap = F.Capacitor.MakeChild()
            ConcreteMultiCapacitor._handle_cls_attr(f"capacitors[{i}]", cap)

            # 3. Create MakeLink edge from PointerSequence to element
            # This allows iteration: for c in multicap.capacitors
            edge = F.Collections.PointerSequence.MakeEdge(
                seq_ref=[capacitors_seq],
                elem_ref=[cap],
                index=i,
            )
            ConcreteMultiCapacitor._handle_cls_attr(f"_capacitor_link_{i}", edge)

            # 4. Connect capacitor terminals to MultiCapacitor's unnamed interfaces
            # capacitor.unnamed[0] ~ self.unnamed[0] (parallel connection)
            conn_0 = fabll.is_interface.MakeConnectionEdge(
                [cap, F.Capacitor.unnamed[0]], [cls.unnamed[0]]
            )
            ConcreteMultiCapacitor._handle_cls_attr(f"_cap_{i}_conn_0", conn_0)

            # capacitor.unnamed[1] ~ self.unnamed[1] (parallel connection)
            conn_1 = fabll.is_interface.MakeConnectionEdge(
                [cap, F.Capacitor.unnamed[1]], [cls.unnamed[1]]
            )
            ConcreteMultiCapacitor._handle_cls_attr(f"_cap_{i}_conn_1", conn_1)

        return ConcreteMultiCapacitor

    @classmethod
    def MakeChild(cls, count: int) -> fabll._ChildField[Self]:
        """
        Create a MultiCapacitor child field with the specified number of capacitors.

        Uses factory() to create a concrete type with capacitors as a proper
        list of Capacitor children.
        """
        logger.debug(f"MultiCapacitor.MakeChild called: count={count}")

        # Use factory to create a concrete type with the right number of capacitors
        ConcreteMultiCapacitor = cls.factory(count)
        out = fabll._ChildField(ConcreteMultiCapacitor)

        return out

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import MultiCapacitor

        multicapacitor = new MultiCapacitor<count=4>
        for c in multicapacitor.capacitors:
            c.capacitance = 100nF +/- 10%
            c.package = "0402"

        electrical1 ~ multicapacitor.unnamed[0]
        electrical2 ~ multicapacitor.unnamed[1]
        # OR using bridge-connect
        electrical1 ~> multicapacitor ~> electrical2
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )


# --------------------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("count", [1, 2, 4, 8])
def test_multicapacitor_factory(count: int):
    """Test MultiCapacitor factory creates correct number of capacitors."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create unique App type per test run
    AppType = fabll.Node._copy_type(fabll.Node, name=f"App_factory_{count}")

    # Dynamically add the multicap with the correct count
    AppType._handle_cls_attr("multicap", MultiCapacitor.MakeChild(count=count))

    app = AppType.bind_typegraph(tg=tg).create_instance(g=g)
    multicap = app.multicap.get()

    # capacitors is a PointerSequence pointing to Capacitor children
    caps = multicap.capacitors.get().as_list()
    assert len(caps) == count
    for cap in caps:
        assert cap.try_cast(F.Capacitor) is not None


def test_multicapacitor_make_child():
    """Test basic MultiCapacitor instantiation via MakeChild."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App_make_child(fabll.Node):
        multicap = MultiCapacitor.MakeChild(count=3)

    app = App_make_child.bind_typegraph(tg=tg).create_instance(g=g)

    # capacitors is a PointerSequence pointing to Capacitor children
    caps = app.multicap.get().capacitors.get().as_list()
    assert len(caps) == 3
    for cap in caps:
        assert cap.try_cast(F.Capacitor) is not None


def test_multicapacitor_indexed_access():
    """Test that capacitors can be accessed by index."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App_indexed_access(fabll.Node):
        multicap = MultiCapacitor.MakeChild(count=2)

    app = App_indexed_access.bind_typegraph(tg=tg).create_instance(g=g)
    multicap = app.multicap.get()

    # Access via PointerSequence as_list
    caps = multicap.capacitors.get().as_list()
    assert len(caps) == 2

    # Each should be a Capacitor
    cap0 = F.Capacitor.bind_instance(caps[0].instance)
    cap1 = F.Capacitor.bind_instance(caps[1].instance)
    assert cap0 is not None
    assert cap1 is not None


def test_multicapacitor_parallel_connection():
    """Test that all capacitors are connected in parallel to unnamed interfaces."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App_parallel_connection(fabll.Node):
        multicap = MultiCapacitor.MakeChild(count=3)

    app = App_parallel_connection.bind_typegraph(tg=tg).create_instance(g=g)
    multicap = app.multicap.get()

    # Get the unnamed interfaces
    unnamed_0 = multicap.unnamed[0].get()
    unnamed_1 = multicap.unnamed[1].get()

    # Each capacitor should be connected to both unnamed interfaces
    caps = multicap.capacitors.get().as_list()
    for cap_node in caps:
        cap = F.Capacitor.bind_instance(cap_node.instance)
        # Check that capacitor's unnamed[0] is connected to multicap's unnamed[0]
        assert cap.unnamed[0].get()._is_interface.get().is_connected_to(unnamed_0)
        # Check that capacitor's unnamed[1] is connected to multicap's unnamed[1]
        assert cap.unnamed[1].get()._is_interface.get().is_connected_to(unnamed_1)


def test_multicapacitor_has_bridge_trait():
    """Test that MultiCapacitor has the can_bridge trait for ~> syntax."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App_bridge_trait(fabll.Node):
        multicap = MultiCapacitor.MakeChild(count=2)

    app = App_bridge_trait.bind_typegraph(tg=tg).create_instance(g=g)
    multicap = app.multicap.get()

    # Should have the can_bridge trait
    assert multicap.has_trait(F.can_bridge)
    bridge_trait = multicap.get_trait(F.can_bridge)

    # Bridge should connect unnamed[0] to unnamed[1]
    bridge_in = bridge_trait.get_in()
    bridge_out = bridge_trait.get_out()

    # Cast bridge_in/out to Electrical to get _is_interface
    bridge_in_electrical = F.Electrical.bind_instance(bridge_in.instance)
    bridge_out_electrical = F.Electrical.bind_instance(bridge_out.instance)

    assert bridge_in_electrical._is_interface.get().is_connected_to(
        multicap.unnamed[0].get()
    )
    assert bridge_out_electrical._is_interface.get().is_connected_to(
        multicap.unnamed[1].get()
    )
