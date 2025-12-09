# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
import re
from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.library import _F as F
from faebryk.library.Collections import _get_pointer_references

logger = logging.getLogger(__name__)


class PadMatchException(Exception):
    pass


class is_lead(fabll.Node):
    """
    A lead is the connection from a component package to the footprint pad
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_lead_name(self) -> str:
        owner = fabll.Traits.bind(self).get_obj_raw()
        return owner.get_name()

    def find_matching_pad(self, pads: list[F.Footprints.is_pad]) -> F.Footprints.is_pad:
        """
        Find a matching pad for this lead based on the available attach_to_pad traits.
        Defaults to matching the lead instance name to the pad name.
        """
        if self.has_trait(can_attach_to_pad_by_name):
            pad = self.get_trait(can_attach_to_pad_by_name).find_matching_pad(pads)
        elif self.has_trait(can_attach_to_any_pad):
            pad = self.get_trait(can_attach_to_any_pad).find_matching_pad(pads)
        elif self.has_trait(can_attach_to_pad_by_name_heuristic):
            pad = self.get_trait(can_attach_to_pad_by_name_heuristic).find_matching_pad(
                pads
            )
        else:
            for pad in pads:
                if self.get_lead_name() == pad.pad_name:
                    break

        if pad is not None:
            fabll.Traits.create_and_add_instance_to(
                node=self, trait=has_associated_pads
            ).setup(pad=pad, parent=self, connect_net=False)
            return pad

        raise PadMatchException(
            f"No matching pad found for lead: {self.get_lead_name()} - {pads}"
        )


class can_attach_to_any_pad(fabll.Node):
    """
    Attach a lead to any pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    def find_matching_pad(self, pads: list[F.Footprints.is_pad]) -> F.Footprints.is_pad:
        """
        Match the first pad that is available.
        """
        claimed_pads = [
            pad.get_pad()
            for pad in fabll.Traits.get_implementors(
                has_associated_pads.bind_typegraph(self.tg), g=self.g
            )
        ]
        for pad in pads:
            if pad in claimed_pads:
                continue
            return pad
        raise PadMatchException(
            f"No matching pad found for lead with is_lead trait: {self}"
        )


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

    def find_matching_pad(self, pads: list[F.Footprints.is_pad]) -> F.Footprints.is_pad:
        """ ""
        Find a pad for this lead based on name match by regex.
        """
        for pad in pads:
            if self.regex.match(pad.pad_name):
                return pad
        raise PadMatchException(
            f"No matching pad found for lead with is_lead trait: {self}"
        )


class can_attach_to_pad_by_name_heuristic(fabll.Node):
    """
    Replaces has_pin_association_heuristic
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    case_sensitive = F.Parameters.BooleanParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls, mapping: list[str], case_sensitive: bool = False
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)

        out.add_dependant(
            F.Literals.Booleans.MakeChild_ConstrainToLiteral(
                [out, cls.case_sensitive], case_sensitive
            )
        )

        for name in mapping:
            name_lit = F.Literals.Strings.MakeChild(name)
            out.add_dependant(name_lit)
            out.add_dependant(F.Collections.Pointer.MakeEdge([out], [name_lit]))

        return out

    def find_matching_pad(self, pads: list[F.Footprints.is_pad]) -> F.Footprints.is_pad:
        """
        Find a matching pad for this lead based on name heuristics.
        """
        case_sensitive = (
            self.case_sensitive.get().force_extract_literal().get_boolean_values()[0]
        )
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

        raise PadMatchException(
            f"Could not find match for lead with aliases [{alt_names}]"
        )


class has_associated_pads(fabll.Node):
    """
    A node that has an associated pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    pad_ptr_ = F.Collections.Pointer.MakeChild()

    # TODO make get_pads to handle one to many connections
    def get_pad(self) -> F.Footprints.is_pad:
        """The pad associated with this node"""
        return self.pad_ptr_.get().deref().cast(F.Footprints.is_pad)

    @classmethod
    def MakeChild(cls, pad: fabll._ChildField[fabll.Node]) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(pad)
        return out

    def setup(self, pad: F.Footprints.is_pad, parent: fabll.Node) -> Self:
        self.pad_ptr_.get().point(pad)  # setup single pointer to single pad
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

    fabll.Traits.create_and_add_instance_to(node=lead, trait=has_associated_pads).setup(
        pad=pad.is_pad_.get(), parent=lead, connect_net=False
    )

    connected_pad = lead.get_trait(has_associated_pads).get_pad()
    assert connected_pad.is_same(pad.is_pad_.get())


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
                    can_attach_to_pad_by_name_heuristic.MakeChild(mapping[e]), [lead]
                )
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

    assert (
        module.anode.get()
        .get_trait(is_lead)
        .has_trait(can_attach_to_pad_by_name_heuristic)
    )
    assert (
        module.cathode.get()
        .get_trait(is_lead)
        .has_trait(can_attach_to_pad_by_name_heuristic)
    )

    with capsys.disabled():
        print(
            fabll.graph.InstanceGraphFunctions.render(
                module.instance, show_traits=True, show_pointers=True
            )
        )

    anode_pad = module.anode.get().get_trait(is_lead).find_matching_pad(pads)

    cathode_pad = module.cathode.get().get_trait(is_lead).find_matching_pad(pads)

    assert anode_pad.is_same(pad1)
    assert cathode_pad.is_same(pad2)


def test_can_attach_to_any_pad():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestModule(fabll.Node):
        unnamed = [F.Electrical.MakeChild() for _ in range(2)]

        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        for e in unnamed:
            lead = fabll.Traits.MakeEdge(is_lead.MakeChild(), [e])
            e.add_dependant(lead)
            lead.add_dependant(
                fabll.Traits.MakeEdge(can_attach_to_any_pad.MakeChild(), [lead])
            )

    class TestPad1(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="pad_a", pad_number="1")
        )

    class TestPad2(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="pad_b", pad_number="2")
        )

    module = TestModule.bind_typegraph(tg).create_instance(g=g)
    pad1 = TestPad1.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    pad2 = TestPad2.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    pads = [pad1, pad2]

    unnamed_0_pad = module.unnamed[0].get().get_trait(is_lead).find_matching_pad(pads)
    unnamed_1_pad = module.unnamed[1].get().get_trait(is_lead).find_matching_pad(pads)

    assert unnamed_0_pad.is_same(pad1)
    assert unnamed_1_pad.is_same(pad2)


def test_can_attach_to_pad_by_lead_name():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestModule(fabll.Node):
        hv = F.Electrical.MakeChild()
        lv = F.Electrical.MakeChild()

        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        for e in [hv, lv]:
            lead = is_lead.MakeChild()
            e.add_dependant(fabll.Traits.MakeEdge(lead, [e]))

    class TestPad1(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="hv", pad_number="1")
        )

    class TestPad2(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="lv", pad_number="2")
        )

    module = TestModule.bind_typegraph(tg).create_instance(g=g)
    pad1 = TestPad1.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    pad2 = TestPad2.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    pads = [pad1, pad2]

    hv_pad = module.hv.get().get_trait(is_lead).find_matching_pad(pads)
    lv_pad = module.lv.get().get_trait(is_lead).find_matching_pad(pads)

    assert hv_pad.is_same(pad1)
    assert lv_pad.is_same(pad2)
