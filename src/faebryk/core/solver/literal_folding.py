# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from collections.abc import Iterable
from typing import Callable

from faebryk.core.parameter import (
    Add,
    And,
    Divide,
    Expression,
    Multiply,
    Or,
    ParameterOperatable,
    Power,
    Subtract,
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


def fold_subtract(
    expr: Subtract,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    if sum(1 for _ in const_ops) == 2:
        dirty = True
        repr_map[expr] = expr.operands[0] - expr.operands[1]
        removed.add(expr)
    elif expr.operands[0] is expr.operands[1]:  # TODO obv eq, replacable
        dirty = True
        repr_map[expr] = 0 * expr.units
        removed.add(expr)
    elif expr.operands[1] == 0 * expr.operands[1].units:
        dirty = True
        repr_map[expr.operands[0]] = repr_map.get(
            expr.operands[0],
            Mutator.copy_operand_recursively(expr.operands[0], repr_map),
        )
        repr_map[expr] = repr_map[expr.operands[0]]
        removed.add(expr)
    else:
        repr_map[expr] = Mutator.copy_operand_recursively(expr, repr_map)

    return dirty


def fold_divide(
    expr: Divide,
    const_ops: Iterable[Literal],
    multiplicity: Counter,
    non_replacable_nonconst_ops: Iterable[ParameterOperatable],
    repr_map: Mutator.REPR_MAP,
    removed: set[ParameterOperatable],
):
    if sum(1 for _ in const_ops) == 2:
        if not expr.operands[1].magnitude == 0:
            dirty = True
            repr_map[expr] = expr.operands[0] / expr.operands[1]
            removed.add(expr)
        else:
            # no valid solution but might not matter e.g. [phi(a,b,...)
            # OR a/0 == b]
            repr_map[expr] = Mutator.copy_operand_recursively(expr, repr_map)
    elif expr.operands[1] is expr.operands[0]:  # TODO obv eq, replacable
        dirty = True
        repr_map[expr] = 1 * dimensionless
        removed.add(expr)
    elif expr.operands[1] == 1 * expr.operands[1].units:
        dirty = True
        repr_map[expr.operands[0]] = repr_map.get(
            expr.operands[0],
            Mutator.copy_operand_recursively(expr.operands[0], repr_map),
        )
        repr_map[expr] = repr_map[expr.operands[0]]
        removed.add(expr)
    else:
        repr_map[expr] = Mutator.copy_operand_recursively(expr, repr_map)

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
        if isinstance(expr, Add):
            return fold_add
        elif isinstance(expr, Or):
            return fold_or
        elif isinstance(expr, And):
            return fold_and
        elif isinstance(expr, Multiply):
            return fold_multiply
        elif isinstance(expr, Subtract):
            return fold_subtract
        elif isinstance(expr, Divide):
            return fold_divide
        return lambda *args: False

    return get_func(expr)(
        expr,
        const_ops,
        multiplicity,
        non_replacable_nonconst_ops,
        repr_map,
        removed,
    )
