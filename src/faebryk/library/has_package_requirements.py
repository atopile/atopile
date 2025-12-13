# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.smd import SMDSize

# from faebryk.libs.util import cast_assert


class has_package_requirements(fabll.Node):
    """
    Collection of constraints for package of module.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    size_ = F.Parameters.EnumParameter.MakeChild(enum_t=SMDSize)

    @classmethod
    def MakeChild(cls, size: SMDSize):  # type: ignore[invalid-method-override]
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
                [out, cls.size_],
                size,
            )
        )
        return out

    def setup(self, *sizes: SMDSize):
        self.size_.get().alias_to_literal(*sizes)
        return self
