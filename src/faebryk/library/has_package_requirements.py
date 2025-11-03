# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F

# from faebryk.core.parameter import EnumDomain
# from faebryk.core.solver.solver import Solver
from faebryk.libs.sets.sets import EnumSet
from faebryk.libs.smd import SMDSize

# from faebryk.libs.util import cast_assert


class has_package_requirements(fabll.Node):
    """
    Collection of constraints for package of module.
    """

    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    # size = fabll.p_field(domain=EnumDomain(SMDSize))
    size = fabll.Parameter.MakeChild_Enum(enum_t=SMDSize)

    def __init__(self, *, size: SMDSize | EnumSet[SMDSize] | None = None) -> None:
        super().__init__()

        self._size = size

    @classmethod
    def MakeChild(cls, size: SMDSize | EnumSet[SMDSize] | None = None):
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.size],
                size,
            )
        )
        return out

    # def get_sizes(self, solver: Solver) -> EnumSet[SMDSize]:
    #     ss = self.size.get_last_known_deduced_superset(solver)
    #     return cast_assert(EnumSet, ss)
