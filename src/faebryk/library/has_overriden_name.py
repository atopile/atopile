# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_overriden_name(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    name_ = fabll.ChildField(fabll.Parameter)

    def get_name(self) -> str | None:
        literal = self.name_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @classmethod
    def MakeChild(cls, name: str) -> fabll.ChildField:
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.name_], name)
        )
        return out

    def setup(self, name: str) -> Self:
        self.name_.get().constrain_to_literal(self.instance.g(), name)
        return self
