# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from collections.abc import Iterable
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


def fold_add(
    expr: Add,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    try:
        const_sum = [next(const_ops)]
        for c in const_ops:
            dirty = True
            const_sum[0] += c
        # TODO make work with all the types
        if const_sum[0] == 0 * expr.units:
            dirty = True
            const_sum = []
    except StopIteration:
        const_sum = []
    if any(m > 1 for m in multiplicity.values()):
        dirty = True
    if dirty:
        copied = {
            n: Mutator.copy_operand_recursively(n, repr_map) for n in multiplicity
        }
        nonconst_prod = [
            Multiply(copied[n], m * dimensionless) if m > 1 else copied[n]
            for n, m in multiplicity.items()
        ]
        new_operands = [
            *nonconst_prod,
            *const_sum,
            *(
                Mutator.copy_operand_recursively(o, repr_map)
                for o in non_replacable_nonconst_ops
            ),
        ]
        if len(new_operands) > 1:
            new_expr = Add(*new_operands)
        elif len(new_operands) == 1:
            new_expr = new_operands[0]
            removed.add(expr)
        else:
            raise ValueError("No operands, should not happen")
        repr_map[expr] = new_expr

    return dirty


def fold_multiply(
    expr: Multiply,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    try:
        const_prod = [next(const_ops)]
        for c in const_ops:
            dirty = True
            const_prod[0] *= c
        if const_prod[0] == 1 * dimensionless:  # TODO make work with all the types
            dirty = True
            const_prod = []
    except StopIteration:
        const_prod = []

    if (
        len(const_prod) == 1 and const_prod[0].magnitude == 0
    ):  # TODO make work with all the types
        dirty = True
        repr_map[expr] = 0 * expr.units
    else:
        if any(m > 1 for m in multiplicity.values()):
            dirty = True
        if dirty:
            copied = {
                n: Mutator.copy_operand_recursively(n, repr_map) for n in multiplicity
            }
            nonconst_power = [
                Power(copied[n], m * dimensionless) if m > 1 else copied[n]
                for n, m in multiplicity.items()
            ]
            new_operands = [
                *nonconst_power,
                *const_prod,
                *(
                    Mutator.copy_operand_recursively(o, repr_map)
                    for o in non_replacable_nonconst_ops
                ),
            ]
            if len(new_operands) > 1:
                new_expr = Multiply(*new_operands)
            elif len(new_operands) == 1:
                new_expr = new_operands[0]
                removed.add(expr)
            else:
                raise ValueError("No operands, should not happen")
            repr_map[expr] = new_expr

    return dirty


def fold_and(
    expr: And,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    const_op_list = list(const_ops)
    if any(not isinstance(o, bool) for o in const_op_list):
        raise ValueError("Or with non-boolean operands")
    if any(not o for o in const_op_list):
        dirty = True
        repr_map[expr] = False
        removed.add(expr)
    elif len(const_op_list) > 0 or any(m > 1 for m in multiplicity.values()):
        new_operands = [
            *(Mutator.copy_operand_recursively(o, repr_map) for o in multiplicity),
            *(
                Mutator.copy_operand_recursively(o, repr_map)
                for o in non_replacable_nonconst_ops
            ),
        ]
        if len(new_operands) > 1:
            new_expr = And(*new_operands)
        elif len(new_operands) == 1:
            new_expr = new_operands[0]
            removed.add(expr)
        else:
            new_expr = True
        repr_map[expr] = new_expr

    return dirty


def fold_or(
    expr: Or,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    const_op_list = list(const_ops)
    if any(not isinstance(o, bool) for o in const_op_list):
        raise ValueError("Or with non-boolean operands")
    if any(o for o in const_op_list):
        dirty = True
        repr_map[expr] = True
        removed.add(expr)
    elif len(const_op_list) > 0 or any(m > 1 for m in multiplicity.values()):
        new_operands = [
            *(Mutator.copy_operand_recursively(o, repr_map) for o in multiplicity),
            *(
                Mutator.copy_operand_recursively(o, repr_map)
                for o in non_replacable_nonconst_ops
            ),
        ]
        if len(new_operands) > 1:
            new_expr = Or(*new_operands)
        elif len(new_operands) == 1:
            new_expr = new_operands[0]
            removed.add(expr)
        else:
            new_expr = False
        repr_map[expr] = new_expr

    return dirty


def fold_pow(
    expr: Power,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    # TODO implement
    return False


def fold_alias(
    expr: Is,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    # TODO implement
    return False


def fold_ge(
    expr: GreaterOrEqual,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    # TODO implement
    return False


def fold_subset(
    expr: IsSubset,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    # TODO implement
    return False


def fold_intersect(
    expr: Intersection,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    # TODO implement
    return False


def fold_union(
    expr: Union,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    # TODO implement
    return False


def fold(
    expr: Expression,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    def get_func[T: Expression](
        expr: T,
    ) -> Callable[
        [
            T,
            Iterable[Literal],
            Counter,
            Iterable[ParameterOperatable],
            Mutator.REPR_MAP,
            set[ParameterOperatable],
        ],
        bool,
    ]:
        # Arithmetic
        # Subtract non-canonical
        if isinstance(expr, Add):
            return fold_add
        elif isinstance(expr, Multiply):
            return fold_multiply
        # Divide non-canonical
        # Sqrt non-canonical
        elif isinstance(expr, Power):
            return fold_pow
        elif isinstance(expr, Log):
            # TODO implement
            return lambda *args: False
        elif isinstance(expr, Abs):
            # TODO implement
            return lambda *args: False
        # Cos non-canonical
        elif isinstance(expr, Sin):
            # TODO implement
            return lambda *args: False
        # Floor non-canonical
        # Ceil non-canonical
        elif isinstance(expr, Round):
            # TODO implement
            return lambda *args: False
        # Logic
        # Xor non-canonical
        # And non-canonical
        # Implies non-canonical
        elif isinstance(expr, Or):
            return fold_or
        # TODO make non-canonical
        elif isinstance(expr, And):
            return fold_and
        # Equality / Inequality
        elif isinstance(expr, Is):
            return fold_alias
        # LessOrEqual non-canonical
        elif isinstance(expr, GreaterOrEqual):
            return fold_ge
        elif isinstance(expr, GreaterThan):
            # TODO implement
            return lambda *args: False
        elif isinstance(expr, IsSubset):
            return fold_subset
        # Sets
        elif isinstance(expr, Intersection):
            return fold_intersect
        elif isinstance(expr, Union):
            return fold_union
        return lambda *args: False

    return get_func(expr)(
        expr,
        const_ops,
        multiplicity,
        non_replacable_nonconst_ops,
        repr_map,
        removed,
    )
