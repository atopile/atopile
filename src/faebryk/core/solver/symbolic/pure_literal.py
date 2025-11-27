# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import functools
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator

logger = logging.getLogger(__name__)


@dataclass
class _Multi:
    f: Callable[..., Any]
    init: F.Literals.LiteralValues | None = None

    def run(self, mutator: Mutator, *args: F.Literals.is_literal) -> Any:
        if self.init is not None:
            init_lit = F.Literals.make_lit(mutator.G_in, mutator.tg_in, self.init).get_trait(
                F.Literals.is_literal
            )
            args = (init_lit, init_lit, *args)
        return functools.reduce(self.f, args)


# TODO consider making this a trait instead

# FIXME: the function take a bad mix of literalnodes and is_literal
_CanonicalExpressions: dict[type[fabll.NodeT], _Multi] = {
    F.Expressions.Add: _Multi(F.Literals.Numbers.op_add_intervals, 0),
    F.Expressions.Multiply: _Multi(F.Literals.Numbers.op_mul_intervals, 1),
    F.Expressions.Power: _Multi(F.Literals.Numbers.op_pow_intervals),
    F.Expressions.Round: _Multi(F.Literals.Numbers.op_round),
    F.Expressions.Abs: _Multi(F.Literals.Numbers.op_abs),
    F.Expressions.Sin: _Multi(F.Literals.Numbers.op_sin),
    F.Expressions.Log: _Multi(F.Literals.Numbers.op_log),
    F.Expressions.Or: _Multi(F.Literals.Booleans.op_or, False),
    F.Expressions.Not: _Multi(F.Literals.Booleans.op_not),
    F.Expressions.Intersection: _Multi(F.Literals.is_literal.op_intersect_intervals),
    F.Expressions.Union: _Multi(F.Literals.is_literal.op_union_intervals),
    F.Expressions.SymmetricDifference: _Multi(
        F.Literals.is_literal.op_symmetric_difference_intervals
    ),
    F.Expressions.Is: _Multi(F.Literals.is_literal.op_is_equal),
    F.Expressions.GreaterOrEqual: _Multi(F.Literals.Numbers.op_greater_or_equal),
    F.Expressions.GreaterThan: _Multi(F.Literals.Numbers.op_greater_than),
    F.Expressions.IsSubset: _Multi(F.Literals.is_literal.is_subset_of),
    F.Expressions.IsBitSet: _Multi(F.Literals.Numbers.op_is_bit_set),
}

# Pure literal folding -----------------------------------------------------------------


def _exec_pure_literal_operands(
    mutator: Mutator,
    expr_type: "fabll.ImplementsType",
    operands: Iterable[F.Parameters.can_be_operand],
) -> F.Literals.is_literal | None:
    operands = list(operands)
    _map = {
        k.bind_typegraph(expr_type.tg).get_or_create_type().node(): v
        for k, v in _CanonicalExpressions.items()
    }
    expr_type_node = fabll.Traits(expr_type).get_obj_raw().get_type_node()
    if expr_type_node not in _map:
        return None
    if not all(o.has_trait(F.Literals.is_literal) for o in operands):
        return None
    try:
        return _map[expr_type_node].run(mutator, *operands)
    except (ValueError, NotImplementedError, ZeroDivisionError):
        return None


def _exec_pure_literal_expressions(
    mutator: Mutator,
    expr: F.Expressions.is_expression,
) -> F.Literals.is_literal | None:
    return _exec_pure_literal_operands(
        mutator,
        fabll.Traits(expr).get_obj_raw().get_trait(fabll.ImplementsType),
        # FIXME: there is no guarantee that this will return them in the correct order
        expr.get_operands(),
    )


@algorithm("Fold pure literal expressions", terminal=False)
def fold_pure_literal_expressions(mutator: Mutator):
    exprs = mutator.get_typed_expressions(
        sort_by_depth=True, required_traits=(F.Expressions.is_canonical,)
    )

    for expr in exprs:
        expr_t_po = expr.get_trait(F.Parameters.is_parameter_operatable)
        # TODO is this needed?
        if mutator.has_been_mutated(expr_t_po) or mutator.is_removed(expr_t_po):
            continue

        # if expression is not evaluatable that's fine
        # just means we can't say anything about the result
        result = _exec_pure_literal_expressions(
            mutator, expr.get_trait(F.Expressions.is_expression)
        )
        if result is None:
            continue
        # type ignore because function sig is not 100% correct
        mutator.utils.alias_is_literal_and_check_predicate_eval(expr, result)  # type: ignore
