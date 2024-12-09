# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from faebryk.core.graph import Graph
from faebryk.core.parameter import (
    ConstrainableExpression,
    Expression,
    Parameter,
    Predicate,
)
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import ConfigFlag

logger = logging.getLogger(__name__)

LOG_PICK_SOLVE = ConfigFlag("LOG_PICK_SOLVE", False)


class Solver(Protocol):
    # TODO booleanlike is very permissive
    type PredicateWithInfo[ArgType] = tuple[ConstrainableExpression, ArgType]

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
        operatable: Parameter,
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

    def inspect_get_known_supersets(
        self, value: Parameter, force_update: bool = True
    ) -> P_Set: ...
