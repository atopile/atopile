from types import SimpleNamespace
from typing import Any

from faebryk.core.node import Node
from faebryk.core.parameter import Expression, Parameter, Predicate
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.symbolic import canonical
from faebryk.libs.sets.sets import P_Set


class NullSolver(DefaultSolver):
    algorithms = SimpleNamespace(
        pre=[
            canonical.convert_to_canonical_literals,
        ],
        iterative=[],
    )

    _superset_cache: dict[Parameter, P_Set] = {}
    _repr_map = None

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

    def update_superset_cache(self, *nodes: Node):
        pass

    def inspect_get_known_supersets(self, param: Parameter) -> P_Set:
        if param in self._superset_cache:
            return self._superset_cache[param]

        if self._repr_map is None:
            self._repr_map = self.simplify_symbolically(param).data.mutation_map

        lit = self._repr_map.try_get_literal(
            param, allow_subset=True, domain_default=True
        )
        assert lit is not None

        self._superset_cache[param] = lit
        return lit
