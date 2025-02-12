from typing import Any

from faebryk.core.cpp import Graph
from faebryk.core.parameter import Expression, Parameter, Predicate
from faebryk.core.solver.solver import Solver
from faebryk.libs.sets.sets import P_Set


class SuperSuperSet(P_Set):
    """Is a superset of anything"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    def is_superset_of(self, other: P_Set) -> bool:
        return True

    def is_empty(self) -> bool:
        return False

    def is_finite(self) -> bool:
        return False

    def __contains__(self, item: Any) -> bool:
        return True

    def __and__(self, other: P_Set) -> P_Set:
        return other

    def is_single_element(self) -> bool:
        return False

    def any(self) -> Any:
        return None

    def serialize_pset(self) -> dict:
        return {}

    @classmethod
    def deserialize_pset(cls, data: dict) -> "P_Set":
        return SuperSuperSet()


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
            true_predicates=predicates,
            false_predicates=[],
            unknown_predicates=[],
        )

    def find_and_lock_solution(self, G: Graph) -> Solver.SolveResultAll:
        return Solver.SolveResultAll(timed_out=False, has_solution=False)

    def inspect_get_known_supersets(
        self, value: Parameter, force_update: bool = True
    ) -> P_Set:
        try:
            return value.domain.unbounded(value)
        except NotImplementedError:
            return value.try_get_literal() or SuperSuperSet()
