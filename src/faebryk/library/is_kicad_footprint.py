# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


class is_kicad_footprint(fabll.Node):
    """
    Marks a node as a KiCad footprint.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()
    kicad_identifier_ = F.Parameters.StringParameter.MakeChild()

    def get_kicad_footprint_identifier(self) -> str:
        return self.kicad_identifier_.get().force_extract_literal().get_values()[0]

    def get_kicad_footprint_name(self) -> str:
        return self.get_kicad_footprint_identifier().split(":")[1]

    def get_pad_names(self) -> list[str]:
        # FIX: is_kicad_pad is not a child of is_kicad_footprint, but of
        # the sibling node of the parent of is_kicad_footprint
        return [
            p.get_trait(F.is_kicad_pad).get_pad_name()
            for p in self.get_children(
                direct_only=False, types=fabll.Node, required_trait=F.is_kicad_pad
            )
        ]

    @classmethod
    def MakeChild(cls, kicad_identifier: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.kicad_identifier_], kicad_identifier
            )
        )
        return out

    def setup(self, kicad_identifier: str) -> Self:
        self.kicad_identifier_.get().alias_to_single(
            g=self.instance.g(), value=kicad_identifier
        )
        return self


def test_is_kicad_footprint():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class KCFootprint(fabll.Node):
        class KCPad(fabll.Node):
            is_kicad_pad = fabll.Traits.MakeEdge(
                F.is_kicad_pad.MakeChild(pad_name="P1")
            )

        is_kicad_footprint = fabll.Traits.MakeEdge(
            is_kicad_footprint.MakeChild(
                kicad_identifier="Resistor:libR_0402_1005Metric2"
            )
        )
        kc_pad = KCPad.MakeChild()

    kicad_footprint = KCFootprint.bind_typegraph(tg=tg).create_instance(g=g)

    assert (
        kicad_footprint.is_kicad_footprint.get().get_kicad_footprint_identifier()
        == "Resistor:libR_0402_1005Metric2"
    )
    assert (
        kicad_footprint.is_kicad_footprint.get().get_kicad_footprint_name()
        == "libR_0402_1005Metric2"
    )
    kc_fp_trait = kicad_footprint.is_kicad_footprint.get()
    pad_names = kc_fp_trait.get_pad_names()

    assert len(pad_names) == 1
    assert pad_names[0] == "P1"
