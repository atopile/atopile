from typing import Any, override

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver


class NullSolver(Solver):
    @override
    def get_any_single(
        self,
        operatable: fabll.NodeT,
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Any:
        return operatable.domain_set().any()

    @override
    def try_fulfill(
        self,
        predicate: fabll.NodeT,
        lock: bool,
        allow_unknown: bool = False,
    ) -> bool:
        if lock:
            predicate.constrain()
        return True

    @override
    def update_superset_cache(self, *nodes: fabll.Node):
        pass

    @override
    def inspect_get_known_supersets(self, value: fabll.NodeT) -> P_Set:
        lit = value.try_get_literal_subset()
        if lit is None:
            lit = value.domain_set()
        return as_lit(lit)

    @override
    def simplify(self, *gs: fabll.Graph | fabll.Node):
        pass
