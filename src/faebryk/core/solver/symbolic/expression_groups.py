# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from functools import partial
from typing import cast

from faebryk.core.parameter import (
    ConstrainableExpression,
    IdempotentExpression,
    IdempotentOperands,
    Involutory,
    ParameterOperatable,
    Reflexive,
    UnaryIdentity,
)
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    FullyAssociative,
    algorithm,
    alias_is_literal,
    alias_is_literal_and_check_predicate_eval,
    flatten_associative,
    is_literal,
    is_replacable,
)
from faebryk.libs.util import (
    unique,
)

logger = logging.getLogger(__name__)


@algorithm("Reflexive predicates")
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

        alias_is_literal_and_check_predicate_eval(pred, True, mutator)


@algorithm("Idempotent deduplicate")
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


@algorithm("Idempotent unpack")
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


@algorithm("Unary identity unpack")
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
        if is_literal(inner):
            alias_is_literal(expr, inner, mutator, terminate=True)
        else:
            mutator.mutate_unpack_expression(expr)


@algorithm("Involutory fold")
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
        if is_literal(innest):
            alias_is_literal(expr, innest, mutator, terminate=True)
        else:
            mutator.mutator_neutralize_expressions(expr)


@algorithm("Associative expressions Full")
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

    for expr in root_ops:
        res = flatten_associative(
            expr, partial(is_replacable, mutator.transformations.mutated)
        )
        if not res.destroyed_operations:
            continue

        mutator.remove(*res.destroyed_operations)

        mutator.mutate_expression(
            expr,
            operands=res.extracted_operands,
        )
