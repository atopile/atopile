# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


class has_datasheet(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    datasheet_ = F.Parameters.StringParameter.MakeChild()

    def get_datasheet(self) -> str:
        return self.datasheet_.get().extract_singleton()

    @classmethod
    def MakeChild(cls, datasheet: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.datasheet_], datasheet)
        )
        return out

    def setup(self, datasheet: str) -> Self:
        self.datasheet_.get().set_singleton(value=datasheet)
        return self


def test_setup_populates_datasheet_literal():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    datasheet_url = "https://example.com/datasheet.pdf"

    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    trait = fabll.Traits.create_and_add_instance_to(
        node=module, trait=has_datasheet
    ).setup(datasheet=datasheet_url)

    assert module.get_trait(has_datasheet) == trait
    assert trait.get_datasheet() == datasheet_url
    assert trait.datasheet_.get().extract_singleton() == datasheet_url


def test_makechild_sets_datasheet_on_instance():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    datasheet_url = "https://example.com/another.pdf"

    class _ModuleWithDatasheet(fabll.Node):
        has_datasheet = fabll.Traits.MakeEdge(
            has_datasheet.MakeChild(datasheet=datasheet_url)
        )

    module = _ModuleWithDatasheet.bind_typegraph(tg=tg).create_instance(g=g)

    assert module.has_trait(has_datasheet)
    assert module.has_datasheet.get().get_datasheet() == datasheet_url
