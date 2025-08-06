# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging

from faebryk.core.solver.solver import Solver
from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)


class has_solver(Trait.decless()):
    def __init__(self, solver: Solver):
        self._solver = solver
        super().__init__()

    @property
    def solver(self) -> Solver:
        return self._solver
