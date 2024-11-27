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
    Mutator,
    alias_is_and_check_constrained,
    alias_is_literal,
    try_extract_all_literals,
    try_extract_numeric_literal,
)
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint
from faebryk.libs.sets.sets import BoolSet
from faebryk.libs.units import dimensionless

logger = logging.getLogger(__name__)

# TODO prettify

Literal = ParameterOperatable.Literal


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


def fold_or(
    expr: Or,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    Or(A, B, C, True) -> True
    Or(A, B, C, False) -> Or(A, B, C)
    Or(A, B, C, P) | P constrained -> True
    ```
    """

    extracted_literals = try_extract_all_literals(
        expr, lit_type=BoolSet, accept_partial=True
    )
    # Or(A, B, C, True) -> True
    if extracted_literals and any(extracted_literals):
        alias_is_and_check_constrained(expr, True)
        return

    # Or(A, B, C, P) | P constrained -> True
    if any(
        op.constrained
        for op in expr.operands
        if isinstance(op, ConstrainableExpression)
    ):
        alias_is_and_check_constrained(expr, True)

    # Or(A, B, C, False) -> Or(A, B, C)
    # TODO also do something when extracted lits?
    if literal_operands:
        # Rebuild without (False) literals
        mutator.mutate_expression(
            expr,
            operands=[
                *replacable_nonliteral_operands.keys(),
                *non_replacable_nonliteral_operands,
            ],
        )


def fold_not(
    expr: Not,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    Not(Not(A)) -> A
    Not(True) -> False
    Not(False) -> True
    Not(P) | P constrained -> False
    ```
    """
    assert len(expr.operands) == 1

    lits = try_extract_all_literals(expr, lit_type=BoolSet)
    if lits:
        inner = lits[0]
        alias_is_and_check_constrained(expr, not inner)
        return

    if replacable_nonliteral_operands:
        op = next(iter(replacable_nonliteral_operands.keys()))
        if isinstance(op, Not):
            inner = op.operands[0]
            # inner Not would have run first
            assert not isinstance(inner, BoolSet)
            expr.alias_is(inner)
            return

    op = expr.operands[0]
    # assume predicate true
    if isinstance(op, ConstrainableExpression) and op.constrained:
        alias_is_and_check_constrained(expr, False)
        return


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
    0^0 -> 1
    A^1 -> A
    0^A -> 0
    1^A -> 1
    5^3 -> 125
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
            return
        if base == 1:
            alias_is_literal(expr, 1)
            return


def is_implies_true(pred: Predicate) -> bool:
    if pred.operands[0] is not pred.operands[1]:
        return False
    alias_is_literal(pred, True)
    return True


def fold_alias(
    expr: Is,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    A is A -> True
    # literals
    X is Y | X == Y -> True
    X is Y | X != Y -> False
    ```
    """

    if is_implies_true(expr):
        return

    lits = try_extract_all_literals(expr)
    if lits is None:
        return
    a, b = lits
    alias_is_and_check_constrained(expr, a == b)


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
    if is_implies_true(expr):
        return

    lits = try_extract_all_literals(expr, lit_type=Quantity_Interval_Disjoint)
    if lits is None:
        return
    a, b = lits
    alias_is_and_check_constrained(expr, a >= b)


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
    # literals
    X is subset of Y -> True / False

    # TODO A subset B, B subset C -> A subset C (transitive)
    ```
    """

    if is_implies_true(expr):
        return

    # FIXME should use op=IsSubset? both?
    lits = try_extract_all_literals(expr)
    if lits is None:
        return
    a, b = lits
    alias_is_and_check_constrained(expr, a.is_subset_of(b))


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
            return fold_alias  # type: ignore
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
