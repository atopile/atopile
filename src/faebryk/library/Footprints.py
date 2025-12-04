# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.library import _F as F


class Footprint(fabll.Node):
    """Genreic footprint"""

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
    A node that is a footprint.
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

    footprint_ptr_ = F.Collections.Pointer.MakeChild()

    @property
    def footprint(self):
        """Return the footprint associated with this node"""
        return self.footprint_ptr_.get().deref()

    @classmethod
    def MakeChild(
        cls, footprint: fabll._ChildField[fabll.Node]
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(footprint)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.footprint_ptr_],
                [footprint],
            )
        )
        return out

    def setup(self, footprint: fabll.Node) -> Self:
        self.footprint_ptr_.get().point(footprint)
        return self


# def test_has_associated_footprint():
#     g = fabll.graph.GraphView.create()
#     tg = fbrk.TypeGraph.create(g=g)

#     class TestFootprint(fabll.Node):
#         _is_footprint = fabll.Traits.MakeEdge(is_footprint.MakeChild())

#     class TestNode(fabll.Node):
#         _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
#         _has_associated_footprint = fabll.Traits.MakeEdge(
#             has_associated_footprint.MakeChild(TestFootprint.MakeChild())
#         )
#         _can_attach_to_footprint = fabll.Traits.MakeEdge(
#             can_attach_to_footprint.MakeChild()
#         )

#     node_with_fp = TestNode.bind_typegraph(tg=tg).create_instance(g=g)

#     assert node_with_fp.has_trait(has_associated_footprint)
#     assert node_with_fp.has_trait(can_attach_to_footprint)

#     fp = node_with_fp.get_trait(has_associated_footprint).footprint
#     assert fp.has_trait(is_footprint)
