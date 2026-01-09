# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import ctypes
import logging
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver

logger = logging.getLogger(__name__)


class has_solver(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    solver_ = F.Parameters.StringParameter.MakeChild()

    def setup(self, solver: Solver) -> Self:  # type: ignore[invalid-method-override]
        self.solver_.get().set_singleton(value=str(id(solver)))
        return self

    def get_solver(self) -> Solver:
        solver_id = int(self.solver_.get().extract_singleton())
        return ctypes.cast(solver_id, ctypes.py_object).value
