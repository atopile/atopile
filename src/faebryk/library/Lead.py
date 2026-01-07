# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
import re
from typing import Self

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.library import _F as F

logger = logging.getLogger(__name__)


class LeadPadMatchException(Exception):
    pass


class is_lead(fabll.Node):
    """
    A lead is the connection from a component package to the footprint pad
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_lead_name(self) -> str:
        owner = fabll.Traits.bind(self).get_obj_raw()
        return owner.get_name()

    def find_matching_pad(
        self, pads: list[F.Footprints.is_pad], associate: bool = True
    ) -> F.Footprints.is_pad:
        """
        Find a matching pad for this lead based on the available attach_to_pad traits.
        Defaults to matching the lead instance name to the pad name.
        """
        pads = sorted(pads, key=lambda x: x.pad_name)
        if self.has_trait(can_attach_to_pad_by_name):
            pad = self.get_trait(can_attach_to_pad_by_name).find_matching_pad(pads)
        elif self.has_trait(can_attach_to_any_pad):
            pad = self.get_trait(can_attach_to_any_pad).find_matching_pad(pads)
        else:
            for pad in pads:
                if self.get_lead_name() == pad.pad_name:
                    break

        if pad is not None:
            if associate:
                fabll.Traits.create_and_add_instance_to(
                    node=self, trait=has_associated_pads
                ).setup(pad=pad)
            return pad

        raise LeadPadMatchException(
            f"No matching pad found for lead: {self.get_lead_name()}"
        )


class can_attach_to_any_pad(fabll.Node):
    """
    Attach a lead to any pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

    def find_matching_pad(self, pads: list[F.Footprints.is_pad]) -> F.Footprints.is_pad:
        """
        Match the first pad that is available.
        """
        # Flatten all pads from has_associated_pads implementors into a single set
        claimed_pads = {
            pad
            for implementor in fabll.Traits.get_implementors(
                has_associated_pads.bind_typegraph(self.tg), g=self.g
            )
            for pad in implementor.get_pads()
        }
        for pad in pads:
            if pad not in claimed_pads:
                return pad
        raise LeadPadMatchException(
            f"No pad available for lead "
            f"[{self.get_name()}] - All pads are probably claimed by other leads."
        )


class can_attach_to_pad_by_name(fabll.Node):
    """
    Attach a lead to a pad by matching the pad name using a regex.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    regex_ = F.Parameters.StringParameter.MakeChild()
    case_sensitive_ = F.Parameters.BooleanParameter.MakeChild()

    @property
    def compiled_regex(self) -> re.Pattern:
        case_sensitive = (
            self.case_sensitive_.get().force_extract_literal().get_boolean_values()[0]
        )
        regex = self.regex_.get().force_extract_literal().get_values()[0]
        try:
            return re.compile(
                regex,
                flags=re.IGNORECASE if not case_sensitive else 0,
            )
        except re.error as e:
            raise LeadPadMatchException(
                f"Invalid regex for lead [{self.get_name()}] with regex [{regex}]: {e}"
            )

    @classmethod
    def MakeChild(
        cls, regex: str, case_sensitive: bool = False
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.regex_], regex)
        )
        out.add_dependant(
            F.Literals.Booleans.MakeChild_ConstrainToLiteral(
                [out, cls.case_sensitive_], case_sensitive
            )
        )
        return out

    def setup(self, regex: str, case_sensitive: bool = False) -> Self:
        self.regex_.get().alias_to_single(value=regex)
        self.case_sensitive_.get().alias_to_single(value=case_sensitive)
        return self

    def find_matching_pad(self, pads: list[F.Footprints.is_pad]) -> F.Footprints.is_pad:
        """
        Find a pad for this lead based on name match by regex.
        """
        regex = self.compiled_regex
        matched_pads: list[F.Footprints.is_pad] = []
        for pad in pads:
            if regex.match(pad.pad_name):
                matched_pads.append(pad)

        if not matched_pads:
            for pad in pads:
                if regex.match(pad.pad_number):
                    matched_pads.append(pad)

        if len(matched_pads) == 1:
            return matched_pads[0]
        if len(matched_pads) > 1:
            raise LeadPadMatchException(
                f"Matched {len(matched_pads)} out of {len(pads)} pads for lead "
                f"[{self.get_name()}] with regex [{regex.pattern}]"
            )
        raise LeadPadMatchException(
            f"No matching pad found for lead [{self.get_name()}] "
            f"with regex [{regex.pattern}]"
        )


class has_associated_pads(fabll.Node):
    """
    A node that has an associated pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    pad_ptr_ = F.Collections.Pointer.MakeChild()

    # TODO make get_pads to handle one to many connections
    def get_pads(self) -> set[F.Footprints.is_pad]:
        """The pad associated with this node"""
        return set(
            pad.cast(F.Footprints.is_pad) for pad in self.pad_ptr_.get().as_list()
        )

    @classmethod
    def MakeChild(cls, pad: fabll._ChildField[fabll.Node]) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(pad)
        return out

    def setup(self, pad: F.Footprints.is_pad) -> Self:
        self.pad_ptr_.get().point(pad)
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
    pad = fabll.Node.bind_typegraph(tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(node=pad, trait=F.Footprints.is_pad).setup(
        pad_name="Pad_A", pad_number="0"
    )

    fabll.Traits.create_and_add_instance_to(node=lead, trait=has_associated_pads).setup(
        pad=pad.get_trait(F.Footprints.is_pad)
    )

    connected_pad = lead.get_trait(has_associated_pads).get_pads().pop()
    assert connected_pad.is_same(pad.get_trait(F.Footprints.is_pad))

    assert connected_pad.pad_name == "Pad_A"
    assert connected_pad.pad_number == "0"


def test_can_attach_to_pad_by_name():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _TestModule(fabll.Node):
        anode = F.Electrical.MakeChild()
        cathode = F.Electrical.MakeChild()

        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        mapping = {
            anode: r"Anode|a",
            cathode: r"cathode|c",
        }

        for e in [anode, cathode]:
            lead = is_lead.MakeChild()
            e.add_dependant(fabll.Traits.MakeEdge(lead, [e]))
            lead.add_dependant(
                fabll.Traits.MakeEdge(
                    can_attach_to_pad_by_name.MakeChild(mapping[e]), [lead]
                )
            )

    class _AnodePad(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="anode", pad_number="1")
        )

    class _CathodePad(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="cathode", pad_number="2")
        )

    module = _TestModule.bind_typegraph(tg).create_instance(g=g)
    anode_pad = _AnodePad.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    cathode_pad = _CathodePad.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    pads = [anode_pad, cathode_pad]

    assert module.anode.get().get_trait(is_lead).has_trait(can_attach_to_pad_by_name)
    assert module.cathode.get().get_trait(is_lead).has_trait(can_attach_to_pad_by_name)

    matched_anode_pad = module.anode.get().get_trait(is_lead).find_matching_pad(pads)
    matched_cathode_pad = (
        module.cathode.get().get_trait(is_lead).find_matching_pad(pads)
    )

    assert matched_anode_pad.is_same(anode_pad)
    assert matched_cathode_pad.is_same(cathode_pad)


def test_can_attach_to_any_pad():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _TestModule(fabll.Node):
        unnamed = [F.Electrical.MakeChild() for _ in range(3)]

        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        for e in unnamed:
            lead = fabll.Traits.MakeEdge(is_lead.MakeChild(), [e])
            e.add_dependant(lead)
            lead.add_dependant(
                fabll.Traits.MakeEdge(can_attach_to_any_pad.MakeChild(), [lead])
            )

    class _TestPad0(fabll.Node):
        is_pad_ = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="pad_0", pad_number="0")
        )

    class _TestPad1(fabll.Node):
        is_pad_ = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="pad_1", pad_number="1")
        )

    class _TestPad2(fabll.Node):
        is_pad_ = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="pad_2", pad_number="2")
        )

    module = _TestModule.bind_typegraph(tg).create_instance(g=g)
    pad0 = _TestPad0.bind_typegraph(tg).create_instance(g=g).is_pad_.get()
    pad1 = _TestPad1.bind_typegraph(tg).create_instance(g=g).is_pad_.get()
    pad2 = _TestPad2.bind_typegraph(tg).create_instance(g=g).is_pad_.get()
    pads = [pad0, pad1, pad2]

    unnamed_0_pad = module.unnamed[0].get().get_trait(is_lead).find_matching_pad(pads)
    unnamed_1_pad = module.unnamed[1].get().get_trait(is_lead).find_matching_pad(pads)

    fabll.Traits.create_and_add_instance_to(
        node=module.unnamed[1].get(), trait=has_associated_pads
    ).setup(pad=pad2)

    with pytest.raises(LeadPadMatchException):
        module.unnamed[2].get().get_trait(is_lead).find_matching_pad(pads)

    assert unnamed_0_pad.is_same(pad0)
    assert unnamed_1_pad.is_same(pad1)


def test_can_attach_to_pad_by_lead_name():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _TestModule(fabll.Node):
        hv = F.Electrical.MakeChild()
        lv = F.Electrical.MakeChild()

        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        for e in [hv, lv]:
            lead = is_lead.MakeChild()
            e.add_dependant(fabll.Traits.MakeEdge(lead, [e]))

    class _HVPad(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="hv", pad_number="1")
        )

    class _LVPad(fabll.Node):
        _is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="lv", pad_number="2")
        )

    module = _TestModule.bind_typegraph(tg).create_instance(g=g)
    hv_pad = _HVPad.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    lv_pad = _LVPad.bind_typegraph(tg).create_instance(g=g)._is_pad.get()
    pads = [hv_pad, lv_pad]

    matched_hv_pad = module.hv.get().get_trait(is_lead).find_matching_pad(pads)
    matched_lv_pad = module.lv.get().get_trait(is_lead).find_matching_pad(pads)

    assert matched_hv_pad.is_same(hv_pad)
    assert matched_lv_pad.is_same(lv_pad)
