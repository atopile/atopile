# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from typing import Self

import faebryk.core.node as fabll

# from faebryk.core.solver.solver import Solver

logger = logging.getLogger(__name__)


class has_solver(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    # def setup(self, solver: Solver) -> Self:
    #     # TODO: Figure out python pointer
    #     self.solver = solver
    #     return self

    # TODO: figure out how to pass solver state without trait
    # solver_ = fabll.ChildField(Solver)
    # def __init__(self, solver: Solver):
    #     self._solver = solver
    #     super().__init__()

    # @property
    # def solver(self) -> Solver:
    #     return self._solver
