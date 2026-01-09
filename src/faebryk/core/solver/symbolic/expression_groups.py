# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from typing import Callable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import MutatorUtils
from faebryk.libs.util import partition, unique

logger = logging.getLogger(__name__)


@algorithm("Reflexive predicates", terminal=False)
def reflexive_predicates(mutator: Mutator):
    """
    A not lit (done by literal_folding)
    A is A -> True
    A ss A -> True
    A >= A -> True
    if predicate then terminate
    """

    reflexives_e = mutator.get_expressions(
        sort_by_depth=True, required_traits=(F.Expressions.is_reflexive,)
    )
    for reflexive_e in reflexives_e:
        if not reflexive_e.as_parameter_operatable.get().get_operations():
            continue
        operands = reflexive_e.get_operands()
        if operands[0].as_literal.try_get():
            continue
        if len(operands) >= 2 and operands[0] is not operands[1]:
            continue

        mutator.create_expression(
            F.Expressions.IsSubset,
            reflexive_e.as_operand.get(),
            mutator.make_singleton(True).can_be_operand.get(),
            assert_=True,
            terminate=True,
        )
        if pred := reflexive_e.try_get_sibling_trait(F.Expressions.is_predicate):
            mutator.predicate_terminate(pred)


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
        # TODO i think most idempotent expressions are using sets to represent operands
        # thus this is never going to trigger
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
            mutator.create_expression(
                F.Expressions.IsSubset,
                expr.as_operand.get(),
                inner,
                assert_=True,
                terminate=True,
            )
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
        innest = (
            inner.as_parameter_operatable.force_get()
            .as_expression.force_get()
            .get_operands()[0]
        )
        if mutator.utils.is_literal(innest):
            mutator.create_expression(
                F.Expressions.IsSubset,
                expr.as_operand.get(),
                innest,
                assert_=True,
                terminate=True,
            )
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

    @dataclass
    class FlattenAssociativeResult:
        extracted_operands: list[F.Parameters.can_be_operand]
        """
        Extracted operands
        """
        destroyed_operations: set[F.Expressions.is_expression]
        """
        ParameterOperables that got flattened and thus are not used anymore
        """

    def flatten_associative(
        to_flatten: F.Expressions.is_flattenable,
        check_destructable: Callable[
            [F.Expressions.is_expression, F.Expressions.is_expression], bool
        ],
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

        out = FlattenAssociativeResult(
            extracted_operands=[],
            destroyed_operations=set(),
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
            if not check_destructable(
                o.get_sibling_trait(F.Expressions.is_expression), to_flatten_expr
            ):
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

            out.destroyed_operations.add(nested_to_flatten_expr)

            res = flatten_associative(
                nested_to_flatten.get_sibling_trait(F.Expressions.is_flattenable),
                check_destructable,
            )
            nested_extracted_operands += res.extracted_operands
            out.destroyed_operations.update(res.destroyed_operations)

        out.extracted_operands.extend(nested_extracted_operands)

        return out

    ops = mutator.get_expressions(
        sort_by_depth=True, required_traits=(F.Expressions.is_flattenable,)
    )

    def _involved_in_expr_with_same_type(e: F.Expressions.is_expression) -> bool:
        return e.get_obj_type_node() in {
            n.get_type_node() for n in e.as_parameter_operatable.get().get_operations()
        }

    # get out deepest expr in compressable tree
    root_ops = [e for e in ops if not _involved_in_expr_with_same_type(e)]

    def is_replacable(
        to_replace: F.Expressions.is_expression,
        parent_expr: F.Expressions.is_expression,
    ) -> bool:
        """
        Check if an expression can be replaced.
        Only possible if not in use somewhere else or already mapped to new expr
        """
        # overly restrictive: equivalent replacement would be ok
        if mutator.has_been_mutated(to_replace.as_parameter_operatable.get()):
            return False
        exprs_involved_in = to_replace.as_parameter_operatable.get().get_operations()
        if len(exprs_involved_in) > 1:
            return False
        return True

    for expr in root_ops:
        expr_flat = expr.get_sibling_trait(F.Expressions.is_flattenable)
        res = flatten_associative(expr_flat, is_replacable)
        if not res.destroyed_operations:
            continue

        mutator.remove(
            *[e.as_parameter_operatable.get() for e in res.destroyed_operations]
        )

        mutator.mutate_expression(
            expr,
            operands=res.extracted_operands,
        )
