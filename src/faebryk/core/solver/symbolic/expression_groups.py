# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging

import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.libs.util import unique

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
        sort_by_depth=True, required_traits=(F.Expressions.is_reflexive,)
    )
    for pred in predicates:
        if not pred.as_parameter_operatable().get_operations():
            continue
        operands = pred.get_operands()
        if operands[0].try_get_sibling_trait(F.Literals.is_literal):
            continue
        if operands[0] is not operands[1]:
            continue

        mutator.utils.alias_is_literal_and_check_predicate_eval(
            pred, mutator.make_lit(True)
        )


@algorithm("Idempotent deduplicate", terminal=False)
def idempotent_deduplicate(mutator: Mutator):
    """
    Or(A, A, B) -> Or(A, B)
    Union(A, A, B) -> Union(A, B)
    Intersection(A, A, B) -> Intersection(A, B)
    """

    exprs = mutator.get_expressions(
        sort_by_depth=True, required_traits=(F.Expressions.has_idempotent_operands,)
    )
    for expr in exprs:
        unique_operands = unique(expr.get_operands(), key=lambda x: x)
        if len(unique_operands) != len(expr.get_operands()):
            mutator.mutate_expression(expr, operands=unique_operands)


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
        mutator.mutate_unpack_expression(expr)


@algorithm("Unary identity unpack", terminal=False)
def unary_identity_unpack(mutator: Mutator):
    """
    E(A), A not lit -> A
    E(A), A lit -> E alias A
    for E in [Add, Multiply, Or, Union, Intersection]
    """

    exprs = mutator.get_expressions(
        sort_by_depth=True, required_traits=(F.Expressions.has_unary_identity,)
    )
    for expr in exprs:
        if len(expr.get_operands()) != 1:
            continue
        inner = expr.get_operands()[0]
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
        sort_by_depth=True, required_traits=(F.Expressions.is_involutory,)
    )
    for expr in exprs:
        if len(expr.get_operands()) != 1:
            continue
        inner = expr.get_operands()[0]
        if inner.get_obj_type_node() != expr.get_obj_type_node():
            continue
        innest = inner.get_sibling_trait(F.Expressions.is_expression).get_operands()[0]
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
    ops = mutator.get_expressions(
        sort_by_depth=True, required_traits=(F.Expressions.is_fully_associative,)
    )
    # get out deepest expr in compressable tree
    root_ops = [
        e
        for e in ops
        if e.get_obj_type_node()
        not in {n.get_type_node() for n in e.as_parameter_operatable().get_operations()}
    ]

    def is_replacable(
        to_replace: F.Expressions.is_expression,
        parent_expr: F.Expressions.is_expression,
    ) -> bool:
        """
        Check if an expression can be replaced.
        Only possible if not in use somewhere else or already mapped to new expr
        """
        # overly restrictive: equivalent replacement would be ok
        if mutator.has_been_mutated(to_replace.as_parameter_operatable()):
            return False
        if to_replace.as_parameter_operatable().get_operations() != {
            parent_expr.as_parameter_operatable()
        }:
            return False
        return True

    for expr in root_ops:
        res = mutator.utils.flatten_associative(expr, is_replacable)
        if not res.destroyed_operations:
            continue

        mutator.remove(*[e.as_parameter_operatable() for e in res.destroyed_operations])

        mutator.mutate_expression(
            expr,
            operands=res.extracted_operands,
        )
