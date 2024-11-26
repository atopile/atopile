# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from cmath import pi

from faebryk.core.graph import GraphFunctions
from faebryk.core.parameter import (
    Add,
    And,
    Ceil,
    Cos,
    Divide,
    Expression,
    Floor,
    GreaterOrEqual,
    GreaterThan,
    Implies,
    IsSubset,
    IsSuperset,
    LessOrEqual,
    LessThan,
    Multiply,
    Not,
    Numbers,
    Or,
    Parameter,
    ParameterOperatable,
    Power,
    Round,
    Sin,
    Sqrt,
    Subtract,
    Xor,
)
from faebryk.core.solver.utils import (
    Mutator,
    NumericLiteralR,
    make_lit,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.units import Quantity, dimensionless, quantity

logger = logging.getLogger(__name__)


def constrain_within_and_domain(mutator: Mutator):
    """
    Translate domain and within constraints to parameter constraints.
    """

    for param in GraphFunctions(mutator.G).nodes_of_type(Parameter):
        new_param = mutator.mutate_parameter(param)
        if new_param.within is not None:
            new_param.constrain_subset(new_param.within)
        if isinstance(new_param.domain, Numbers) and not new_param.domain.negative:
            new_param.constrain_ge(0.0 * new_param.units)


def convert_to_canonical_literals(mutator: Mutator):
    """
    - remove units for NumberLike
    - NumberLike -> Quantity_Interval_Disjoint
    - bool -> BoolSet
    - Enum -> P_Set[Enum]
    """

    param_ops = GraphFunctions(mutator.G).nodes_of_type(ParameterOperatable)

    for po in ParameterOperatable.sort_by_depth(param_ops, ascending=True):
        # Parameter
        if isinstance(po, Parameter):
            mutator.mutate_parameter(
                po,
                units=dimensionless,
                soft_set=Quantity_Interval_Disjoint._from_intervals(
                    Quantity_Interval_Disjoint.from_value(po.soft_set)._intervals,
                    dimensionless,
                )
                if po.soft_set is not None
                else None,
                guess=quantity(po.guess, dimensionless)
                if po.guess is not None
                else None,
            )

        # Expression
        elif isinstance(po, Expression):

            def mutate(
                i: int, operand: ParameterOperatable.All
            ) -> ParameterOperatable.All:
                if isinstance(operand, NumericLiteralR):
                    if isinstance(operand, int | float | Quantity) and not isinstance(
                        operand, bool
                    ):
                        return Quantity_Interval_Disjoint.from_value(
                            quantity(operand, dimensionless)
                        )
                    if isinstance(operand, Quantity_Interval_Disjoint):
                        return Quantity_Interval_Disjoint._from_intervals(
                            operand._intervals, dimensionless
                        )
                    if isinstance(operand, Quantity_Interval):
                        return Quantity_Interval_Disjoint(
                            Quantity_Interval._from_interval(
                                operand._interval, dimensionless
                            )
                        )
                if ParameterOperatable.is_literal(operand):
                    return P_Set.from_value(operand)

                assert isinstance(operand, ParameterOperatable)
                return operand

            mutator.mutate_expression_with_op_map(po, mutate)


def convert_to_canonical_operations(mutator: Mutator):
    """
    Transforms Sub-Add to Add-Add
    ```
    A - B -> A + (-1 * B)
    A / B -> A * B^-1
    A <= B -> B >= A
    A < B -> B > A
    A superset B -> B subset A
    Logic (xor, and, implies) -> Or & Not
    floor/ceil -> round(x -/+ 0.5)
    cos(x) -> sin(x + pi/2)
    sqrt(x) -> x^-0.5
    ```
    """

    MirroredExpressions = [
        (
            Add,
            Subtract,
            lambda operands: [operands[0]]
            + [Multiply(o, make_lit(-1)) for o in operands[1:]],
        ),
        (
            Multiply,
            Divide,
            lambda operands: [operands[0]]
            + [Power(o, make_lit(-1)) for o in operands[1:]],
        ),
        (
            Not,
            And,
            lambda operands: [Or(*map(Not, operands))],
        ),
        (
            Or,
            Implies,
            lambda operands: [Not(operands[0]), *operands[1:]],
        ),
        (
            Not,
            Xor,
            lambda operands: [
                Or(
                    Not(Or(*operands)),
                    Not(Or(*map(Not, operands))),
                )
            ],
        ),
        (
            Round,
            Floor,
            lambda operands: [Add(o, make_lit(-0.5)) for o in operands],
        ),
        (
            Round,
            Ceil,
            lambda operands: [Add(o, make_lit(0.5)) for o in operands],
        ),
        (
            Sin,
            Cos,
            lambda operands: [Add(o, make_lit(pi / 2)) for o in operands],
        ),
        (
            Power,
            Sqrt,
            lambda operands: [*operands, make_lit(-0.5)],
        ),
        (
            GreaterOrEqual,
            LessOrEqual,
            lambda operands: list(reversed(operands)),
        ),
        (
            GreaterThan,
            LessThan,
            lambda operands: list(reversed(operands)),
        ),
        (
            IsSubset,
            IsSuperset,
            lambda operands: list(reversed(operands)),
        ),
    ]

    for Target, Convertible, Converter in MirroredExpressions:
        convertible = {e for e in GraphFunctions(mutator.G).nodes_of_type(Convertible)}

        for expr in ParameterOperatable.sort_by_depth(convertible, ascending=True):
            mutator.mutate_expression(
                expr, Converter(expr.operands), expression_factory=Target
            )
