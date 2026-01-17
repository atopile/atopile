# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_net_name(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    name_ = fabll._ChildField(F.Parameters.StringParameter)

    def get_name(self) -> str:
        return self.name_.get().extract_singleton()

    @classmethod
    def MakeChild(cls, name: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.name_], name)
        )
        return out

    def setup(self, name: str) -> Self:
        self.name_.get().set_singleton(value=name)
        return self
