# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from collections.abc import Sequence
from typing import Callable, cast

from faebryk.core.parameter import (
    Abs,
    Add,
    ConstrainableExpression,
    GreaterOrEqual,
    GreaterThan,
    Intersection,
    Is,
    IsSubset,
    Log,
    Multiply,
    Not,
    Or,
    ParameterOperatable,
    Power,
    Round,
    Sin,
    SymmetricDifference,
    Union,
)
from faebryk.core.solver.algorithm import SolverAlgorithm, algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    CanonicalExpression,
    CanonicalNumber,
    Contradiction,
    make_lit,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
)
from faebryk.libs.sets.sets import BoolSet, as_lit
from faebryk.libs.util import cast_assert, groupby, partition_as_list

logger = logging.getLogger(__name__)

# TODO prettify
# - e.g rename from fold


# Boilerplate ==========================================================================

MERGED = False

fold_algorithms: list[SolverAlgorithm] = []
expr_wise_algos: dict[
    type[CanonicalExpression],
    Callable[[CanonicalExpression, Mutator], None],
] = {}


def fold_literals[T: CanonicalExpression](
    mutator: Mutator, expr_type: type[T], f: Callable[[T, Mutator], None]
):
    """
    Tries to do operations on literals or fold expressions.
    - If possible to do literal operation, aliases expr with result.
    - If fold results in new expr, replaces old expr with new one.
    - If fold results in neutralization, returns operand if not literal else alias.

    Examples:
    ```
    Or(True, B) -> alias: True
    Add(A, B, 5, 10) -> replace: Add(A, B, 15)
    Add(10, 15) -> alias: 25
    Not(Not(A)) -> neutralize=replace: A
    ```
    """
    exprs = mutator.nodes_of_type(expr_type, sort_by_depth=True, new_only=False)
    for expr in exprs:
        if mutator.has_been_mutated(expr) or mutator.is_removed(expr):
            continue

        # covered by pure literal folding
        if mutator.utils.is_pure_literal_expression(expr):
            continue

        f(expr, mutator)


@algorithm("Expression-wise", terminal=False)
def expression_wise(mutator: Mutator):
    exprs = mutator.nodes_of_types(
        tuple(expr_wise_algos.keys()), sort_by_depth=True, new_only=False
    )
    exprs_by_type = groupby(exprs, lambda e: type(e))
    for expr_type, exprs in exprs_by_type.items():
        for expr in exprs:
            if mutator.has_been_mutated(expr) or mutator.is_removed(expr):
                continue

            # covered by pure literal folding
            if mutator.utils.is_pure_literal_expression(expr):
                continue
            expr_wise_algos[expr_type](expr, mutator)  # type: ignore


def expression_wise_algorithm[T: CanonicalExpression](expr_type: type[T]):
    def wrap(func: Callable[[T, Mutator], None]) -> SolverAlgorithm:
        if MERGED:
            expr_wise_algos[expr_type] = func  # type: ignore
            if expression_wise not in fold_algorithms:
                fold_algorithms.append(expression_wise)
            return expression_wise
        else:

            @algorithm(f"Fold {expr_type.__name__}", terminal=False)
            def wrapped(mutator: Mutator):
                fold_literals(mutator, expr_type, func)

            fold_algorithms.append(wrapped)
            return wrapped

    return wrap


# TODO REMOVE JUST A TEST
@algorithm("NOOOP")
def noop(mutator: Mutator):
    pass


fold_algorithms.append(noop)


# Arithmetic ---------------------------------------------------------------------------


@expression_wise_algorithm(Add)
def fold_add(expr: Add, mutator: Mutator):
    """
    A + A + 5 + 10 -> 2*A + 15
    A + 5 + (-5) -> A
    A + (-A) + 5 -> Add(5)
    A + (3 * A) + 5 -> (4 * A) + 5
    A + (A * B * 2) -> A + (A * B * 2)
    #TODO think about -> A * (1 + B * 2) (factorization), not in here tho
    A + (B * 2) -> A + (B * 2)
    A + (A * 2) + (A * 3) -> (6 * A)
    A + (A * 2) + ((A *2 ) * 3) -> (3 * A) + (3 * (A * 2))
    #TODO recheck double match (of last case)
    """

    # A + X, B + X, X = A * 5
    # 6*A
    # (A * 2) + (A * 5)
    literal_operands = list(expr.get_operand_literals().values())
    p_operands = expr.get_operand_operatables()
    non_replacable_nonliteral_operands, _replacable_nonliteral_operands = (
        partition_as_list(lambda o: not mutator.has_been_mutated(o), p_operands)
    )
    replacable_nonliteral_operands = Counter(_replacable_nonliteral_operands)
    literal_sum = mutator.utils.fold_op(literal_operands, lambda a, b: a + b, 0)  # type: ignore #TODO

    new_factors, old_factors = mutator.utils.collect_factors(
        replacable_nonliteral_operands, Multiply
    )

    # if non-lit factors all 1 and no literal folding, nothing to do
    if not new_factors and len(literal_sum) == len(literal_operands):
        return

    # Careful, modifying old graph, but should be ok
    factored_operands = [
        mutator.create_expression(Multiply, n, m, from_ops=[expr])
        for n, m in new_factors.items()
    ]

    new_operands = [
        *factored_operands,
        *old_factors,
        *literal_sum,
        *non_replacable_nonliteral_operands,
    ]

    if new_operands == expr.operands:
        return

    # unpack if single operand (operatable)
    if len(new_operands) == 1 and isinstance(new_operands[0], ParameterOperatable):
        new_operands = cast(list[ParameterOperatable], new_operands)
        mutator.mutate_unpack_expression(expr, new_operands)
        return

    new_expr = mutator.mutate_expression(
        expr, operands=new_operands, expression_factory=Add
    )
    # if only one literal operand, equal to it
    if len(new_operands) == 1:
        mutator.utils.alias_to(new_expr, new_operands[0], terminate=True)


@expression_wise_algorithm(Multiply)
def fold_multiply(expr: Multiply, mutator: Mutator):
    """
    TODO doc other simplifications
    A * (A + B)^-1 -> 1 + (B * A^-1)^-1
    """

    literal_operands = list(expr.get_operand_literals().values())
    p_operands = expr.get_operand_operatables()
    non_replacable_nonliteral_operands, _replacable_nonliteral_operands = (
        partition_as_list(lambda o: not mutator.has_been_mutated(o), p_operands)
    )
    replacable_nonliteral_operands = Counter(_replacable_nonliteral_operands)

    literal_prod = mutator.utils.fold_op(literal_operands, lambda a, b: a * b, 1)  # type: ignore #TODO

    new_powers, old_powers = mutator.utils.collect_factors(
        replacable_nonliteral_operands, Power
    )

    # if non-lit powers all 1 and no literal folding, nothing to do
    if not (
        not new_powers
        and len(literal_prod) == len(literal_operands)
        and not (
            literal_prod
            and literal_prod[0] == 0
            and len(replacable_nonliteral_operands)
            + len(non_replacable_nonliteral_operands)
            > 0
        )
    ):
        # Careful, modifying old graph, but should be ok
        powered_operands = [
            mutator.create_expression(Power, n, m, from_ops=[expr])
            for n, m in new_powers.items()
        ]

        new_operands = [
            *powered_operands,
            *old_powers,
            *literal_prod,
            *non_replacable_nonliteral_operands,
        ]

        # 0 * A -> 0
        if 0 in new_operands:
            new_operands = [make_lit(0)]
            # convert_operable_aliased_to_single_into_literal takes care of rest

        # unpack if single operand (operatable)
        if len(new_operands) == 1 and isinstance(new_operands[0], ParameterOperatable):
            new_operands = cast(list[ParameterOperatable], new_operands)
            mutator.mutate_unpack_expression(expr, new_operands)
            return

        if new_operands != expr.operands:
            new_expr = mutator.mutate_expression(
                expr, operands=new_operands, expression_factory=Multiply
            )

            # if only one literal operand, equal to it
            if len(new_operands) == 1:
                mutator.utils.alias_to(new_expr, new_operands[0], terminate=True)
            return

    # if len(expr.operands) == 2:
    #     # TODO pos independend
    #     A, right = expr.operands
    #     # A * (A + B)^-1 -> (1 + B * A^-1)^-1
    #     if (
    #         isinstance(A, ParameterOperatable)
    #         and isinstance(right, Power)
    #         and right.get_operand_literals().get(1) == -1
    #         and isinstance(inner := right.operands[0], Add)
    #         and len(inner.operands) == 2
    #         and not inner.get_operand_literals()
    #         and A in inner.operands
    #     ):
    #         B = inner.get_other_operand(A)
    #         A_inv = mutator.create_expression(
    #             Power,
    #             A,
    #             make_lit(-1),
    #             from_ops=[expr],
    #         )
    #         mutator.mutate_expression(
    #             expr,
    #             expression_factory=Power,
    #             operands=[
    #                 mutator.create_expression(
    #                     Add,
    #                     make_lit(1),
    #                     mutator.create_expression(Multiply, B, A_inv,
    #                       from_ops=[expr]),
    #                 ),
    #                 make_lit(-1),
    #             ],
    #         )


@expression_wise_algorithm(Power)
def fold_pow(expr: Power, mutator: Mutator):
    """
    ```
    A^0 -> 1
    A^1 -> A
    0^A -> 0
    1^A -> 1
    #TODO: (A^B)^C -> A^(B*C)
    #TODO rethink: 0^0 -> 1
    ```
    """

    # TODO if (litex0)^negative -> new constraint

    base, exp = expr.operands

    # All literals
    if mutator.utils.is_numeric_literal(base) and mutator.utils.is_numeric_literal(exp):
        try:
            result = base**exp
        except NotImplementedError:
            # TODO either fix or raise a warning
            return
        mutator.utils.alias_to(expr, result, terminate=True)
        return

    if mutator.utils.is_numeric_literal(exp):
        if exp == 1:
            mutator.mutate_unpack_expression(expr)
            return

        # in python 0**0 is also 1
        if exp == 0:
            mutator.utils.alias_to(expr, as_lit(1), terminate=True)
            return

    if mutator.utils.is_numeric_literal(base):
        if base == 0:
            mutator.utils.alias_to(expr, as_lit(0), terminate=True)
            # FIXME: exp >! 0
            return
        if base == 1:
            mutator.utils.alias_to(expr, as_lit(1), terminate=True)
            return


# @expression_wise_algorithm(Log)
def fold_log(expr: Log, mutator: Mutator):
    """
    # TODO log(A*B) -> log(A) + log(B)
    # TODO log(A^B) -> B*log(A)
    """
    return


# @expression_wise_algorithm(Abs)
def fold_abs(expr: Abs, mutator: Mutator):
    """
    # TODO |-A| = |A|
    # TODO |A*B| = |A|*|B|
    # TODO |A+B| <= |A|+|B|
    """
    return


# @expression_wise_algorithm(Round)
def fold_round(expr: Round, mutator: Mutator):
    """
    TODO: Think about round(A + X)
    """
    return


@expression_wise_algorithm(Sin)
def fold_sin(expr: Sin, mutator: Mutator):
    """
    Sin ss! [-1, 1]
    #TODO Sin(-A) -> -Sin(A)
    #TODO Sin(A + 2*pi) -> Sin(A)
    #TODO Sin(A+B) -> Sin(A)*Cos(B) + Cos(A)*Sin(B)
    """
    mutator.utils.subset_to(expr, make_lit(Quantity_Interval(-1, 1)), from_ops=[expr])


# Setic --------------------------------------------------------------------------------


# @expression_wise_algorithm(Intersection)
def fold_intersect(expr: Intersection, mutator: Mutator):
    """
    Intersection(A) -> A (implicit)
    """

    return


# @expression_wise_algorithm(Union)
def fold_union(expr: Union, mutator: Mutator):
    """
    Union(A) -> A (implicit)
    """

    return


# @expression_wise_algorithm(SymmetricDifference)
def fold_symmetric_difference(expr: SymmetricDifference, mutator: Mutator):
    """ """

    return


# Constrainable ------------------------------------------------------------------------


@expression_wise_algorithm(Or)
def fold_or(expr: Or, mutator: Mutator):
    """
    ```
    Or(A, B, C, True) -> True
    Or(A, B, C, False) -> Or(A, B, C)
    Or(A, B, A) -> Or(A, B)
    Or() -> False
    ```
    """

    # Or(P) -> P implicit (unary identity unpack)
    # Or!(P) -> P! implicit (unary identity unpack)
    # Or(A, B, A) -> Or(A, B) implicit (idempotent)

    # Or(A, B, C, True) -> True
    if BoolSet(True) in expr.get_operand_literals():
        mutator.utils.alias_is_literal_and_check_predicate_eval(expr, True)
        return

    # Or(A, B, C, False) -> Or(A, B, C)
    filtered_operands = [op for op in expr.operands if BoolSet(False) != op]
    if len(filtered_operands) != len(expr.operands):
        # Rebuild without False literals
        mutator.mutate_expression(expr, operands=filtered_operands)
        return


@expression_wise_algorithm(Not)
def fold_not(expr: Not, mutator: Mutator):
    """
    ```
    ¬(¬A) -> A
    ¬P | P constrained -> False

    ¬!(¬A v ¬B v C) -> ¬!(¬!A v ¬!B v C), ¬!C
    ¬!A -> A is! False
    ```
    """
    # TODO ¬(A >= B) -> (B > A) ss ¬(A >= B) (only ss because of partial overlap)

    # ¬(¬A) -> A implicit
    # ¬!(¬A) -> !A implicit

    assert len(expr.operands) == 1
    op = expr.operands[0]
    assert isinstance(op, ParameterOperatable)

    # ¬P | P constrained -> False
    if isinstance(op, ConstrainableExpression) and op.constrained:
        # ¬!P! | P constrained -> Contradiction
        if expr.constrained:
            raise Contradiction("¬!P!", involved=[expr], mutator=mutator)
        mutator.utils.alias_to(expr, as_lit(False), terminate=True)
        return

    if not mutator.has_been_mutated(op):
        # TODO this is kinda ugly, should be in Or fold if it aliases to false
        # ¬!(¬A v ¬B v C) -> ¬!(¬!A v ¬!B v C), ¬!C
        if expr.constrained:
            # ¬( v )
            if isinstance(op, Or):
                # FIXME remove this shortcut
                # should be handle in more general way
                # maybe we need to terminate non-predicates too
                if not op.operands:
                    mutator.utils.alias_is_literal_and_check_predicate_eval(expr, True)
                for inner_op in op.operands:
                    # ¬(¬A v ...)
                    if isinstance(inner_op, Not):
                        for not_op in inner_op.operands:
                            if (
                                isinstance(not_op, ConstrainableExpression)
                                and not not_op.constrained
                            ):
                                mutator.constrain(
                                    cast_assert(
                                        ConstrainableExpression,
                                        mutator.get_copy(not_op),
                                    )
                                )
                    # ¬(A v ...)
                    elif isinstance(inner_op, ConstrainableExpression):
                        parent_nots = inner_op.get_operations(Not)
                        if parent_nots:
                            for n in parent_nots:
                                mutator.constrain(n)
                        else:
                            mutator.create_expression(
                                Not, inner_op, from_ops=[expr], constrain=True
                            )

    if expr.constrained:
        mutator.utils.alias_is_literal_and_check_predicate_eval(op, False)


@expression_wise_algorithm(Is)
def fold_is(expr: Is, mutator: Mutator):
    """
    ```
    P is! True -> P!
    ```
    """

    is_true_alias = expr.constrained and BoolSet(True) in expr.get_operand_literals()
    if is_true_alias:
        # P1 is! True -> P1!
        # P1 is! P2!  -> P1! (implicit)
        for p in expr.get_operand_operatables(ConstrainableExpression):
            mutator.constrain(p)


@expression_wise_algorithm(IsSubset)
def fold_subset(expr: IsSubset, mutator: Mutator):
    """
    ```
    A is B, A ss B | B non(ex)literal -> repr(B, A)
    A ss ([X]) -> A is ([X])
    A ss {} -> A is {}
    # predicates
    P ss! True -> P!
    P ss! False -> ¬!P
    P1 ss! P2! -> P1!
    # literals
    X ss Y -> True / False

    A ss! B, B ss!/is! C -> A ss! C in transitive_subset
    ```
    """

    A, B = expr.operands

    if not mutator.utils.is_literal(B):
        return

    # A ss ([X]) -> A is ([X])
    # A ss {} -> A is {}
    if B.is_single_element() or B.is_empty():
        mutator.mutate_expression(expr, expression_factory=Is)
        return

    if expr.constrained:
        # P1 ss! True -> P1!
        # P1 ss! P2!  -> P1!
        if (
            B == BoolSet(True)
            or isinstance(B, ConstrainableExpression)
            and B.constrained
        ):
            assert isinstance(A, ConstrainableExpression)
            mutator.constrain(A)
        # P ss! False -> ¬!P
        if B == BoolSet(False):
            assert isinstance(A, ConstrainableExpression)
            mutator.create_expression(Not, A, from_ops=[expr], constrain=True)


@expression_wise_algorithm(GreaterOrEqual)
def fold_ge(expr: GreaterOrEqual, mutator: Mutator):
    """
    ```
    A >= A -> True
    # literals
    X >= Y -> [True] / [False] / [True, False]
    A >=! X | |X| > 1 -> A >=! X.max()
    X >=! A | |X| > 1 -> X.min() >=! A
    # uncorrelated
    A >= B{I|X} -> A >= X.max()
    B{I|X} >= A -> X.min() >= A
    ```
    """
    left, right = expr.operands
    literal_operands = cast(Sequence[CanonicalNumber], expr.get_operand_literals())

    # A >=! X | |X| > 1 -> A >=! X.max()
    # X >=! A | |X| > 1 -> X.min() >=! A
    if literal_operands and expr.constrained:
        assert len(literal_operands) == 1
        lit = literal_operands[0]
        if not lit.is_single_element() and not lit.is_empty():
            if left is lit:
                mutator.mutate_expression(
                    expr, operands=[make_lit(lit.min_elem), right]
                )
            else:
                assert right is lit
                mutator.mutate_expression(expr, operands=[left, make_lit(lit.max_elem)])
        return


# @expression_wise_algorithm(GreaterThan)
def fold_gt(expr: GreaterThan, mutator: Mutator):
    """ """
    return
