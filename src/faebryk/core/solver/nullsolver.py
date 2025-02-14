from types import SimpleNamespace
from typing import Any

from faebryk.core.cpp import Graph
from faebryk.core.parameter import Expression, Parameter, Predicate
from faebryk.core.solver import canonical
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.solver import Solver
from faebryk.libs.sets.sets import P_Set


class NullSolver(DefaultSolver):
    algorithms = SimpleNamespace(
        pre=[canonical.convert_to_canonical_literals], iterative=[]
    )

    _superset_cache: dict[Parameter, P_Set] = {}

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
        self, param: Parameter, force_update: bool = True
    ) -> P_Set:
        if param in self._superset_cache:
            return self._superset_cache[param]

        repr_map, _ = self.simplify_symbolically(param.get_graph())

        result = param.domain_set()
        if (
            param in repr_map.repr_map
            and (lit := repr_map.try_get_literal(param, allow_subset=True)) is not None
        ):
            result = P_Set.from_value(lit)

        self._superset_cache[param] = result
        return result
