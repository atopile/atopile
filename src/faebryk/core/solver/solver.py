# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Any, Protocol

import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import ConfigFlag

logger = logging.getLogger(__name__)

LOG_PICK_SOLVE = ConfigFlag("LOG_PICK_SOLVE", False)


class NotDeducibleException(Exception):
    def __init__(
        self,
        predicate: F.Expressions.IsConstrainable,
        not_deduced: list[F.Expressions.IsConstrained],
    ):
        self.predicate = predicate
        self.not_deduced = not_deduced

    def __str__(self):
        return f"Could not deduce predicate: {self.predicate}"


class Solver(Protocol):
    def get_any_single(
        self,
        operatable: F.Parameters.is_parameter,
        lock: bool,
        suppose_constraint: F.Expressions.IsConstrained | None = None,
        minimize: F.Expressions.is_expression | None = None,
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
        predicate: F.Expressions.IsConstrainable,
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

    def inspect_get_known_supersets(
        self, value: F.Parameters.is_parameter
    ) -> F.Literals.is_literal: ...

    def update_superset_cache(self, *nodes: fabll.Node): ...

    def simplify(self, *gs: graph.GraphView | fabll.Node): ...
