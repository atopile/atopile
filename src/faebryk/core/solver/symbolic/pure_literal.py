# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import functools
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable, cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)


@dataclass
class _Multi:
    f: Callable[..., Any]
    init: F.Literals.LiteralValues | None = None

    def run(
        self, *args: F.Literals.LiteralNodes, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> F.Literals.is_literal:
        if self.init is not None:
            init_lit = F.Literals.make_simple_lit_singleton(g, tg, self.init)
            args = (init_lit, init_lit, *args)

        def _f(
            *args: F.Literals.LiteralNodes,
        ) -> F.Literals.LiteralNodes | F.Literals.is_literal | bool:
            return self.f(*args, g=g, tg=tg)

        out = functools.reduce(
            _f,  # type: ignore # some function return is_literal/bool but its ok
            args,
        )
        # TODO: remove hack for equals returning bool
        if isinstance(out, F.Literals.LiteralValues):
            out = F.Literals.make_simple_lit_singleton(g, tg, out)
        return out if isinstance(out, F.Literals.is_literal) else out.is_literal.get()


# TODO consider making this a trait instead

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
    F.Expressions.Is: _Multi(F.Literals.is_literal.equals),
    F.Expressions.GreaterOrEqual: _Multi(F.Literals.Numbers.op_greater_or_equal),
    F.Expressions.GreaterThan: _Multi(F.Literals.Numbers.op_greater_than),
    F.Expressions.IsSubset: _Multi(F.Literals.is_literal.is_subset_of),
    F.Expressions.IsBitSet: _Multi(F.Literals.Numbers.op_is_bit_set),
}

# Pure literal folding -----------------------------------------------------------------


def _exec_pure_literal_operands(
    g: graph.GraphView,
    tg: fbrk.TypeGraph,
    expr_type: "fabll.ImplementsType",
    operands: Iterable[F.Parameters.can_be_operand],
) -> F.Literals.is_literal | None:
    operands = list(operands)
    _map = {
        k.bind_typegraph(expr_type.tg).get_or_create_type().node().get_uuid(): v
        for k, v in _CanonicalExpressions.items()
    }
    expr_type_node = fabll.Traits(expr_type).get_obj_raw().instance.node()
    if expr_type_node.get_uuid() not in _map:
        return None
    lits = [o.try_get_sibling_trait(F.Literals.is_literal) for o in operands]
    if not all(lits):
        return None
    lits = cast(list[F.Literals.is_literal], lits)
    lits_nodes = [o.switch_cast() for o in lits]
    try:
        return _map[expr_type_node.get_uuid()].run(g=g, tg=tg, *lits_nodes)
    except (ValueError, NotImplementedError, ZeroDivisionError):
        return None


def _exec_pure_literal_expressions(
    g: graph.GraphView,
    tg: fbrk.TypeGraph,
    expr: F.Expressions.is_expression,
) -> F.Literals.is_literal | None:
    return _exec_pure_literal_operands(
        g,
        tg,
        not_none(
            fabll.TypeNodeBoundTG.try_get_trait_of_type(
                fabll.ImplementsType,
                not_none(fabll.Traits(expr).get_obj_raw().get_type_node()),
            )
        ),
        # FIXME: there is no guarantee that this will return them in the correct order
        expr.get_operands(),
    )


@algorithm("Fold pure literal expressions", terminal=False)
def fold_pure_literal_expressions(mutator: Mutator):
    exprs = mutator.get_expressions(sort_by_depth=True)

    for expr in exprs:
        expr_po = expr.get_sibling_trait(F.Parameters.is_parameter_operatable)
        # TODO is this needed?
        if mutator.has_been_mutated(expr_po) or mutator.is_removed(expr_po):
            continue

        # if expression is not evaluatable that's fine
        # just means we can't say anything about the result
        result = _exec_pure_literal_expressions(
            mutator.G_transient,
            mutator.tg_in,
            expr,
        )
        if result is None:
            continue
        mutator.utils.alias_is_literal_and_check_predicate_eval(expr, result)


def test_fold_simple_literal_expressions_single():
    """Test that Add(1, 2) folds to 3."""
    from faebryk.core.solver.mutator import MutationMap

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    E = BoundExpressions(g=g, tg=tg)
    expr = E.add(E.lit_op_single(1.0), E.lit_op_single(2.0))

    mut_map = MutationMap.bootstrap(tg=tg, g=g)
    mutator0 = Mutator(
        mutation_map=mut_map,
        algo=fold_pure_literal_expressions,
        iteration=0,
        terminal=True,
    )
    res0 = mutator0.run()
    res0.mutation_stage.print_mutation_table()
    mut_map = mut_map.extend(res0.mutation_stage)

    lit = not_none(
        (
            mut_map.try_get_literal(
                expr.get_sibling_trait(F.Parameters.is_parameter_operatable)
            )
        )
    )
    assert lit.equals_singleton(3.0)


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    typer.run(test_fold_simple_literal_expressions_single)
