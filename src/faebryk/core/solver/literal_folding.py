# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from collections.abc import Sequence
from typing import Callable

from faebryk.core.parameter import (
    Abs,
    Add,
    ConstrainableExpression,
    Difference,
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
    Predicate,
    Round,
    Sin,
    SymmetricDifference,
    Union,
)
from faebryk.core.solver.utils import (
    CanonicalNumber,
    CanonicalOperation,
    Contradiction,
    Mutator,
    alias_is_literal,
    alias_is_literal_and_check_predicate_eval,
    try_extract_all_literals,
    try_extract_boolset,
    try_extract_numeric_literal,
)
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint
from faebryk.libs.sets.sets import BoolSet
from faebryk.libs.units import dimensionless
from faebryk.libs.util import cast_assert

logger = logging.getLogger(__name__)

# TODO prettify

Literal = ParameterOperatable.Literal

# Arithmetic ---------------------------------------------------------------------------


def _fold_op(
    operands: Sequence[Literal],
    operator: Callable[[Literal, Literal], Literal],
    identity: Literal,
):
    """
    Return 'sum' of all literals in the iterable, or empty list if sum is identity.
    """
    if not operands:
        return []

    literal_it = iter(operands)
    const_sum = [next(literal_it)]
    for c in literal_it:
        const_sum[0] = operator(const_sum[0], c)

    # TODO make work with all the types
    if const_sum[0] == identity:
        const_sum = []

    return const_sum


def fold_add(
    expr: Add,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
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

    literal_sum = _fold_op(literal_operands, lambda a, b: a + b, 0.0 * expr.units)  # type: ignore #TODO

    # collect factors
    factors: dict[ParameterOperatable, ParameterOperatable.NumberLiteral] = dict(
        replacable_nonliteral_operands.items()
    )
    for mul in set(factors.keys()):
        if not isinstance(mul, Multiply):
            continue
        if len(mul.operands) != 2:
            continue
        if not any(ParameterOperatable.is_literal(operand) for operand in mul.operands):
            continue
        if not any(operand in factors for operand in mul.operands):
            continue
        lit = next(o for o in mul.operands if ParameterOperatable.is_literal(o))
        paramop = next(o for o in mul.operands if not ParameterOperatable.is_literal(o))
        factors[paramop] += lit  # type: ignore #TODO
        mutator.remove(mul)
        del factors[mul]

    # if no literal folding and non-lit factors all 1, nothing to do
    if all(m == 1 for m in factors.values()) and len(literal_sum) == len(
        literal_operands
    ):
        return

    # Careful, modifying old graph, but should be ok
    nonlit_operands = [Multiply(n, m) if m != 1 else n for n, m in factors.items()]

    new_operands = [
        *nonlit_operands,
        *literal_sum,
        *non_replacable_nonliteral_operands,
    ]

    # unpack if single operand (operatable)
    if len(new_operands) == 1 and isinstance(new_operands[0], ParameterOperatable):
        mutator._mutate(expr, mutator.get_copy(new_operands[0]))
        return

    new_expr = mutator.mutate_expression(
        expr, operands=new_operands, expression_factory=Add
    )

    # if only one literal operand, equal to it
    if len(new_operands) == 1:
        alias_is_literal(new_expr, new_operands[0])


def fold_multiply(
    expr: Multiply,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    literal_prod = _fold_op(literal_operands, lambda a, b: a * b, 1.0 * expr.units)  # type: ignore #TODO

    # collect factors
    powers: dict[ParameterOperatable, ParameterOperatable.NumberLiteral] = dict(
        replacable_nonliteral_operands.items()
    )
    for power in set(powers.keys()):
        if not isinstance(power, Power):
            continue
        lit = power.operands[1]
        paramop = power.operands[0]
        if not ParameterOperatable.is_literal(lit):
            continue
        assert isinstance(lit, CanonicalNumber)
        if paramop not in powers:
            continue
        # not lit >= 0 is not the same as lit < 0
        if paramop.try_get_literal() == 0 and not lit >= 0 * dimensionless:
            continue
        powers[paramop] += lit  # type: ignore
        mutator.remove(power)
        del powers[power]

    # if no literal folding and non-lit factors all 1, nothing to do
    if all(m == 1 for m in powers.values()) and len(literal_prod) == len(
        literal_operands
    ):
        return

    # Careful, modifying old graph, but should be ok
    nonlit_operands = [Power(n, m) if m != 1 else n for n, m in powers.items()]

    new_operands = [
        *nonlit_operands,
        *literal_prod,
        *non_replacable_nonliteral_operands,
    ]

    zero_operand = any(
        ParameterOperatable.try_extract_literal(o) == 0.0 * o.units
        for o in new_operands
    )
    if zero_operand:
        new_operands = [0.0 * expr.units]

    # unpack if single operand (operatable)
    if len(new_operands) == 1 and isinstance(new_operands[0], ParameterOperatable):
        mutator._mutate(expr, mutator.get_copy(new_operands[0]))
        return

    new_expr = mutator.mutate_expression(
        expr, operands=new_operands, expression_factory=Multiply
    )

    # if only one literal operand, equal to it
    if len(new_operands) == 1:
        alias_is_literal(new_expr, new_operands[0])


def fold_pow(
    expr: Power,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    A^0 -> 1
    A^1 -> A
    0^A -> 0
    1^A -> 1
    5^3 -> 125
    #TODO rethink: 0^0 -> 1
    ```
    """

    base, exp = map(try_extract_numeric_literal, expr.operands)
    # All literals
    if base is not None and exp is not None:
        alias_is_literal(expr, base**exp)
        return

    if exp is not None:
        if exp == 1:
            mutator._mutate(expr, mutator.get_copy(expr.operands[0]))
            return

        # in python 0**0 is also 1
        if exp == 0:
            alias_is_literal(expr, 1)
            return

    if base is not None:
        if base == 0:
            alias_is_literal(expr, 0)
            # FIXME: exp >! 0
            return
        if base == 1:
            alias_is_literal(expr, 1)
            return


# Setic --------------------------------------------------------------------------------
def fold_intersect(
    expr: Intersection,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    # TODO implement
    pass


def fold_union(
    expr: Union,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    # TODO implement
    pass


# Constrainable ------------------------------------------------------------------------


def fold_or(
    expr: Or,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    Or(A, B, C, TrueEx) -> True
    Or(A, B, C, FalseEx) -> Or(A, B, C)
    Or(A, B, C, P) | P constrained -> True
    #TODO Or(A, B, A) -> Or(A, B)
    Or(P) -> P
    Or!(P) -> P!
    Or() -> False
    ```
    """

    extracted_literals = try_extract_all_literals(
        expr, lit_type=BoolSet, accept_partial=True
    )
    # Or(A, B, C, True) -> True
    if extracted_literals and any(extracted_literals):
        alias_is_literal_and_check_predicate_eval(expr, True, mutator)
        return

    # Or() -> False
    if not expr.operands:
        alias_is_literal_and_check_predicate_eval(expr, False, mutator)
        return

    # Or(A, B, C, FalseEx) -> Or(A, B, C)
    # Or(A, B, A) -> Or(A, B)
    operands_not_clearly_false = {
        op
        for op in expr.operands
        if (lit := try_extract_boolset(op, allow_subset=True)) is None or True in lit
    }
    if len(operands_not_clearly_false) != len(expr.operands):
        # Rebuild without (False) literals
        mutator.mutate_expression(expr, operands=operands_not_clearly_false)

    # Or(P) -> P
    if len(expr.operands) == 1:
        op = cast_assert(ParameterOperatable, expr.operands[0])
        out = cast_assert(
            ConstrainableExpression, mutator._mutate(expr, mutator.get_copy(op))
        )
        # Or(P!) -> P!
        if expr.constrained:
            out.constrain()
        return


def fold_not(
    expr: Not,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    ¬(¬A) -> A
    ¬True -> False
    ¬False -> True
    ¬P | P constrained -> False

    ¬!(¬A v ¬B v C) -> ¬!(¬!A v ¬!B v C), ¬!C
    ```
    """
    # TODO ¬(A >= B) -> (B > A) ss ¬(A >= B) (only ss because of partial overlap)

    assert len(expr.operands) == 1

    lits = try_extract_all_literals(expr, lit_type=BoolSet)
    if lits:
        inner = lits[0]
        alias_is_literal_and_check_predicate_eval(expr, not inner, mutator)
        return

    op = expr.operands[0]
    if isinstance(op, ConstrainableExpression) and op.constrained and expr.constrained:
        raise Contradiction(expr)

    if replacable_nonliteral_operands:
        op = next(iter(replacable_nonliteral_operands.keys()))
        if isinstance(op, Not):
            inner = op.operands[0]
            # inner Not would have run first
            assert not isinstance(inner, BoolSet)
            mutator._mutate(expr, mutator.get_copy(inner))
            return

        # TODO this is kinda ugly
        # ¬!(¬A v ¬B v C) -> ¬!(¬!A v ¬!B v C), ¬!C
        if isinstance(op, Or) and expr.constrained:
            for inner_op in op.operands:
                if isinstance(inner_op, Not):
                    for not_op in inner_op.operands:
                        if isinstance(not_op, ConstrainableExpression):
                            not_op.constrain()
                elif isinstance(inner_op, ConstrainableExpression):
                    Not(inner_op).constrain()


def if_operands_same_make_true(pred: Predicate, mutator: Mutator) -> bool:
    if pred.operands[0] is not pred.operands[1]:
        return False
    alias_is_literal_and_check_predicate_eval(pred, True, mutator)
    return True


def fold_is(
    expr: Is,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    A is A -> True
    A is X, A is Y | X != Y, X,Y lit -> Contradiction
    # predicates
    P is! True -> P!
    P is! False -> ¬!P
    P1 is! P2! -> P1!
    # literals
    X is Y | X == Y -> True
    X is Y | X != Y -> False
    ```
    """

    # A is B -> R is R
    # A is E -> R is R, R is E
    # A is False, E is False
    #

    # A is A -> A is!! A
    if if_operands_same_make_true(expr, mutator):
        return

    # A is X, A is Y | X != Y -> Contradiction
    # is enough to check because of alias class merge
    lits = try_extract_all_literals(expr)

    # TODO Xex/Yex or X/Y enough?
    # Xex is Yex
    if lits is not None:
        a, b = lits
        alias_is_literal_and_check_predicate_eval(expr, a == b, mutator)
        return

    if expr.constrained:
        # P1 is! True -> P1!
        # P1 is! P2!  -> P1!
        if BoolSet(True) in literal_operands or any(
            op.constrained
            for op in expr.get_operatable_operands(ConstrainableExpression)
        ):
            for p in expr.get_operatable_operands(ConstrainableExpression):
                p.constrain()
        # P is! False -> ¬!P
        if BoolSet(False) in literal_operands:
            for p in expr.get_operatable_operands(ConstrainableExpression):
                Not(p).constrain()


def fold_subset(
    expr: IsSubset,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    A is subset of A -> True
    # predicates
    P ss! True -> P!
    P ss! False -> ¬!P
    P1 ss! P2! -> P1!
    # literals
    X is subset of Y -> True / False

    # TODO A subset B, B subset C -> A subset C (transitive)
    ```
    """

    if if_operands_same_make_true(expr, mutator):
        return

    # FIXME should use op=IsSubset? both?
    lits = try_extract_all_literals(expr)
    if lits is None:
        return
    a, b = lits
    alias_is_literal_and_check_predicate_eval(expr, a.is_subset_of(b), mutator)

    if expr.constrained:
        # P1 ss! True -> P1!
        # P1 ss! P2!  -> P1!
        if BoolSet(True) in literal_operands or any(
            op.constrained
            for op in expr.get_operatable_operands(ConstrainableExpression)
        ):
            for p in expr.get_operatable_operands(ConstrainableExpression):
                p.constrain()
        # P ss! False -> ¬!P
        if BoolSet(False) in literal_operands:
            for p in expr.get_operatable_operands(ConstrainableExpression):
                Not(p).constrain()


def fold_ge(
    expr: GreaterOrEqual,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    A >= A -> True
    # literals
    X >= Y -> True / False
    ```
    """
    if if_operands_same_make_true(expr, mutator):
        return

    lits = try_extract_all_literals(expr, lit_type=Quantity_Interval_Disjoint)
    if lits is None:
        return
    a, b = lits
    alias_is_literal_and_check_predicate_eval(expr, a >= b, mutator)


# Boilerplate --------------------------------------------------------------------------


def fold(
    expr: CanonicalOperation,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
) -> None:
    """
    literal_operands must be actual literals, not the literal the operand is aliased to!
    maybe it would be fine for set literals with one element?
    """

    def get_func[T: CanonicalOperation](
        expr: T,
    ) -> Callable[
        [
            T,
            Sequence[Literal],
            Counter[ParameterOperatable],
            Sequence[ParameterOperatable],
            Mutator,
        ],
        None,
    ]:
        # Arithmetic
        if isinstance(expr, Add):
            return fold_add  # type: ignore
        elif isinstance(expr, Multiply):
            return fold_multiply  # type: ignore
        elif isinstance(expr, Power):
            return fold_pow  # type: ignore
        elif isinstance(expr, Round):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, Abs):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, Sin):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, Log):
            # TODO implement
            return lambda *args: None
        # Logic
        elif isinstance(expr, Or):
            return fold_or  # type: ignore
        elif isinstance(expr, Not):
            return fold_not  # type: ignore
        # Equality / Inequality
        elif isinstance(expr, Is):
            return fold_is  # type: ignore
        elif isinstance(expr, GreaterOrEqual):
            return fold_ge  # type: ignore
        elif isinstance(expr, GreaterThan):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, IsSubset):
            return fold_subset  # type: ignore
        # Sets
        elif isinstance(expr, Intersection):
            return fold_intersect  # type: ignore
        elif isinstance(expr, Union):
            return fold_union  # type: ignore
        elif isinstance(expr, SymmetricDifference):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, Difference):
            # TODO implement
            return lambda *args: None

        raise ValueError(f"unsupported operation: {expr}")

    get_func(expr)(
        expr,
        literal_operands,
        replacable_nonliteral_operands,
        non_replacable_nonliteral_operands,
        mutator,
    )
