# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.symbolic.invariants import AliasClass
from faebryk.libs.util import OrderedSet, partition

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


@dataclass
class _FlattenAssociativeResult:
    extracted_operands: list[F.Parameters.can_be_operand]
    """
    Extracted operands
    """
    destroyed_operations: OrderedSet[F.Expressions.is_expression]
    """
    ParameterOperables that got flattened and thus are not used anymore
    """


def _flatten_associative(
    mutator: Mutator,
    to_flatten: F.Expressions.is_flattenable,
):
    """
    Recursively extract operands from nested expressions of the same type.

    ```
    (A + B) + C + (D + E)
    Y    Z   X    W
    flatten(Z) -> flatten(Y) + [C] + flatten(X)
    flatten(Y) -> [A, B]
    flatten(X) -> flatten(W) + [D, E]
    flatten(W) -> [C]
    -> [A, B, C, D, E] = extracted operands
    -> {Z, X, W, Y} = destroyed operations
    ```

    Note: `W` flattens only for right associative operations

    Args:
    - check_destructable(expr, parent_expr): function to check if an expression is
        allowed to be flattened (=destructed)
    """

    out = _FlattenAssociativeResult(
        extracted_operands=[],
        destroyed_operations=OrderedSet(),
    )

    to_flatten_expr = to_flatten.get_sibling_trait(F.Expressions.is_expression)
    is_associative = bool(
        to_flatten.try_get_sibling_trait(F.Expressions.is_associative)
    )
    to_flatten_obj = fabll.Traits(to_flatten).get_obj_raw()

    def can_be_flattened(
        o: F.Parameters.can_be_operand,
    ) -> bool:
        if not is_associative:
            if not to_flatten_expr.get_operands()[0].is_same(o):
                return False
        if not fabll.Traits(o).get_obj_raw().has_same_type_as(to_flatten_obj):
            return False
        o_po = o.as_parameter_operatable.force_get()
        if mutator.has_been_mutated(o_po):
            return False
        if len(o.get_operations()) > 1:
            return False
        return True

    non_compressible_operands, nested_compressible_operations = map(
        list,
        partition(
            can_be_flattened,
            to_flatten_expr.get_operands(),
        ),
    )
    out.extracted_operands.extend(non_compressible_operands)

    nested_extracted_operands = []
    for nested_to_flatten in nested_compressible_operations:
        nested_to_flatten_po = nested_to_flatten.as_parameter_operatable.force_get()
        nested_to_flatten_expr = nested_to_flatten_po.as_expression.force_get()
        nested_to_flatten_fl = nested_to_flatten.get_sibling_trait(
            F.Expressions.is_flattenable
        )

        out.destroyed_operations.add(nested_to_flatten_expr)

        # recursive flatten
        res = _flatten_associative(mutator, nested_to_flatten_fl)
        nested_extracted_operands += res.extracted_operands
        out.destroyed_operations.update(res.destroyed_operations)

    out.extracted_operands.extend(nested_extracted_operands)

    return out


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
        sort_by_depth=True, required_traits=(F.Expressions.is_flattenable,)
    )

    def _involved_in_expr_with_same_type(e: F.Expressions.is_expression) -> bool:
        return e.get_obj_type_node() in {
            n.get_type_node() for n in e.as_parameter_operatable.get().get_operations()
        }

    # get out deepest expr in compressable tree
    root_ops = [e for e in ops if not _involved_in_expr_with_same_type(e)]

    for expr in root_ops:
        # Skip expressions that were removed or mutated by a previous iteration
        expr_po = expr.as_parameter_operatable.get()
        if mutator.is_removed(expr_po) or mutator.has_been_mutated(expr_po):
            continue

        expr_flat = expr.get_sibling_trait(F.Expressions.is_flattenable)
        res = _flatten_associative(mutator, expr_flat)
        if not res.destroyed_operations:
            continue

        mutator.remove(
            *[e.as_parameter_operatable.get() for e in res.destroyed_operations]
        )

        mutator.mutate_expression(
            expr,
            operands=res.extracted_operands,
        )
