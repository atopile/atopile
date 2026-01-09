from typing import Any, override

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver


class NullSolver(Solver):
    @override
    def extract_superset(
        self,
        value: F.Parameters.is_parameter,
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> F.Literals.is_literal:
        lit = value.as_parameter_operatable.get().try_extract_superset()
        if lit is None:
            lit = value.domain_set()
        return lit

    @override
    def simplify(
        self,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        terminal: bool = False,
        relevant: list[F.Parameters.can_be_operand] | None = None,
    ):
        pass
