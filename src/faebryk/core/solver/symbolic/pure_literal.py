# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable, cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)


@dataclass
class _Multi:
    f: Callable[..., Any]
    default_arg: F.Literals.LiteralValues | None = None

    def run(
        self, *args: F.Literals.LiteralNodes, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> F.Literals.is_literal:
        if not args and self.default_arg is not None:
            init_lit = F.Literals.make_singleton(g, tg, self.default_arg)
            args = (init_lit,)

        out = self.f(*args, g=g, tg=tg)

        # TODO: remove hack for equals returning bool
        if isinstance(out, F.Literals.LiteralValues):
            out = F.Literals.make_singleton(g, tg, out)
        return out if isinstance(out, F.Literals.is_literal) else out.is_literal.get()


# TODO consider making this a trait instead

_CanonicalExpressions: dict[type[fabll.NodeT], _Multi] = {
    F.Expressions.Add: _Multi(F.Literals.Numbers.op_add_intervals, 0),
    F.Expressions.Subtract: _Multi(F.Literals.Numbers.op_subtract_intervals),
    F.Expressions.Multiply: _Multi(F.Literals.Numbers.op_mul_intervals, 1),
    F.Expressions.Divide: _Multi(F.Literals.Numbers.op_div_intervals),
    F.Expressions.Power: _Multi(F.Literals.Numbers.op_pow_intervals),
    F.Expressions.Sqrt: _Multi(F.Literals.Numbers.op_sqrt),
    F.Expressions.Round: _Multi(F.Literals.Numbers.op_round),
    F.Expressions.Abs: _Multi(F.Literals.Numbers.op_abs),
    F.Expressions.Sin: _Multi(F.Literals.Numbers.op_sin),
    F.Expressions.Log: _Multi(
        F.Literals.Numbers.op_log,
    ),
    F.Expressions.And: _Multi(F.Literals.Booleans.op_and, True),
    F.Expressions.Or: _Multi(F.Literals.Booleans.op_or, False),
    F.Expressions.Xor: _Multi(F.Literals.Booleans.op_xor),
    F.Expressions.Not: _Multi(F.Literals.Booleans.op_not),
    F.Expressions.Intersection: _Multi(F.Literals.is_literal.op_setic_intersect),
    F.Expressions.Union: _Multi(F.Literals.is_literal.op_setic_union),
    # TODO wtf
    F.Expressions.LessThan: _Multi(F.Literals.Numbers.op_mul_intervals),
    F.Expressions.GreaterThan: _Multi(F.Literals.Numbers.op_mul_intervals),
    #
    F.Expressions.Floor: _Multi(F.Literals.Numbers.op_floor),
    F.Expressions.Ceil: _Multi(F.Literals.Numbers.op_ceil),
    F.Expressions.Min: _Multi(F.Literals.Numbers.min_elem),
    F.Expressions.Max: _Multi(F.Literals.Numbers.max_elem),
    F.Expressions.SymmetricDifference: _Multi(
        F.Literals.is_literal.op_setic_symmetric_difference
    ),
    F.Expressions.GreaterOrEqual: _Multi(F.Literals.Numbers.op_greater_or_equal),
    F.Expressions.GreaterThan: _Multi(F.Literals.Numbers.op_greater_than),
    F.Expressions.Is: _Multi(F.Literals.is_literal.op_setic_equals),
    F.Expressions.IsSubset: _Multi(F.Literals.is_literal.op_setic_is_subset_of),
    F.Expressions.IsBitSet: _Multi(F.Literals.Numbers.op_is_bit_set),
}

# Pure literal folding -----------------------------------------------------------------


def _get_type(expr_type: "fabll.ImplementsType | type[fabll.NodeT]") -> _Multi | None:
    if isinstance(expr_type, type):
        return _CanonicalExpressions[expr_type]
    else:
        _map = {
            fabll.TypeNodeBoundTG.get_or_create_type_in_tg(expr_type.tg, k)
            .node()
            .get_uuid(): v
            for k, v in _CanonicalExpressions.items()
        }
        expr_type_node = fabll.Traits(expr_type).get_obj_raw().instance.node()
        if expr_type_node.get_uuid() not in _map:
            return None
        return _map[expr_type_node.get_uuid()]


def exec_pure_literal_operands(
    g: graph.GraphView,
    tg: fbrk.TypeGraph,
    expr_type: "fabll.ImplementsType | type[fabll.NodeT]",
    operands: Iterable[F.Parameters.can_be_operand],
) -> F.Literals.is_literal | None:
    operands = list(operands)
    expr_type_ = _get_type(expr_type)
    if expr_type_ is None:
        return None

    lits = [o.as_literal.try_get() for o in operands]
    if not all(lits):
        return None
    lits = cast(list[F.Literals.is_literal], lits)
    lits_nodes = [o.switch_cast() for o in lits]
    try:
        return expr_type_.run(g=g, tg=tg, *lits_nodes)
    except (ValueError, NotImplementedError, ZeroDivisionError, TypeError):
        return None


def exec_pure_literal_expression(
    g: graph.GraphView,
    tg: fbrk.TypeGraph,
    expr: F.Expressions.is_expression,
) -> F.Literals.is_literal | None:
    expr_type = not_none(
        fabll.TypeNodeBoundTG.try_get_trait_of_type(
            fabll.ImplementsType,
            not_none(fabll.Traits(expr).get_obj_raw().get_type_node()),
        )
    )
    return exec_pure_literal_operands(g, tg, expr_type, expr.get_operands())
