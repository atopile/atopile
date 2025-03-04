# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Any, Protocol

from faebryk.core.graph import Graph
from faebryk.core.node import Node
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


class NotDeducibleException(Exception):
    def __init__(
        self,
        predicate: ConstrainableExpression,
        not_deduced: list[ConstrainableExpression],
    ):
        self.predicate = predicate
        self.not_deduced = not_deduced

    def __str__(self):
        return f"Could not deduce predicate: {self.predicate}"


class Solver(Protocol):
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

    def try_fulfill(
        self,
        predicate: ConstrainableExpression,
        lock: bool,
        allow_unknown: bool = False,
    ) -> bool:
        """
        Try to fulfill the predicate.

        Args:
            predicate: The predicate to fulfill.
            lock: If True, ensure the result is part of the solution set of
                  the expression.

        Returns:
            True if found definite answer, False if allow_unknown and e.g Timeout or
            no deduction possible
        Raises:
            TimeoutError if not allow_unknown and timeout
            Contradiction if predicate proved false
        """
        ...

    def inspect_get_known_supersets(self, value: Parameter) -> P_Set: ...

    def update_superset_cache(self, *nodes: Node): ...

    def simplify(self, *gs: Graph | Node): ...
