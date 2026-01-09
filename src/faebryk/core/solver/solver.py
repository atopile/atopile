# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Protocol

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.library._F as F
from faebryk.libs.util import ConfigFlag

logger = logging.getLogger(__name__)

LOG_PICK_SOLVE = ConfigFlag("LOG_PICK_SOLVE", False)


class NotDeducibleException(Exception):
    def __init__(
        self,
        predicate: F.Expressions.is_assertable,
        not_deduced: list[F.Expressions.is_predicate],
    ):
        self.predicate = predicate
        self.not_deduced = not_deduced

    def __str__(self):
        return f"Could not deduce predicate: {self.predicate}"


class Solver(Protocol):
    def extract_superset(
        self,
        value: F.Parameters.is_parameter,
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> F.Literals.is_literal: ...

    def simplify(
        self,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        terminal: bool = False,
        relevant: list[F.Parameters.can_be_operand] | None = None,
    ): ...

    def simplify_for(
        self,
        *ops: F.Parameters.can_be_operand,
        terminal: bool = False,
    ):
        g = ops[0].g
        tg = ops[0].tg
        relevant = list(ops)
        return self.simplify(
            g=g,
            tg=tg,
            terminal=terminal,
            relevant=relevant,
        )

    def simplify_and_extract_superset(
        self,
        value: F.Parameters.is_parameter,
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> F.Literals.is_literal:
        g = g or value.g
        tg = tg or value.tg
        self.simplify(g=g, tg=tg, terminal=False, relevant=[value.as_operand.get()])
        return self.extract_superset(value, g=g, tg=tg)
