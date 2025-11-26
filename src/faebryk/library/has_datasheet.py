# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


class has_datasheet(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    datasheet_ = F.Parameters.StringParameter.MakeChild()

    def get_datasheet(self) -> str:
        return self.datasheet_.get().force_extract_literal().get_values()[0]

    @classmethod
    def MakeChild(cls, datasheet: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.datasheet_], datasheet
            )
        )
        return out

    def setup(self, datasheet: str) -> Self:
        self.datasheet_.get().alias_to_single(value=datasheet)
        return self


def test_setup_populates_datasheet_literal():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    datasheet_url = "https://example.com/datasheet.pdf"

    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    trait = fabll.Traits.create_and_add_instance_to(
        node=module, trait=F.has_datasheet
    ).setup(datasheet=datasheet_url)

    assert module.get_trait(F.has_datasheet) == trait
    assert trait.get_datasheet() == datasheet_url
    assert trait.datasheet_.get().force_extract_literal().get_values() == [
        datasheet_url
    ]


def test_makechild_sets_datasheet_on_instance():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    datasheet_url = "https://example.com/another.pdf"

    class ModuleWithDatasheet(fabll.Node):
        datasheet = fabll.Traits.MakeEdge(
            F.has_datasheet.MakeChild(datasheet=datasheet_url)
        )

    module = ModuleWithDatasheet.bind_typegraph(tg=tg).create_instance(g=g)

    assert module.has_trait(F.has_datasheet)
    assert module.get_trait(F.has_datasheet).get_datasheet() == datasheet_url
