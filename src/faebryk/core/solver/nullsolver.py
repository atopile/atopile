from typing import Any, override

from faebryk.core.cpp import Graph
from faebryk.core.node import Node
from faebryk.core.parameter import (
    ConstrainableExpression,
    Expression,
    Parameter,
    Predicate,
)
from faebryk.core.solver.solver import Solver
from faebryk.libs.sets.sets import P_Set, as_lit


class NullSolver(Solver):
    @override
    def get_any_single(
        self,
        operatable: Parameter,
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Any:
        return operatable.domain_set().any()

    @override
    def try_fulfill(
        self,
        predicate: ConstrainableExpression,
        lock: bool,
        allow_unknown: bool = False,
    ) -> bool:
        if lock:
            predicate.constrain()
        return True

    @override
    def update_superset_cache(self, *nodes: Node):
        pass

    @override
    def inspect_get_known_supersets(self, value: Parameter) -> P_Set:
        lit = value.try_get_literal_subset()
        if lit is None:
            lit = value.domain_set()
        return as_lit(lit)

    @override
    def simplify(self, *gs: Graph | Node):
        pass
