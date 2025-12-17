# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.libs.smd import SMDSize

# from faebryk.libs.util import cast_assert


class has_package_requirements(fabll.Node):
    """
    Collection of constraints for package of module.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
    size_ = F.Parameters.EnumParameter.MakeChild(enum_t=SMDSize)

    def get_sizes(self, solver: Solver) -> list[SMDSize]:
        # TODO: use solver to get size
        sizes = self.size_.get().force_extract_literal().get_values_typed(SMDSize)

        return sizes

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
