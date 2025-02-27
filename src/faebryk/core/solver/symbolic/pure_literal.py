# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import functools
import logging
import operator
from typing import Callable, Iterable, cast

from faebryk.core.parameter import (
    Abs,
    Add,
    GreaterOrEqual,
    GreaterThan,
    Intersection,
    Is,
    IsSubset,
    Log,
    Multiply,
    Not,
    Or,
    Power,
    Round,
    Sin,
    SymmetricDifference,
    Union,
)
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    CanonicalExpression,
    MutatorUtils,
    SolverLiteral,
    make_lit,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval_Disjoint,
)
from faebryk.libs.sets.sets import BoolSet, P_Set

logger = logging.getLogger(__name__)


def _multi(op: Callable, init=None) -> Callable:
    def wrapped(*args):
        if init is not None:
            init_lit = make_lit(init)
            args = [init_lit, init_lit, *args]
        assert args
        return functools.reduce(op, args)

    return wrapped


# TODO consider making the oprerator property of the expression type

_CanonicalExpressions = {
    Add: _multi(operator.add, 0),
    Multiply: _multi(operator.mul, 1),
    Power: operator.pow,
    Round: round,
    Abs: abs,
    Sin: Quantity_Interval_Disjoint.op_sin,
    Log: Quantity_Interval_Disjoint.op_log,
    Or: _multi(BoolSet.op_or, False),
    Not: BoolSet.op_not,
    Intersection: _multi(operator.and_),
    Union: _multi(operator.or_),
    SymmetricDifference: operator.xor,
    Is: operator.eq,
    GreaterOrEqual: operator.ge,
    GreaterThan: operator.gt,
    IsSubset: P_Set.is_subset_of,
}

# Pure literal folding -----------------------------------------------------------------


def _exec_pure_literal_expressions(expr: CanonicalExpression) -> SolverLiteral:
    assert MutatorUtils.is_pure_literal_expression(expr)
    return _CanonicalExpressions[type(expr)](*expr.operands)


@algorithm("Fold pure literal expressions", terminal=False)
def fold_pure_literal_expressions(mutator: Mutator):
    exprs = mutator.nodes_of_types(
        tuple(_CanonicalExpressions.keys()), sort_by_depth=True
    )
    exprs = cast(Iterable[CanonicalExpression], exprs)

    for expr in exprs:
        # TODO is this needed?
        if mutator.has_been_mutated(expr) or mutator.is_removed(expr):
            continue

        if not mutator.utils.is_pure_literal_expression(expr):
            continue

        # if expression is not evaluatable that's fine
        # just means we can't say anything about the result
        try:
            result = _exec_pure_literal_expressions(expr)
        except (ValueError, NotImplementedError, ZeroDivisionError):
            continue
        # type ignore because function sig is not 100% correct
        mutator.utils.alias_is_literal_and_check_predicate_eval(expr, result)  # type: ignore
