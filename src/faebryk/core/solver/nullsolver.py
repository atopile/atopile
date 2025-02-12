from typing import Any

from faebryk.core.cpp import Graph
from faebryk.core.parameter import Expression, Parameter, Predicate
from faebryk.core.solver.solver import Solver
from faebryk.libs.sets.sets import P_Set


class NullSolver(Solver):
    def get_any_single(
        self,
        operatable: Parameter,
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Any:
        return None

    def assert_any_predicate(
        self,
        predicates: list[Solver.PredicateWithInfo],
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Solver.SolveResultAny:
        return Solver.SolveResultAny(
            timed_out=False,
            true_predicates=[],
            false_predicates=[],
            unknown_predicates=predicates,
        )

    def find_and_lock_solution(self, G: Graph) -> Solver.SolveResultAll:
        return Solver.SolveResultAll(timed_out=False, has_solution=False)

    def inspect_get_known_supersets(
        self, value: Parameter, force_update: bool = True
    ) -> P_Set:
        return value.domain.unbounded(value)
