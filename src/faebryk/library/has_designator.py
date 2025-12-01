# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.app.designators import attach_random_designators

class has_designator(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    designator_ = F.Parameters.StringParameter.MakeChild()

    def get_designator(self) -> str | None:
        literal = self.designator_.get().try_extract_constrained_literal()
        if literal is None:
            return None
        return literal.get_values()[0]

    @classmethod
    def MakeChild(cls, designator: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.designator_], designator
            )
        )
        return out

    def setup(self, designator: str) -> Self:
        self.designator_.get().alias_to_single(value=designator)
        return self

class Test:

    def test_designator_generation(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        resistor1 = F.Resistor.bind_typegraph(tg=tg).create_instance(g=g)
        resistor2 = F.Resistor.bind_typegraph(tg=tg).create_instance(g=g)
        capacitor1 = F.Capacitor.bind_typegraph(tg=tg).create_instance(g=g)

        assert resistor1.has_trait(F.has_designator) is False
        assert resistor2.has_trait(F.has_designator) is False
        assert capacitor1.has_trait(F.has_designator) is False

        attach_random_designators(tg)

        assert {
            resistor1.get_trait(F.has_designator).get_designator(),
            resistor2.get_trait(F.has_designator).get_designator()
        } == {"R1", "R2"}
        
        assert capacitor1.get_trait(F.has_designator).get_designator() == "C1"

    def test_manual_designator_assignment(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        resistor1 = F.Resistor.bind_typegraph(tg=tg).create_instance(g=g)
        resistor2 = F.Resistor.bind_typegraph(tg=tg).create_instance(g=g)
        capacitor1 = F.Capacitor.bind_typegraph(tg=tg).create_instance(g=g)

        assert resistor1.has_trait(F.has_designator) is False

        fabll.Traits.create_and_add_instance_to(resistor1, F.has_designator)
        resistor1.get_trait(F.has_designator).setup("R1")

        assert resistor1.get_trait(F.has_designator).get_designator() == "R1"

        attach_random_designators(tg)

        assert resistor1.get_trait(F.has_designator).get_designator() == "R1"
        assert resistor2.get_trait(F.has_designator).get_designator() == "R2"

        assert capacitor1.get_trait(F.has_designator).get_designator() == "C1"
