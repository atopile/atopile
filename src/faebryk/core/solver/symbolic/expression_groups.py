# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from typing import cast

import faebryk.core.node as fabll
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.library.Expressions import (
    has_idempotent_operands,
    has_unary_identity,
    is_fully_associative,
    is_idempotent,
    is_involutory,
    is_reflexive,
)
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

    predicates = mutator.get_expressions(
        sort_by_depth=True, required_traits=(is_reflexive,)
    )
    for pred in predicates:
        if not pred.operatable_operands:
            continue
        if not fabll.isparameteroperable(pred.operands[0]):
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

    exprs = mutator.get_expressions(
        sort_by_depth=True, required_traits=(has_idempotent_operands,)
    )
    for expr in exprs:
        unique_operands = unique(expr.operands, key=lambda x: x)
        if len(unique_operands) != len(expr.operands):
            mutator.mutate_expression(expr, operands=unique_operands)


@algorithm("Idempotent unpack", terminal=False)
def idempotent_unpack(mutator: Mutator):
    """
    Abs(Abs(A)) -> Abs(A)
    """

    exprs = mutator.get_expressions(
        sort_by_depth=True, required_traits=(is_idempotent,)
    )
    for expr in exprs:
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

    exprs = mutator.get_expressions(
        sort_by_depth=True, required_traits=(has_unary_identity,)
    )
    for expr in exprs:
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

    exprs = mutator.get_expressions(
        sort_by_depth=True, required_traits=(is_involutory,)
    )
    for expr in exprs:
        if len(expr.operands) != 1:
            continue
        inner = expr.operands[0]
        if type(inner) is not type(expr):
            continue
        assert Expressions.isinstance_node(inner, type(expr))
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
        list[fabll.Node],
        mutator.get_expressions(
            sort_by_depth=True, required_traits=(is_fully_associative,)
        ),
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
