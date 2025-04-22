# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from cmath import pi
from typing import cast

from faebryk.core.parameter import (
    Add,
    And,
    CanonicalExpression,
    Cardinality,
    Ceil,
    ConstrainableExpression,
    Cos,
    Difference,
    Divide,
    Expression,
    Floor,
    GreaterOrEqual,
    GreaterThan,
    Implies,
    Intersection,
    IsSubset,
    IsSuperset,
    LessOrEqual,
    LessThan,
    Max,
    Min,
    Multiply,
    Not,
    Or,
    Parameter,
    ParameterOperatable,
    Power,
    Round,
    Sin,
    Sqrt,
    Subtract,
    SymmetricDifference,
    Union,
    Xor,
)
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    SolverAllExtended,
    make_lit,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    QuantityLikeR,
)
from faebryk.libs.sets.sets import as_lit
from faebryk.libs.units import dimensionless, quantity
from faebryk.libs.util import cast_assert

logger = logging.getLogger(__name__)

NumericLiteralR = (*QuantityLikeR, Quantity_Interval_Disjoint, Quantity_Interval)


@algorithm("Constrain within and domain", single=True, terminal=False)
def constrain_within_domain(mutator: Mutator):
    """
    Translate domain and within constraints to parameter constraints.
    """

    for param in mutator.nodes_of_type(Parameter):
        new_param = mutator.mutate_parameter(param, override_within=True, within=None)
        if param.within is not None:
            mutator.utils.subset_to(new_param, param.within, from_ops=[param])
        mutator.utils.subset_to(
            new_param,
            param.domain_set(),
            from_ops=[param],
        )


@algorithm("Alias predicates to true", single=True, terminal=False)
def alias_predicates_to_true(mutator: Mutator):
    """
    Alias predicates to True since we need to assume they are true.
    """

    for predicate in mutator.nodes_of_type(ConstrainableExpression):
        if predicate.constrained:
            new_predicate = cast_assert(
                ConstrainableExpression, mutator.mutate_expression(predicate)
            )
            mutator.utils.alias_to(new_predicate, as_lit(True))
            # reset solver flag
            mutator.predicate_reset_termination(new_predicate)


@algorithm("Canonical literal form", single=True, terminal=False)
def convert_to_canonical_literals(mutator: Mutator):
    """
    - remove units for NumberLike
    - NumberLike -> Quantity_Interval_Disjoint
    - bool -> BoolSet
    - Enum -> P_Set[Enum]
    """

    param_ops = mutator.nodes_of_type(ParameterOperatable, sort_by_depth=True)

    for po in param_ops:
        # Parameter
        if isinstance(po, Parameter):
            mutator.mutate_parameter(
                po,
                units=dimensionless,
                soft_set=make_lit(po.soft_set).to_dimensionless()
                if po.soft_set is not None
                else None,
                within=make_lit(po.within).to_dimensionless()
                if po.within is not None
                else None,
                guess=quantity(po.guess, dimensionless)
                if po.guess is not None
                else None,
                override_within=True,
            )

        # Expression
        elif isinstance(po, Expression):

            def mutate(i: int, operand: SolverAllExtended) -> SolverAllExtended:
                if not ParameterOperatable.is_literal(operand):
                    return operand
                lit = make_lit(operand)
                if isinstance(lit, Quantity_Interval_Disjoint):
                    return lit.to_dimensionless()
                return lit

            # need to ignore existing because non-canonical literals
            # are congruent to canonical
            mutator.mutate_expression_with_op_map(po, mutate, ignore_existing=True)


@algorithm("Canonical expression form", single=True, terminal=False)
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

    UnsupportedOperations: dict[type[Expression], type[Expression] | None] = {
        GreaterThan: GreaterOrEqual,
        LessThan: LessOrEqual,
        Cardinality: None,
    }

    def c[T: CanonicalExpression](op: type[T], *operands) -> T:
        return mutator.create_expression(
            op, *operands, from_ops=getattr(c, "from_ops", None)
        )

    def curry(e_type: type[CanonicalExpression]) -> type[Expression]:
        def _(*operands):
            operands = [
                make_lit(o) if not isinstance(o, ParameterOperatable) else o
                for o in operands
            ]
            return c(e_type, *operands)

        # hack
        return cast(type[Expression], _)

    # CanonicalNumeric
    Add_ = curry(Add)
    Multiply_ = curry(Multiply)
    Power_ = curry(Power)
    # Round_ = curry(Round)
    # Abs_ = curry(Abs)
    # Sin_ = curry(Sin)
    # Log_ = curry(Log)

    # CanonicalLogic
    Or_ = curry(Or)
    Not_ = curry(Not)

    # CanonicalSetic
    # Intersection_ = curry(Intersection)
    Union_ = curry(Union)
    SymmetricDifference_ = curry(SymmetricDifference)

    # CanonicalPredicate
    # GreaterOrEqual_ = curry(GreaterOrEqual)
    # IsSubset_ = curry(IsSubset)
    # Is_ = curry(Is)
    # GreaterThan_ = curry(GreaterThan)

    MirroredExpressions = [
        (
            Add,
            Subtract,
            lambda operands: [operands[0]] + [Multiply_(o, -1) for o in operands[1:]],
        ),
        (
            Multiply,
            Divide,
            lambda operands: [operands[0]] + [Power_(o, -1) for o in operands[1:]],
        ),
        (
            Not,
            And,
            lambda operands: [Or_(*[Not_(o) for o in operands])],
        ),
        (
            Or,
            Implies,
            lambda operands: [Not_(operands[0]), *operands[1:]],
        ),
        (
            Not,
            Xor,
            lambda operands: [
                Or_(Not_(Or_(*operands)), Not_(Or_(*[Not_(o) for o in operands])))
            ],
        ),
        (
            Round,
            Floor,
            lambda operands: [Add_(*operands, -0.5)],
        ),
        (
            Round,
            Ceil,
            lambda operands: [Add_(*operands, 0.5)],
        ),
        (
            Sin,
            Cos,
            lambda operands: [Add_(*operands, pi / 2)],
        ),
        (
            Power,
            Sqrt,
            lambda operands: [*operands, make_lit(0.5)],
        ),
        (
            GreaterOrEqual,
            LessOrEqual,
            lambda operands: list(reversed(operands)),
        ),
        (
            # GreaterThan,
            # TODO
            GreaterOrEqual,
            LessThan,
            lambda operands: list(reversed(operands)),
        ),
        # TODO remove once support for LT/GT
        (
            GreaterOrEqual,
            GreaterThan,
            lambda operands: operands,
        ),
        (
            IsSubset,
            IsSuperset,
            lambda operands: list(reversed(operands)),
        ),
        (
            # A - B - C = A - (B | C)
            # = A & (A ^ (B | C))
            Intersection,
            Difference,
            lambda operands: [
                operands[0],
                SymmetricDifference_(operands[0], Union_(*operands)),
            ],
        ),
    ]

    lookup = {
        Convertible: (Target, Converter)
        for Target, Convertible, Converter in MirroredExpressions
    }

    exprs = mutator.nodes_of_type(Expression, sort_by_depth=True)
    for e in exprs:
        if type(e) in UnsupportedOperations:
            replacement = UnsupportedOperations[type(e)]
            if replacement is None:
                logger.warning(
                    f"{type(e)}({e.compact_repr(mutator.print_context)}) not supported "
                    f"by solver, skipping"
                )
                mutator.remove(e)
                continue

            logger.warning(
                f"{type(e)}({e.compact_repr(mutator.print_context)}) not supported "
                f"by solver, converting to {replacement}"
            )

        from_ops = [e]
        # TODO move up, by implementing Parameter Target
        # Min, Max
        if isinstance(e, (Min, Max)):
            p = Parameter(units=e.units)
            mutator.register_created_parameter(p, from_ops=from_ops)
            union = Union(*[mutator.get_copy(o) for o in e.operands])
            mutator.create_expression(
                IsSubset, p, union, from_ops=from_ops, constrain=True
            )
            if isinstance(e, Min):
                mutator.create_expression(GreaterOrEqual, union, p, from_ops=from_ops)
            else:
                mutator.create_expression(GreaterOrEqual, p, union, from_ops=from_ops)
            mutator._mutate(e, p)
            continue

        if type(e) not in lookup:
            continue

        # Rest
        Target, Converter = lookup[type(e)]

        setattr(c, "from_ops", from_ops)
        mutator.mutate_expression(
            e,
            Converter(e.operands),
            expression_factory=Target,
        )
