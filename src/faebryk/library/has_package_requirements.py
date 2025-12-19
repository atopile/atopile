# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.smd import SMDSize


class has_package_requirements(fabll.Node):
    """
    Collection of constraints for package of module.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
    size = F.Parameters.EnumParameter.MakeChild(enum_t=SMDSize)

    def get_sizes(self) -> list[SMDSize]:
        return self.size.get().force_extract_literal().get_values_typed(SMDSize)

    @classmethod
    def MakeChild(cls, size: SMDSize):  # type: ignore[invalid-method-override]
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
                [out, cls.size],
                size,
            )
        )
        return out
