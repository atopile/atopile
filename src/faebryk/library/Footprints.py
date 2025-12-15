# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.core.graph_render import GraphRenderer
from faebryk.library import _F as F

logger = logging.getLogger(__name__)


class FootprintError(Exception):
    pass


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


class is_footprint(fabll.Node):
    """
    Mark node as a footprint.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    def get_pads(self) -> list[is_pad]:
        parent = fabll.Traits(self).get_obj_raw()
        pads_nodes = parent.get_children(
            direct_only=False, types=fabll.Node, required_trait=is_pad
        )
        return [p.get_trait(is_pad) for p in pads_nodes]


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
    footprint_ = F.Collections.Pointer.MakeChild()

    def get_footprint(self) -> is_footprint:
        return self.footprint_.get().deref().cast(is_footprint)

    def setup(self, footprint: is_footprint):
        self.footprint_.get().point(footprint)
        return self

    def setup_from_pads_and_leads(
        self,
        component_node: fabll.Node,
        pads: list[fabll.Node],
        leads: list["F.Lead.is_lead"] | None = None,
    ) -> Self:
        """
        Create and attach the following to a component node:
        - a footprint node (via this trait)
            - with attached pad nodes with each the is pad trait and name/number
        - add edge pointing to the footprint node

        If leads are provided, match the pads and leads.
        """
        from faebryk.library.Lead import has_associated_pads

        if not component_node.has_trait(can_attach_to_footprint):
            raise FootprintError(
                f"{component_node.get_name(accept_no_parent=True)} cannot attach to a "
                "footprint"
            )

        # we need to create and add a footprint node to the component node
        # (via can_attach_to_footprint trait) if it doesn't exist yet
        fp = fabll.Node.bind_typegraph_from_instance(
            component_node.instance
        ).create_instance(g=component_node.instance.g())
        fp_trait = fabll.Traits.create_and_add_instance_to(node=fp, trait=is_footprint)
        # add pad_nodes to the footprint with composition edge
        for pad_node in pads:
            if not pad_node.has_trait(is_pad):
                raise FootprintError(
                    f"{pad_node.get_name(accept_no_parent=True)} is not a pad"
                )
            fp.add_child(pad_node)

        fabll.Traits.create_and_add_instance_to(
            node=component_node, trait=has_associated_footprint
        ).setup(fp_trait)

        pads_t = fp_trait.get_pads()
        if leads is not None:
            # only attach to leads that don't have associated pads yet
            for lead_t in [lt for lt in leads if not lt.has_trait(has_associated_pads)]:
                matched_pad = lead_t.find_matching_pad(pads_t)
                logger.debug(
                    f"matched pad and lead: "
                    f"{matched_pad.pad_name}:{lead_t.get_lead_name()}"
                    f"for {component_node.get_name()}"
                )
        self.setup(fp_trait)
        return self


# TODO this is a placeholder for now, will be removed
class GenericFootprint(fabll.Node):
    """Generic footprint"""

    is_footprint = fabll.Traits.MakeEdge(is_footprint.MakeChild())

    pads_ = F.Collections.PointerSet.MakeChild()

    def setup(self, pads: list[is_pad]):
        """Setup the footprint with pads"""
        for pad in pads:
            self.pads_.get().append(pad)
        return self


def test_has_associated_footprint():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestFootprint(fabll.Node):
        _is_footprint = fabll.Traits.MakeEdge(is_footprint.MakeChild())

    class TestModule(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _has_associated_footprint = fabll.Traits.MakeEdge(
            has_associated_footprint.MakeChild()
        )
        _can_attach_to_footprint = fabll.Traits.MakeEdge(
            can_attach_to_footprint.MakeChild()
        )

    footprint_instance = TestFootprint.bind_typegraph(tg=tg).create_instance(g=g)
    module_with_footprint = TestModule.bind_typegraph(tg=tg).create_instance(g=g)

    module_with_footprint.get_trait(has_associated_footprint).setup(
        footprint_instance._is_footprint.get()
    )

    assert module_with_footprint.has_trait(has_associated_footprint)
    assert module_with_footprint.has_trait(can_attach_to_footprint)
    assert (
        module_with_footprint.get_trait(has_associated_footprint)
        .get_footprint()
        .instance.node()
        .is_same(other=footprint_instance._is_footprint.get().instance.node())
    )


def test_is_footprint():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestPad(fabll.Node):
        pass

    class TestFootprint(fabll.Node):
        is_footprint_ = fabll.Traits.MakeEdge(is_footprint.MakeChild())
        pads = [TestPad.MakeChild() for _ in range(3)]
        for i, pad in enumerate(pads):
            pad.add_dependant(
                fabll.Traits.MakeEdge(is_pad.MakeChild(f"pad_{i}", f"{i}"), [pad])
            )

    footprint_node = TestFootprint.bind_typegraph(tg=tg).create_instance(g=g)

    pads = footprint_node.is_footprint_.get().get_pads()
    assert len(pads) == 3
    for i, pad in enumerate(pads):
        assert pad.pad_name == f"pad_{i}"
        assert pad.pad_number == f"{i}"
