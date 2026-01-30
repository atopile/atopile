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
        F.Expressions.Or,  # TODO: just squash these instead
    ]


@algorithm("Associative fold", terminal=False)
def associative_fold(mutator: Mutator):
    """
    Add(Add(A, B), Z) -> Add(A, B, Z)

    The inner expression must be the sole such expression in its class.
    """
    for expr_t in _get_associative_expr_types():
        for expr in mutator.get_typed_expressions(expr_t):
            is_expr = expr.is_expression.get()

            expansions = {
                non_lit: list(nested_expr.get_operands())
                for non_lit in is_expr.get_operand_operatables()
                if len(
                    class_exprs := AliasClass.of(
                        non_lit.as_operand.get()
                    ).get_with_trait(F.Expressions.is_expression)
                )
                == 1
                and (nested_expr := next(iter(class_exprs))).expr_isinstance(expr_t)
            }

            if not expansions:
                continue

            # preserves operand order
            new_ops: list[F.Parameters.can_be_operand] = []
            for op in is_expr.get_operands():
                po = op.as_parameter_operatable.try_get()
                if po is not None and po in expansions:
                    new_ops.extend(expansions[po])
                else:
                    new_ops.append(op)

            mutator.mutate_expression(is_expr, operands=new_ops)
