# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_designator(fabll.Node):
    designator_ = fabll.ChildField(fabll.Parameter)

    def get_designator(self) -> str | None:
        literal = self.designator_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @classmethod
    def MakeChild(cls, designator: str) -> fabll.ChildField:
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.designator_], designator
            )
        )
        return out

    def setup(self, designator: str) -> Self:
        self.designator_.get().constrain_to_literal(
            g=self.instance.g(), value=designator
        )
        return self
