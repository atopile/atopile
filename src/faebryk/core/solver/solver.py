# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from faebryk.core.graph import Graph
from faebryk.core.parameter import (
    Expression,
    ParameterOperatable,
    Predicate,
)
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint
from faebryk.libs.sets.sets import P_Set

logger = logging.getLogger(__name__)


class Solver(Protocol):
    # TODO booleanlike is very permissive
    type PredicateWithInfo[ArgType] = tuple[ParameterOperatable.BooleanLike, ArgType]

    class SolverError(Exception): ...

    class TimeoutError(SolverError): ...

    class DivisionByZeroError(SolverError): ...

    @dataclass
    class SolveResult:
        timed_out: bool

    @dataclass
    class SolveResultAny[ArgType](SolveResult):
        true_predicates: list["Solver.PredicateWithInfo[ArgType]"]
        false_predicates: list["Solver.PredicateWithInfo[ArgType]"]
        unknown_predicates: list["Solver.PredicateWithInfo[ArgType]"]

    @dataclass
    class SolveResultAll(SolveResult):
        has_solution: bool

    # timeout per solve call in milliseconds
    timeout: int
    # threads: int
    # in megabytes
    # memory: int

    def get_any_single(
        self,
        operatable: ParameterOperatable,
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Any:
        """
        Solve for a single value for the given expression.

        Args:
            operatable: The expression or parameter to solve.
            suppose_constraint: An optional constraint that can be added to make solving
                                easier. It is only in effect for the duration of the
                                solve call.
            minimize: An optional expression to minimize while solving.
            lock: If True, ensure the result is part of the solution set of
                              the expression.

        Returns:
            A SolveResultSingle object containing the chosen value.
        """
        ...

    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> SolveResultAny[ArgType]:
        """
        Make at least one of the passed predicates true, unless that is impossible.

        Args:
            predicates: A list of predicates to solve.
            suppose_constraint: An optional constraint that can be added to make solving
                                easier. It is only in effect for the duration of the
                                solve call.
            minimize: An optional expression to minimize while solving.
            lock: If True, add the solutions as constraints.

        Returns:
            A SolveResult object containing the true, false, and unknown predicates.

        Note:
            There is no specific order in which the predicates are solved.
        """
        ...

    # run deferred work
    def find_and_lock_solution(self, G: Graph) -> SolveResultAll: ...

    def inspect_known_min(
        self, value: ParameterOperatable.NumberLike
    ) -> ParameterOperatable.Number: ...

    def inspect_known_max(
        self, value: ParameterOperatable.NumberLike
    ) -> ParameterOperatable.Number: ...

    def inspect_known_values(
        self, value: ParameterOperatable.BooleanLike
    ) -> P_Set[bool]: ...

    # Could be exponentially many
    def inspect_known_supersets_are_few(
        self, value: ParameterOperatable.Sets
    ) -> bool: ...

    def inspect_get_known_supersets(
        self, value: ParameterOperatable.Sets
    ) -> Iterable[P_Set]: ...

    def inspect_get_known_superranges(
        self, value: ParameterOperatable.NumberLike
    ) -> Quantity_Interval_Disjoint: ...
