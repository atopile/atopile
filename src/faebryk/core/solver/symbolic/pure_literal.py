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
    IsBitSet,
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
    SolverAll,
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
    IsBitSet: Quantity_Interval_Disjoint.op_is_bit_set,
}

# Pure literal folding -----------------------------------------------------------------


def _exec_pure_literal_operands(
    expr_type: type[CanonicalExpression], operands: Iterable[SolverAll]
) -> SolverLiteral | None:
    operands = list(operands)
    if expr_type not in _CanonicalExpressions:
        return None
    if not all(MutatorUtils.is_literal(o) for o in operands):
        return None
    try:
        return _CanonicalExpressions[expr_type](*operands)
    except (ValueError, NotImplementedError, ZeroDivisionError):
        return None


def _exec_pure_literal_expressions(expr: CanonicalExpression) -> SolverLiteral | None:
    return _exec_pure_literal_operands(type(expr), expr.operands)


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

        # if expression is not evaluatable that's fine
        # just means we can't say anything about the result
        result = _exec_pure_literal_expressions(expr)
        if result is None:
            continue
        # type ignore because function sig is not 100% correct
        mutator.utils.alias_is_literal_and_check_predicate_eval(expr, result)  # type: ignore
