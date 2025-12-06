# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
import re
from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.library.Collections import _get_pointer_references
from faebryk.library import _F as F
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)

class is_lead(fabll.Node):
    """
    A lead is the connection from a component package to the footprint pad
    """

    class PadMatchException(Exception):
        pass

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_lead(self) -> tuple[fabll.Node, str]:
        return not_none(self.get_parent())

    def find_matching_pad(self, pads: list[F.Footprints.is_pad]) -> F.Footprints.is_pad:
        # 1. try find name match with regex if can_attach_to_pad_by_name is present
        # 2. try any pin if can_attach_to_any_pad is present
        # 3. try find exact name match (lead name == pad name)
        # 4. if no match, return None
        if self.has_trait(can_attach_to_pad_by_name):
            matched_pad = next(
                (
                    pad
                    for pad in pads
                    if self.get_trait(can_attach_to_pad_by_name).regex.match(
                        pad.pad_name
                    )
                ),
                None,
            )
        elif self.has_trait(can_attach_to_any_pad):
            matched_pad = next(
                (pad for pad in pads),
                None,
            )
        else:
            matched_pad = next(
                (pad for pad in pads if self.get_lead()[1] == pad.pad_name),
                None,
            )
        if matched_pad is None:
            raise self.PadMatchException(
                f"No matching pad found for lead: {self.get_lead()[1]} - {pads}"
            )
        return matched_pad

    # TODO: this is ugly code
    def find_matching_pad_name(self, pad_names: list[str]) -> str:
        # 1. try find name match with regex if can_attach_to_pad_by_name is present
        # 2. try any pin if can_attach_to_any_pad is present
        # 3. try find exact name match (lead name == pad name)
        # 4. if no match, return None
        if self.has_trait(can_attach_to_pad_by_name):
            matched_pad = next(
                (
                    pad_name
                    for pad_name in pad_names
                    if self.get_trait(can_attach_to_pad_by_name).regex.match(pad_name)
                ),
                None,
            )
        elif self.has_trait(can_attach_to_any_pad):
            matched_pad = next(
                (pad_name for pad_name in pad_names),
                None,
            )
        else:
            matched_pad = next(
                (pad_name for pad_name in pad_names if self.get_lead()[1] == pad_name),
                None,
            )

        if matched_pad is None:
            raise self.PadMatchException(
                f"No matching pad found for lead with is_lead trait: {self}"
            )
        return matched_pad


class can_attach_to_any_pad(fabll.Node):
    """
    Attach a lead to any pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()


class can_attach_to_pad_by_name(fabll.Node):
    """
    Attach a lead to a pad by matching the pad name using a regex.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    regex_ = F.Parameters.StringParameter.MakeChild()

    @property
    def regex(self) -> re.Pattern:
        return re.compile(self.regex_.get().force_extract_literal().get_values()[0])

    @classmethod
    def MakeChild(cls, regex: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.regex_], regex)
        )
        return out

    def setup(self, regex: str) -> Self:
        self.regex_.get().alias_to_single(value=regex)
        return self


class can_attach_to_pad_by_name_heuristic(fabll.Node):
    """
    Replaces has_pin_association_heuristic
    """
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    case_sensitive = F.Parameters.BooleanParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls,
        mapping: list[str],
        case_sensitive: bool = False
    ) -> fabll._ChildField[Self]:
        logger.info(f"Making can_attach_to_pad_by_name_heuristic with mapping: {mapping}")
        out = fabll._ChildField(cls)

        out.add_dependant(
            F.Literals.Booleans.MakeChild_ConstrainToLiteral(
                [out, cls.case_sensitive], case_sensitive
            )
        )

        for name in mapping:
            name_lit = F.Literals.Strings.MakeChild(name)
            out.add_dependant(name_lit)
            out.add_dependant(
                F.Collections.Pointer.MakeEdge([out], [name_lit])
            )

        return out

    def lead_matches_pad(self, pads: list[F.Footprints.is_pad]) -> F.Footprints.is_pad:
        """
        Find a matching pad for this lead based on name heuristics.
        """
        case_sensitive = self.case_sensitive.get().try_extract_constrained_literal().get_single()
        alt_names = _get_pointer_references(self)
        nc = {"NC", "nc"}

        for pad in pads:
            match = False
            if pad.pad_name in nc:
                continue
            for alt_name in alt_names:
                alt_name = alt_name.cast(F.Literals.Strings).get_values()[0]
                if not case_sensitive:
                    if pad.pad_name.lower() == alt_name.lower():
                        match = True
                else:
                    if pad.pad_name == alt_name:
                        match = True
                if match:
                    logger.info(
                        f"Matched pad [{pad.pad_number}:{pad.pad_name}]\
                            to lead via alias [{alt_name}]"
                    )
                    return pad

        raise is_lead.PadMatchException(
            f"Could not find match for lead with aliases [{alt_names}]"
        )


class has_associated_pad(fabll.Node):
    """
    A node that has an associated pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    pad_ptr_ = F.Collections.Pointer.MakeChild()

    def get_pad(self) -> fabll.Node:
        """The pad associated with this node"""
        return self.pad_ptr_.get().deref()

    @classmethod
    def MakeChild(cls, pad: fabll._ChildField[fabll.Node]) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(pad)
        return out

    def setup(
        self, pad: F.Footprints.is_pad, parent: fabll.Node, connect_net: bool = True
    ) -> Self:
        self.pad_ptr_.get().point(pad)

        if connect_net:
            if parent.try_get_trait(fabll.is_interface) is None:
                raise ValueError("Parent is not an Electrical")
            pad_net_t = pad.try_get_trait(F.Footprints.has_associated_net)
            if pad_net_t is None:
                raise ValueError("Pad has no associated net")
            pad_net_t.net.part_of.get()._is_interface.get().connect_to(parent)
        return self


def test_is_lead():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    lead = F.Electrical.bind_typegraph(tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(node=lead, trait=is_lead)
    fabll.Traits.create_and_add_instance_to(node=lead, trait=can_attach_to_any_pad)

    assert lead.has_trait(is_lead)
    assert lead.has_trait(can_attach_to_any_pad)

    # emulate attaching to a pad, normaly done in build process
    pad = F.Footprints.GenericPad.bind_typegraph(tg).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(node=lead, trait=has_associated_pad).setup(
        pad=pad.is_pad_.get(), parent=lead, connect_net=False
    )

    connected_pad = lead.get_trait(has_associated_pad).get_pad()
    assert connected_pad.is_same(pad.is_pad_.get())
    # TODO: add net to pad so we can test this
    # assert (
    #     connected_pad.get_trait(F.KiCadFootprints.has_associated_net)
    #     .net.get_trait(fabll.is_interface)
    #     .is_connected_to(lead)
    # )


def test_can_attach_to_pad_by_name_heuristic(capsys):
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestModule(fabll.Node):
        anode = F.Electrical.MakeChild()
        cathode = F.Electrical.MakeChild()

        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        mapping = {
            anode: ["Anode", "a"],
            cathode: ["cathode", "c"],
        }

        for e in [anode, cathode]:
            lead = is_lead.MakeChild()
            e.add_dependant(fabll.Traits.MakeEdge(lead, [e]))
            lead.add_dependant(
                fabll.Traits.MakeEdge(
                    can_attach_to_pad_by_name_heuristic.MakeChild(mapping[e]), [lead])
            )

    class TestPad1(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="anode", pad_number="1")
        )

    class TestPad2(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="cathode", pad_number="2")
        )

    module = TestModule.bind_typegraph(tg).create_instance(g=g)
    pad1 = TestPad1.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    pad2 = TestPad2.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    pads = [pad1, pad2]

    assert module.anode.get().get_trait(is_lead).has_trait(
        can_attach_to_pad_by_name_heuristic)
    assert module.cathode.get().get_trait(is_lead).has_trait(
        can_attach_to_pad_by_name_heuristic)

    with capsys.disabled():
        print(fabll.graph.InstanceGraphFunctions.render(
            module.instance, show_traits=True, show_pointers=True))

    anode_pad = module.anode.get().get_trait(is_lead).get_trait(
        can_attach_to_pad_by_name_heuristic).lead_matches_pad(pads)

    cathode_pad = module.cathode.get().get_trait(is_lead).get_trait(
        can_attach_to_pad_by_name_heuristic).lead_matches_pad(pads)

    assert anode_pad.is_same(pad1)
    assert cathode_pad.is_same(pad2)


def test_can_attach_to_any_pad(capsys):
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestModule(fabll.Node):
        unnamed = [F.Electrical.MakeChild() for _ in range(2)]

        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        for e in unnamed:
            lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [e])
            e.add_dependant(lead)
            lead.add_dependant(fabll.Traits.MakeEdge(F.Lead.can_attach_to_any_pad.MakeChild(), [lead]))

    module = TestModule.bind_typegraph(tg).create_instance(g=g)

    assert module.unnamed[0].get().get_trait(F.Lead.is_lead).has_trait(F.Lead.can_attach_to_any_pad)
    assert module.unnamed[1].get().get_trait(F.Lead.is_lead).has_trait(F.Lead.can_attach_to_any_pad)

    with capsys.disabled():
        print(fabll.graph.InstanceGraphFunctions.render(module.instance, show_traits=True))
