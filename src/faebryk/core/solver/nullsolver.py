from typing import Any, override

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver


class NullSolver(Solver):
    @override
    def get_any_single(
        self,
        operatable: F.Parameters.is_parameter,
        lock: bool,
        suppose_predicate: F.Expressions.is_assertable | None = None,
        minimize: F.Expressions.is_expression | None = None,
    ) -> Any:
        return operatable.domain_set().any()

    @override
    def try_fulfill(
        self,
        predicate: F.Expressions.is_assertable,
        lock: bool,
        allow_unknown: bool = False,
    ) -> bool:
        if lock:
            predicate.assert_()
        return True

    @override
    def inspect_get_known_supersets(
        self, value: F.Parameters.is_parameter
    ) -> F.Literals.is_literal:
        lit = value.as_parameter_operatable.get().try_get_subset_or_alias_literal()
        if lit is None:
            lit = value.domain_set()
        return lit

    @override
    def simplify(self, g: graph.GraphView, tg: fbrk.TypeGraph, terminal: bool = False):
        pass
