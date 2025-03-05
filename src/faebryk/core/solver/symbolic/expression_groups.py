# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from typing import cast

from faebryk.core.parameter import (
    ConstrainableExpression,
    Expression,
    IdempotentExpression,
    IdempotentOperands,
    Involutory,
    ParameterOperatable,
    Reflexive,
    UnaryIdentity,
)
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import FullyAssociative
from faebryk.libs.util import (
    unique,
)

logger = logging.getLogger(__name__)


@algorithm("Reflexive predicates", terminal=False)
def reflexive_predicates(mutator: Mutator):
    """
    A not lit (done by literal_folding)
    A is A -> True
    A ss A -> True
    A >= A -> True
    """

    predicates = mutator.nodes_of_types(Reflexive, sort_by_depth=True)
    for pred in predicates:
        assert isinstance(pred, ConstrainableExpression)
        if not pred.operatable_operands:
            continue
        if not isinstance(pred.operands[0], ParameterOperatable):
            continue
        if pred.operands[0] is not pred.operands[1]:
            continue

        mutator.utils.alias_is_literal_and_check_predicate_eval(pred, True)


@algorithm("Idempotent deduplicate", terminal=False)
def idempotent_deduplicate(mutator: Mutator):
    """
    Or(A, A, B) -> Or(A, B)
    Union(A, A, B) -> Union(A, B)
    Intersection(A, A, B) -> Intersection(A, B)
    """

    exprs = mutator.nodes_of_types(IdempotentOperands, sort_by_depth=True)
    for expr in exprs:
        assert isinstance(expr, IdempotentOperands)
        unique_operands = unique(expr.operands, key=lambda x: x)
        if len(unique_operands) != len(expr.operands):
            mutator.mutate_expression(expr, operands=unique_operands)


@algorithm("Idempotent unpack", terminal=False)
def idempotent_unpack(mutator: Mutator):
    """
    Abs(Abs(A)) -> Abs(A)
    """

    exprs = mutator.nodes_of_types(IdempotentExpression, sort_by_depth=True)
    for expr in exprs:
        assert isinstance(expr, IdempotentExpression)
        assert len(expr.operands) == 1
        inner = expr.operands[0]
        if type(inner) is not type(expr):
            continue
        mutator.mutate_unpack_expression(expr)


@algorithm("Unary identity unpack", terminal=False)
def unary_identity_unpack(mutator: Mutator):
    """
    E(A), A not lit -> A
    E(A), A lit -> E alias A
    for E in [Add, Multiply, Or, Union, Intersection]
    """

    exprs = mutator.nodes_of_types(UnaryIdentity, sort_by_depth=True)
    for expr in exprs:
        assert isinstance(expr, UnaryIdentity)
        if len(expr.operands) != 1:
            continue
        inner = expr.operands[0]
        if mutator.utils.is_literal(inner):
            mutator.utils.alias_to(expr, inner, terminate=True)
        else:
            mutator.mutate_unpack_expression(expr)


@algorithm("Involutory fold", terminal=False)
def involutory_fold(mutator: Mutator):
    """
    Not(Not(A)) -> A
    """

    exprs = mutator.nodes_of_type(Involutory, sort_by_depth=True)
    for expr in exprs:
        assert isinstance(expr, Involutory)
        if len(expr.operands) != 1:
            continue
        inner = expr.operands[0]
        if type(inner) is not type(expr):
            continue
        assert isinstance(inner, type(expr))
        innest = inner.operands[0]
        if mutator.utils.is_literal(innest):
            mutator.utils.alias_to(expr, innest, terminate=True)
        else:
            mutator.mutator_neutralize_expressions(expr)


@algorithm("Associative expressions", terminal=False)
def associative_flatten(mutator: Mutator):
    """
    Makes
    ```
    (A + B) + (C + (D + E))
       Y    Z    X    W
    -> +(A,B,C,D,E)
       Z'

    for +, *, and, or, &, |, ^
    """
    ops = cast(
        list[FullyAssociative],
        mutator.nodes_of_types(FullyAssociative, sort_by_depth=True),
    )
    # get out deepest expr in compressable tree
    root_ops = [e for e in ops if type(e) not in {type(n) for n in e.get_operations()}]

    def is_replacable(to_replace: Expression, parent_expr: Expression) -> bool:
        """
        Check if an expression can be replaced.
        Only possible if not in use somewhere else or already mapped to new expr
        """
        # overly restrictive: equivalent replacement would be ok
        if mutator.has_been_mutated(to_replace):
            return False
        if to_replace.get_operations() != {parent_expr}:
            return False
        return True

    for expr in root_ops:
        res = mutator.utils.flatten_associative(expr, is_replacable)
        if not res.destroyed_operations:
            continue

        mutator.remove(*res.destroyed_operations)

        mutator.mutate_expression(
            expr,
            operands=res.extracted_operands,
        )
