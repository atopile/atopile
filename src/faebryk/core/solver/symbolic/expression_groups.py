# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.symbolic.invariants import AliasClass

logger = logging.getLogger(__name__)


@algorithm("Idempotent unpack", terminal=False)
def idempotent_unpack(mutator: Mutator):
    """
    Abs(Abs(A)) -> Abs(A)
    """

    exprs = mutator.get_expressions(
        sort_by_depth=True, required_traits=(F.Expressions.is_idempotent,)
    )
    for expr in exprs:
        assert len(expr.get_operands()) == 1
        inner = expr.get_operands()[0]
        if inner.get_obj_type_node() != expr.get_type_node():
            continue
        mutator.utils.mutate_unpack_expression(expr)


@algorithm("Unary identity unpack", terminal=False)
def unary_identity_unpack(mutator: Mutator):
    """
    f(A), A not lit -> A (if lit handled by pure literal)
    for f in [Add, Multiply, Or, Union, Intersection]
    """

    exprs = mutator.get_expressions(
        sort_by_depth=True, required_traits=(F.Expressions.has_unary_identity,)
    )
    for expr in exprs:
        if len(expr.get_operands()) != 1:
            continue
        inner = expr.get_operands()[0]
        if mutator.utils.is_literal(inner):
            continue
        mutator.utils.mutate_unpack_expression(expr)


@algorithm("Involutory fold", terminal=False)
def involutory_fold(mutator: Mutator):
    """
    Not(Not(A)) -> A (a not lit, else pure + superset estimate)
    """

    exprs = mutator.get_expressions(
        sort_by_depth=True, required_traits=(F.Expressions.is_involutory,)
    )
    for expr in exprs:
        if len(expr.get_operands()) != 1:
            continue
        for inner in AliasClass.of(expr.get_operands()[0]).get_with_trait(
            F.Expressions.is_expression
        ):
            if (
                fabll.Traits(inner).get_obj_raw().get_type_node()
                != expr.get_obj_type_node()
            ):
                continue
            innest = inner.get_operands()[0]
            if mutator.utils.is_literal(innest):
                continue
            mutator.utils.mutator_neutralize_expressions(expr)
            break
