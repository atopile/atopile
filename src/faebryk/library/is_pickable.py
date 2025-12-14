# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_pickable(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_pickable_node(self) -> fabll.Node:
        """
        Gets the node associate with the is_pickable trait.
        This is a little weird as is_pickable_by_type etc
        have a trait instance of is_pickable, not the node itself.
        """
        owner_trait = fabll.Traits(self).get_obj_raw()
        pickable_node = fabll.Traits(owner_trait).get_obj_raw()
        return pickable_node


def test_get_pickable_node():
    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.graph as graph
    from faebryk.library.is_pickable_by_type import is_pickable_by_type
    from faebryk.library.Resistor import Resistor

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        r1 = Resistor.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    # Get pickable trait instance of r1
    pickable_trait = app.r1.get().get_trait(is_pickable_by_type).get_trait(is_pickable)

    assert pickable_trait is not None
    pickable_node = pickable_trait.get_pickable_node()
    assert pickable_node.get_full_name() == app.r1.get().get_full_name()
