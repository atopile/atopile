# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.library import _F as F
from faebryk.libs.util import not_none


class is_lead(fabll.Node):
    """
    A lead is the connection from a component package to the footprint pad
    """

    class PadMatchException(Exception):
        pass

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_lead(self) -> tuple[fabll.Node, str]:
        return not_none(self.get_parent())

    def find_matching_pad(
        self, pads: list[F.Footprints.is_pad]
    ) -> F.Footprints.is_pad | None:
        # 1. try find name match with regex if can_attach_to_pad_by_name is present
        # 2. try any pin if can_attach_to_any_pad is present
        # 3. try find exact name match (lead name == pad name)
        # 4. if no match, return None
        if self.has_trait(F.can_attach_to_pad_by_name):
            matched_pad = next(
                (
                    pad
                    for pad in pads
                    if self.get_trait(F.can_attach_to_pad_by_name).regex.match(
                        pad.pad_name
                    )
                ),
                None,
            )
        elif self.has_trait(F.can_attach_to_any_pad):
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
                f"No matching pad found for lead with is_lead trait: {self}"
            )
        return matched_pad


def test_is_lead():
    from faebryk.library.has_associated_pad import has_associated_pad

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestLead(fabll.Node):
        _is_lead = fabll.Traits.MakeEdge(is_lead.MakeChild())
        _can_attach_to_any_pad = fabll.Traits.MakeEdge(
            F.can_attach_to_any_pad.MakeChild()
        )
        line = F.Electrical.MakeChild()

    lead = TestLead.bind_typegraph(tg).create_instance(g=g)

    assert lead.has_trait(is_lead)
    assert lead.has_trait(F.can_attach_to_any_pad)

    # emulate attaching to a pad, normaly done in build process
    class TestPad(fabll.Node):
        # _is_pad = fabll.Traits.MakeEdge(F.Footprints.is_pad.MakeChild())
        _has_associated_net = fabll.Traits.MakeEdge(
            F.has_associated_net.MakeChild(F.Net.MakeChild())
        )

    pad = TestPad.bind_typegraph(tg).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(node=lead, trait=has_associated_pad).setup(
        pad=pad
    )

    connected_pad = lead.get_trait(has_associated_pad).pad
    assert connected_pad.is_same(pad)
    assert (
        connected_pad.get_trait(F.has_associated_net)
        .net.get_trait(fabll.is_interface)
        .is_connected_to(lead.line.get())
    )
