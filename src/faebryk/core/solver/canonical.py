# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from cmath import pi

from faebryk.core.graph import GraphFunctions
from faebryk.core.parameter import (
    Add,
    And,
    Ceil,
    ConstrainableExpression,
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
    Max,
    Min,
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
    Union,
    Xor,
)
from faebryk.core.solver.utils import (
    CanonicalOperation,
    Mutator,
    NumericLiteralR,
    alias_is_literal,
    make_lit,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.units import Quantity, dimensionless, quantity
from faebryk.libs.util import cast_assert

logger = logging.getLogger(__name__)


def constrain_within_domain(mutator: Mutator):
    """
    Translate domain and within constraints to parameter constraints.
    #TODO: Alias predicates to True since we need to assume they are true.
    """

    for param in GraphFunctions(mutator.G).nodes_of_type(Parameter):
        new_param = mutator.mutate_parameter(param)
        if param.within is not None:
            mutator.create_expression(IsSubset, new_param, param.within).constrain()
        if isinstance(new_param.domain, Numbers) and not new_param.domain.negative:
            mutator.create_expression(
                GreaterOrEqual, new_param, make_lit(quantity(0.0, new_param.units))
            ).constrain()

    for predicate in GraphFunctions(mutator.G).nodes_of_type(ConstrainableExpression):
        if predicate.constrained:
            new_predicate = cast_assert(
                ConstrainableExpression, mutator.mutate_expression(predicate)
            )
            alias_is_literal(new_predicate, True, mutator)
            # reset solver flag
            mutator.mark_predicate_false(new_predicate)


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
    min(x) -> p, p ss x, p le x
    max(x) -> p, p ss x, p ge x
    ```
    """

    def c[T: CanonicalOperation](op: type[T], *operands) -> T:
        return mutator.create_expression(op, *operands)

    MirroredExpressions = [
        (
            Add,
            Subtract,
            lambda operands: [operands[0]]
            + [c(Multiply, o, make_lit(-1)) for o in operands[1:]],
        ),
        (
            Multiply,
            Divide,
            lambda operands: [operands[0]]
            + [c(Power, o, make_lit(-1)) for o in operands[1:]],
        ),
        (
            Not,
            And,
            lambda operands: [c(Or, *[c(Not, o) for o in operands])],
        ),
        (
            Or,
            Implies,
            lambda operands: [c(Not, operands[0]), *operands[1:]],
        ),
        (
            Not,
            Xor,
            lambda operands: [
                c(
                    Or,
                    c(Not, c(Or, *operands)),
                    c(Not, c(Or, *[c(Not, o) for o in operands])),
                )
            ],
        ),
        (
            Round,
            Floor,
            lambda operands: [c(Add, o, make_lit(-0.5)) for o in operands],
        ),
        (
            Round,
            Ceil,
            lambda operands: [c(Add, o, make_lit(0.5)) for o in operands],
        ),
        (
            Sin,
            Cos,
            lambda operands: [c(Add, o, make_lit(pi / 2)) for o in operands],
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

    lookup = {
        Convertible: (Target, Converter)
        for Target, Convertible, Converter in MirroredExpressions
    }

    exprs = GraphFunctions(mutator.G).nodes_of_type(Expression)
    for e in ParameterOperatable.sort_by_depth(exprs, ascending=True):
        # TODO move up, by implementing Parameter Target
        # Min, Max
        if isinstance(e, (Min, Max)):
            p = Parameter(units=e.units)
            mutator.register_created_parameter(p)
            union = Union(*[mutator.get_copy(o) for o in e.operands])
            mutator.create_expression(IsSubset, p, union).constrain()
            if isinstance(e, Min):
                mutator.create_expression(GreaterOrEqual, union, p)
            else:
                mutator.create_expression(GreaterOrEqual, p, union)
            mutator._mutate(e, p)
            continue

        if type(e) not in lookup:
            continue

        # Rest
        Target, Converter = lookup[type(e)]

        mutator.mutate_expression(
            e,
            Converter(e.operands),
            expression_factory=Target,
        )
