# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.symbolic.invariants import AliasClass
from faebryk.libs.util import once

logger = logging.getLogger(__name__)


@algorithm("Idempotent unpack", terminal=False)
def idempotent_unpack(mutator: Mutator):
    """
    Abs(Abs(A)) -> Abs(A)
    """

    exprs = mutator.get_expressions(required_traits=(F.Expressions.is_idempotent,))
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

    exprs = mutator.get_expressions(required_traits=(F.Expressions.has_unary_identity,))
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

    exprs = mutator.get_expressions(required_traits=(F.Expressions.is_involutory,))
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


@once
def _get_associative_expr_types() -> list[type[F.Expressions.ExpressionNodes]]:
    # TODO: dynamic
    # all types in typegraph that have a is_associative MakeChild
    return [
        F.Expressions.Add,
        F.Expressions.Multiply,
        F.Expressions.Or,
    ]


@algorithm("Associative fold", terminal=False)
def associative_fold(mutator: Mutator):
    """
    Add(Add(A, B), Z) -> Add(A, B, Z)

    The inner expression must be the sole member of its class.
    """
    for expr_t in _get_associative_expr_types():
        for expr in mutator.get_typed_expressions(expr_t):
            is_expr = expr.is_expression.get()

            non_lit_ops = is_expr.get_operand_operatables()
            if len(non_lit_ops) != 1:
                continue

            non_lit = next(iter(non_lit_ops))
            non_lit_op = non_lit.as_operand.get()

            # class must contain a single expr
            class_exprs = AliasClass.of(non_lit_op).get_with_trait(
                F.Expressions.is_expression
            )
            if len(class_exprs) != 1:
                continue

            # and that expr must be of type expr_t
            nested_expr = next(iter(class_exprs))
            if not nested_expr.expr_isinstance(expr_t):
                continue

            # preserves operand order
            new_ops = []
            for op in is_expr.get_operands():
                if op.is_same(non_lit_op):
                    new_ops.extend(nested_expr.get_operands())
                else:
                    new_ops.append(op)

            new_expr = mutator.create_check_and_insert_expression(expr_t, *new_ops)

            if new_expr.out:
                mutator.create_check_and_insert_expression(
                    F.Expressions.Is,
                    new_expr.out.as_operand.get(),
                    expr.can_be_operand.get(),
                    assert_=True,
                )
