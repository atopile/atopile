# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from collections.abc import Sequence
from typing import Callable

from faebryk.core.parameter import (
    Abs,
    Add,
    And,
    Expression,
    GreaterOrEqual,
    GreaterThan,
    Intersection,
    Is,
    IsSubset,
    Log,
    Multiply,
    Or,
    ParameterOperatable,
    Power,
    Predicate,
    Round,
    Sin,
    Union,
)
from faebryk.core.solver.utils import (
    ContradictionByLiteral,
    Mutator,
    alias_is_literal,
)
from faebryk.libs.units import dimensionless
from faebryk.libs.util import KeyErrorAmbiguous

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
    A + (B * 2) -> A + (B * 2)
    A + (A * 2) + (A * 3) -> (6 * A)
    A + (A * 2) + ((A *2 ) * 3) -> (3 * A) + (3 * (A * 2))
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
        if paramop not in powers:
            continue
        # not lit >= 0 is not the same as lit < 0
        if paramop.try_get_literal() == 0.0 * paramop.units and not lit >= 0.0 * dimensionless:
            continue
        powers[paramop] += lit  # type: ignore #TODO
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

    zero_operand = any(ParameterOperatable.try_extract_literal(o) == 0.0 * o.units for o in new_operands)
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


def try_extract_all_literals(expr: Predicate, op: type[Expression] | None = None) -> list[Literal] | None:
    try:
        as_lits = [ParameterOperatable.try_extract_literal(o, op) for o in expr.operands]
    except KeyErrorAmbiguous as e:
        raise ContradictionByLiteral(
            f"Duplicate unequal is literals: {e.duplicates}"
        ) from e

    if None in as_lits:
        return None
    return as_lits

def raise_alias_is_bool(expr: Predicate, value: bool) -> bool:
    alias_is_literal(expr, value)
    if not value and expr.constrained:
        return True
    return False

def fold_and(
    expr: And,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    #TODO remove true ones
    lits = try_extract_all_literals(expr)
    if lits is None:
        return
    false_ops = [op for (lit, op) in zip(lits, expr.operands) if lit == False] #TODO sets of bools
    if raise_alias_is_bool(expr, len(false_ops) == 0):
        raise ContradictionByLiteral(f"False operands: {false_ops}")


def fold_or(
    expr: Or,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    #TODO remove false ones
    lits = try_extract_all_literals(expr)
    if lits is None:
        return
    true_ops = [op for (lit, op) in zip(lits, expr.operands) if lit == True] #TODO sets of bools
    if raise_alias_is_bool(expr, len(true_ops) > 0):
        raise ContradictionByLiteral(f"All false: {expr.operands}")


def fold_pow(
    expr: Power,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    if len(literal_operands) == 2:
        base, exp = literal_operands
        if exp == 1.0 * dimensionless:
            alias_is_literal(expr, base)
            return
        elif exp == -1.0 * dimensionless:
            alias_is_literal(expr, 1.0 * dimensionless / base)
            return
        else:
            #FIXME not supported by sets yet
            alias_is_literal(expr, base ** exp)
            return

    if not ParameterOperatable.is_literal(expr.operands[1]):
        return

    exp = literal_operands[-1]

    if exp == 1.0 * dimensionless:
        mutator._mutate(expr, mutator.get_copy(expr.operands[0]))
        return

    #TODO handle exp == 0 and base != 0/0 not in base

def is_implies_true(pred: Predicate) -> bool:
    # CONSIDER: when can we remove the expression?
    if pred.operands[0] is pred.operands[1]:
        alias_is_literal(pred, True)
        return True
    return False

def fold_alias(
    expr: Is,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    if is_implies_true(expr):
        return

    lits = try_extract_all_literals(expr)
    if lits is None:
        return
    a, b = lits
    if raise_alias_is_bool(expr, a == b):
        raise ContradictionByLiteral(f"{a} != {b}")


def fold_ge(
    expr: GreaterOrEqual,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    if is_implies_true(expr):
        return

    lits = try_extract_all_literals(expr)
    if lits is None:
        return
    a, b = lits
    if raise_alias_is_bool(expr, a >= b):
        raise ContradictionByLiteral(f"{a} not >= {b}")



def fold_subset(
    expr: IsSubset,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    if is_implies_true(expr):
        return

    #FIXME should use op=IsSubset? both?
    lits = try_extract_all_literals(expr)
    if lits is None:
        return
    a, b = lits
    if raise_alias_is_bool(expr, a.is_subset_of(b)):
        raise ContradictionByLiteral(f"{a} not subset of {b}")


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
    expr: Expression,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
) -> None:
    """
    literal_operands must be actual literals, not the literal the operand is aliased to!
    maybe it would be fine for set literals with one element?
    """

    def get_func[T: Expression](
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
        # Subtract non-canonical
        if isinstance(expr, Add):
            return fold_add  # type: ignore
        elif isinstance(expr, Multiply):
            return fold_multiply  # type: ignore
        # Divide non-canonical
        # Sqrt non-canonical
        elif isinstance(expr, Power):
            return fold_pow  # type: ignore
        elif isinstance(expr, Log):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, Abs):
            # TODO implement
            return lambda *args: None
        # Cos non-canonical
        elif isinstance(expr, Sin):
            # TODO implement
            return lambda *args: None
        # Floor non-canonical
        # Ceil non-canonical
        elif isinstance(expr, Round):
            # TODO implement
            return lambda *args: None
        # Logic
        # Xor non-canonical
        # And non-canonical
        # Implies non-canonical
        elif isinstance(expr, Or):
            return fold_or  # type: ignore
        # TODO make non-canonical
        elif isinstance(expr, And):
            return fold_and  # type: ignore
        # Equality / Inequality
        elif isinstance(expr, Is):
            return fold_alias  # type: ignore
        # LessOrEqual non-canonical
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
        return lambda *args: None

    get_func(expr)(
        expr,
        literal_operands,
        replacable_nonliteral_operands,
        non_replacable_nonliteral_operands,
        mutator,
    )
