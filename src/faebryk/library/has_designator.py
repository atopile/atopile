# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_designator(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    designator_ = F.Parameters.StringParameter.MakeChild()

    def get_designator(self) -> str:
        literal = self.designator_.get().try_extract_constrained_literal()
        if literal is None:
            raise ValueError("Designator is not set")
        return str(literal)

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
        self.designator_.get().constrain_to_single(value=designator)
        return self
