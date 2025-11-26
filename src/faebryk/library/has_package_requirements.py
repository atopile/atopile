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

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    # size = fabll.p_field(domain=EnumDomain(SMDSize))
    # size_ = F.Parameters.EnumParameter.MakeChild(enum_t=SMDSize)

    @classmethod
    def MakeChild(cls, size: SMDSize):
        out = fabll._ChildField(cls)
        # TODO: Constrain to ENUM value
        # out.add_dependant(
        # F.Expressions.Is.MakeChild_ConstrainToLiteral(
        #     [out, cls.size],
        #     size,
        # )
        # )
        return out

    def setup(self, *sizes: SMDSize):
        pass
        # self.size_.get().alias_to_literal(g=self.instance.g(), value=sizes)
        # return self

    # def get_sizes(self, solver: Solver) -> EnumSet[SMDSize]:
    #     ss = self.size.get_last_known_deduced_superset(solver)
    #     return cast_assert(EnumSet, ss)
