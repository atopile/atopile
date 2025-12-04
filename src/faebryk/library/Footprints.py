# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.library import _F as F


# TODO remove this
class Footprint(fabll.Node):
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    @staticmethod
    def get_footprint_of_parent(
        intf: fabll.Node,
    ) -> "tuple[fabll.Node, Footprint]":
        from faebryk.library._F import has_footprint

        parent, trait = intf.get_parent_with_trait(has_footprint)
        return parent, trait.get_footprint()

class is_footprint(fabll.Node):
    """
    Marker trait for nodes that a footprint.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

class can_attach_to_footprint(fabll.Node):
    """
    Marker trait for nodes that can be attached to a footprint.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

class has_associated_footprint(fabll.Node):
    """
    Link between a node and a footprint. Added during build process.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    def get_footprint(self):
        return is_footprint.bind_instance(EdgePointer.get_referenced_node_from_node(node=self.instance))

    def set_footprint(self, footprint: "is_footprint"):
        EdgePointer.point_to(bound_node=self.instance, target_node=footprint.instance.node(), order=None)

    @classmethod
    def MakeChild(cls, footprint: fabll._ChildField[is_footprint]) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(footprint)
        out.add_dependant(F.Collections.Pointer.MakeEdge([out], [footprint]))
        return out

def test_has_associated_footprint_typegraph(capsys):
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestFootprint(fabll.Node):
        _is_footprint = fabll.Traits.MakeEdge(is_footprint.MakeChild())

    class TestModule(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _has_associated_footprint = fabll.Traits.MakeEdge(has_associated_footprint.MakeChild(TestFootprint.MakeChild()))
        _can_attach_to_footprint = fabll.Traits.MakeEdge(can_attach_to_footprint.MakeChild())

    module_with_footprint = TestModule.bind_typegraph(tg=tg).create_instance(g=g)

    assert module_with_footprint.has_trait(has_associated_footprint)
    assert module_with_footprint.has_trait(can_attach_to_footprint)
    assert module_with_footprint.get_trait(has_associated_footprint).get_footprint().has_trait(is_footprint)

# def test_has_associated_footprint_instancegraph(capsys):
#     g = fabll.graph.GraphView.create()
#     tg = fbrk.TypeGraph.create(g=g)

#     has_associated_footprint = F.Footprints.has_associated_footprint.bind_typegraph(tg=tg).create_instance(g=g)
#     is_footprint = F.Footprints.is_footprint.bind_typegraph(tg=tg).create_instance(g=g)

#     has_associated_footprint.set_footprint(is_footprint)

#     assert has_associated_footprint.get_footprint()

#     with capsys.disabled():
#         print(fabll.graph.InstanceGraphFunctions.render(
#             has_associated_footprint.instance, show_traits=True, show_pointers=True))
