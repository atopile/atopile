# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.module import Module
from faebryk.core.parameter import EnumDomain
from faebryk.core.solver.solver import Solver
from faebryk.libs.library import L
from faebryk.libs.sets.sets import EnumSet
from faebryk.libs.smd import SMDSize
from faebryk.libs.util import cast_assert


class has_package_requirements(Module.TraitT.decless()):
    """
    Collection of constraints for package of module.
    """

    size = L.p_field(domain=EnumDomain(SMDSize))

    def __init__(self, *, size: SMDSize | EnumSet[SMDSize] | None = None) -> None:
        super().__init__()

        self._size = size

    def __preinit__(self):
        if self._size is not None:
            self.size.constrain_subset(EnumSet(self._size))

    def get_sizes(self, solver: Solver) -> EnumSet[SMDSize]:
        ss = self.size.get_last_known_deduced_superset(solver)
        return cast_assert(EnumSet, ss)
