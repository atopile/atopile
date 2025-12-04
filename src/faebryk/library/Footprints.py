# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import TYPE_CHECKING, Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.library import _F as F

if TYPE_CHECKING:
    from faebryk.library.Net import Net


class is_footprint(fabll.Node):
    """
    Marker trait for nodes that a footprint.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()


class is_pad(fabll.Node):
    """
    A pad is a connection point on a footprint.
    It can be connected to a lead of a package.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    pad_name_ = F.Parameters.StringParameter.MakeChild()
    pad_number_ = F.Parameters.StringParameter.MakeChild()

    pad_ = F.Collections.Pointer.MakeChild()

    @property
    def pad(self) -> fabll.Node:
        return self.pad_.get().deref()

    @property
    def pad_name(self) -> str:
        return self.pad_name_.get().force_extract_literal().get_values()[0]

    @property
    def pad_number(self) -> str:
        return self.pad_number_.get().force_extract_literal().get_values()[0]

    @classmethod
    def MakeChild(cls, pad_name: str, pad_number: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.pad_name_], pad_name
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.pad_number_], pad_number
            )
        )
        return out

    def setup(self, pad_name: str, pad_number: str):
        self.pad_name_.get().alias_to_single(value=pad_name)
        self.pad_number_.get().alias_to_single(value=pad_number)
        return self


class has_associated_net(fabll.Node):
    """
    Link between pad-node and net. Added during build process.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    net_ptr_ = F.Collections.Pointer.MakeChild()

    @property
    def net(self) -> "Net":
        """Return the net associated with this node"""
        from faebryk.library.Net import Net

        return self.net_ptr_.get().deref().cast(Net)

    @classmethod
    def MakeChild(cls, net: "fabll._ChildField[Net]") -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(net)
        return out


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

    def get_footprint(self) -> is_footprint:
        return fabll.Node.bind_instance(EdgePointer.get_referenced_node_from_node(node=self.instance)).get_trait(is_footprint)

    def set_footprint(self, footprint: is_footprint):
        EdgePointer.point_to(bound_node=self.instance, target_node=fbrk.EdgeTrait.get_owner_node_of(bound_node=footprint.instance).node(), order=None)


class GenericPad(fabll.Node):
    """Generic pad"""

    is_pad = fabll.Traits.MakeEdge(is_pad.MakeChild(pad_name="", pad_number=""))

    @classmethod
    def MakeChild(cls, pad_name: str, pad_number: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(is_pad.MakeChild(pad_name, pad_number))
        return out

    def setup(self, pad_name: str, pad_number: str):
        self.is_pad.get().setup(pad_name, pad_number)


# TODO this is a placeholder for now, will be removed
class GenericFootprint(fabll.Node):
    """Generic footprint"""

    is_footprint = fabll.Traits.MakeEdge(is_footprint.MakeChild())

    pads_ = F.Collections.PointerSet.MakeChild()

    @classmethod
    def MakeChild(cls, pads: list[tuple[str, str]]) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        for number, name in pads:
            pad = GenericPad.MakeChild(name, number)
            out.add_dependant(pad)
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge([out, cls.pads_], [pad])
            )
        return out

    def setup(self, pads: list[tuple[str, str]]):
        """Setup the footprint with pads(number, name)"""
        for number, name in pads:
            pad = GenericPad.bind_typegraph(tg=self.tg).create_instance(
                g=self.instance.g()
            )
            pad.setup(name, number)
            self.pads_.get().append(pad)


# def test_has_associated_footprint():
#     g = fabll.graph.GraphView.create()
#     tg = fbrk.TypeGraph.create(g=g)

#     has_associated_footprint = has_associated_footprint.bind_typegraph(tg=tg).
#     .create_instance(g=g)
#     is_footprint = is_footprint.bind_typegraph(tg=tg).create_instance(g=g)

#     has_associated_footprint.set_footprint(is_footprint)

#     assert has_associated_footprint.get_footprint()

#     with capsys.disabled():
#         print(fabll.graph.InstanceGraphFunctions.render(
#             has_associated_footprint.instance, show_traits=True, show_pointers=True))


def test_has_associated_footprint(capsys):
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestFootprint(fabll.Node):
        _is_footprint = fabll.Traits.MakeEdge(is_footprint.MakeChild())

    class TestModule(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _has_associated_footprint = fabll.Traits.MakeEdge(has_associated_footprint.MakeChild())
        _can_attach_to_footprint = fabll.Traits.MakeEdge(can_attach_to_footprint.MakeChild())

    footprint_instance = TestFootprint.bind_typegraph(tg=tg).create_instance(g=g)
    module_with_footprint = TestModule.bind_typegraph(tg=tg).create_instance(g=g)

    module_with_footprint.get_trait(has_associated_footprint).set_footprint(footprint_instance._is_footprint.get())

    assert module_with_footprint.has_trait(has_associated_footprint)
    assert module_with_footprint.has_trait(can_attach_to_footprint)
    assert module_with_footprint.get_trait(has_associated_footprint).get_footprint().instance.node().is_same(other=footprint_instance._is_footprint.get().instance.node())

    with capsys.disabled():
        print(fabll.graph.InstanceGraphFunctions.render(
            module_with_footprint.instance, show_traits=True, show_pointers=True))