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
    Round,
    Sin,
    Union,
)
from faebryk.core.solver.utils import (
    Mutator,
)
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
    A + (B * 2) -> A + (B * 2)
    A + (A * 2) + (A * 3) -> (6 * A)
    A + (A * 2) + ((A *2 ) * 3) -> (3 * A) + (3 * (A * 2))

    #TODO
    A + B | A alias B ; never happens
    A + B | B alias [1,5] -> (A + B) , (A + B) subset (A + [1,5])
    A + B | B subset [1,5] -> (A + B) , (A + B) subset (A + [1,5])
    """

    literal_sum = _fold_op(literal_operands, lambda a, b: a + b, 0 * expr.units)  # type: ignore #TODO

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
        factors[paramop] += lit
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
        new_expr.alias_is(new_operands[0])


def fold_multiply(
    expr: Multiply,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    try:
        const_prod = [next(literal_operands)]
        for c in literal_operands:
            const_prod[0] *= c
        if const_prod[0] == 1 * dimensionless:  # TODO make work with all the types``
            const_prod = []
    except StopIteration:
        const_prod = []

    if len(const_prod) == 1 and const_prod[0].magnitude == 0:
        # TODO make work with all the types
        mutator.repr_map[expr] = 0 * expr.units
    else:
        if any(m > 1 for m in replacable_nonliteral_operands.values()):
            copied = {
                n: mutator.copy_operand_recursively(n)
                for n in replacable_nonliteral_operands
            }
            nonconst_power = [
                Power(copied[n], m * dimensionless) if m > 1 else copied[n]
                for n, m in replacable_nonliteral_operands.items()
            ]
            new_operands = [
                *nonconst_power,
                *const_prod,
                *(
                    mutator.copy_operand_recursively(o)
                    for o in non_replacable_nonliteral_operands
                ),
            ]
            if len(new_operands) > 1:
                new_expr = Multiply(*new_operands)
            elif len(new_operands) == 1:
                new_expr = new_operands[0]
                mutator.remove(expr)
            else:
                raise ValueError("No operands, should not happen")
            mutator.repr_map[expr] = new_expr


def fold_and(
    expr: And,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    const_op_list = list(literal_operands)
    if any(not isinstance(o, bool) for o in const_op_list):
        raise ValueError("Or with non-boolean operands")
    if any(not o for o in const_op_list):
        mutator.repr_map[expr] = False
        mutator.remove(expr)
    elif len(const_op_list) > 0 or any(
        m > 1 for m in replacable_nonliteral_operands.values()
    ):
        new_operands = [
            *(
                mutator.copy_operand_recursively(o)
                for o in replacable_nonliteral_operands
            ),
            *(
                mutator.copy_operand_recursively(o)
                for o in non_replacable_nonliteral_operands
            ),
        ]
        if len(new_operands) > 1:
            new_expr = And(*new_operands)
        elif len(new_operands) == 1:
            new_expr = new_operands[0]
            mutator.remove(expr)
        else:
            new_expr = True
        mutator.repr_map[expr] = new_expr


def fold_or(
    expr: Or,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    const_op_list = list(literal_operands)
    if any(not isinstance(o, bool) for o in const_op_list):
        raise ValueError("Or with non-boolean operands")
    if any(o for o in const_op_list):
        mutator.repr_map[expr] = True
        mutator.remove(expr)
    elif len(const_op_list) > 0 or any(
        m > 1 for m in replacable_nonliteral_operands.values()
    ):
        new_operands = [
            *(
                mutator.copy_operand_recursively(o)
                for o in replacable_nonliteral_operands
            ),
            *(
                mutator.copy_operand_recursively(o)
                for o in non_replacable_nonliteral_operands
            ),
        ]
        if len(new_operands) > 1:
            new_expr = Or(*new_operands)
        elif len(new_operands) == 1:
            new_expr = new_operands[0]
            mutator.remove(expr)
        else:
            new_expr = False
        mutator.repr_map[expr] = new_expr


def fold_pow(
    expr: Power,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    # TODO implement
    pass


def fold_alias(
    expr: Is,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    # TODO implement
    pass


def fold_ge(
    expr: GreaterOrEqual,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    # TODO implement
    pass


def fold_subset(
    expr: IsSubset,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    # TODO implement
    pass


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
        # FIXME remove
        elif True:
            return lambda *args: None

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
