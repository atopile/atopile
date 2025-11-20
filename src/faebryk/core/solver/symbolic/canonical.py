# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from cmath import pi
from typing import Callable, cast

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.libs.util import not_none

Add = F.Expressions.Add
And = F.Expressions.And
Cardinality = F.Expressions.Cardinality
Ceil = F.Expressions.Ceil
Cos = F.Expressions.Cos
Difference = F.Expressions.Difference
Divide = F.Expressions.Divide
Floor = F.Expressions.Floor
GreaterOrEqual = F.Expressions.GreaterOrEqual
GreaterThan = F.Expressions.GreaterThan
Implies = F.Expressions.Implies
Intersection = F.Expressions.Intersection
is_predicate = F.Expressions.is_predicate
IsSubset = F.Expressions.IsSubset
IsSuperset = F.Expressions.IsSuperset
LessOrEqual = F.Expressions.LessOrEqual
LessThan = F.Expressions.LessThan
Multiply = F.Expressions.Multiply
Not = F.Expressions.Not
Or = F.Expressions.Or
Power = F.Expressions.Power
Round = F.Expressions.Round
Sin = F.Expressions.Sin
Sqrt = F.Expressions.Sqrt
Subtract = F.Expressions.Subtract
SymmetricDifference = F.Expressions.SymmetricDifference
Union = F.Expressions.Union
Xor = F.Expressions.Xor

logger = logging.getLogger(__name__)

# NumericLiteralR = (*QuantityLikeR, Quantity_Interval_Disjoint, Quantity_Interval)


@algorithm("Constrain within and domain", single=True, terminal=False)
def constrain_within_domain(mutator: Mutator):
    """
    Translate domain and within predicates to parameter predicates.
    """

    for param in mutator.get_parameters_of_type(F.Parameters.NumericParameter):
        p = param.get_trait(F.Parameters.is_parameter)
        po = p.as_parameter_operatable()
        new_param = mutator.mutate_parameter(
            p,
            override_within=True,
            within=None,
        )
        if (within := param.get_within()) is not None:
            mutator.utils.subset_to(
                new_param.as_operand(),
                within.get_trait(F.Parameters.can_be_operand),
                from_ops=[po],
            )
        mutator.utils.subset_to(
            new_param.as_operand(),
            p.domain_set().as_operand(),
            from_ops=[po],
        )


@algorithm("Alias predicates to true", single=True, terminal=False)
def alias_predicates_to_true(mutator: Mutator):
    """
    Alias predicates to True since we need to assume they are true.
    """

    for predicate in mutator.get_expressions(required_traits=(is_predicate,)):
        new_predicate = mutator.mutate_expression(predicate)
        mutator.utils.alias_to(
            new_predicate.get_sibling_trait(F.Parameters.can_be_operand),
            mutator.make_lit(True).get_trait(F.Parameters.can_be_operand),
        )


@algorithm("Canonical literal form", single=True, terminal=False)
def convert_to_canonical_literals(mutator: Mutator):
    """
    - remove units for NumberLike
    - NumberLike -> Quantity_Interval_Disjoint
    - bool -> BoolSet
    - Enum -> P_Set[Enum]
    """

    for param in mutator.get_parameters():
        if (
            np := fabll.Traits(param)
            .get_obj_raw()
            .try_cast(F.Parameters.NumericParameter)
        ):
            mutator.mutate_parameter(
                param,
                units=F.Units.Dimensionless.bind_typegraph(mutator.tg)
                .create_instance(mutator.G_in)
                .get_trait(F.Units.IsUnit),
                soft_set=soft_set.to_dimensionless()
                if (soft_set := np.get_soft_set()) is not None
                else None,
                within=within.to_dimensionless()
                if (within := np.get_within()) is not None
                else None,
                guess=guess.to_dimensionless()
                if (guess := np.get_guess()) is not None
                else None,
                override_within=True,
            )
        else:
            mutator.mutate_parameter(param)

    for expr in mutator.get_expressions(sort_by_depth=True):

        def mutate(
            _: int, operand: F.Parameters.can_be_operand
        ) -> F.Parameters.can_be_operand:
            if np := fabll.Traits(operand).get_obj_raw().try_cast(F.Literals.Numbers):
                return np.to_dimensionless().get_trait(F.Parameters.can_be_operand)
            return operand

        # need to ignore existing because non-canonical literals
        # are congruent to canonical
        mutator.mutate_expression_with_op_map(expr, mutate, ignore_existing=True)


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

    UnsupportedOperations: dict[type[fabll.NodeT], type[fabll.NodeT] | None] = {
        GreaterThan: GreaterOrEqual,
        LessThan: LessOrEqual,
        Cardinality: None,
    }
    _UnsupportedOperations = {
        k.bind_typegraph(mutator.tg).get_or_create_type().node(): v
        for k, v in UnsupportedOperations.items()
    }

    def c[T: fabll.NodeT](op: type[T], *operands: F.Parameters.can_be_operand) -> T:
        return fabll.Traits(
            mutator.create_expression(
                op,
                *operands,
                from_ops=getattr(c, "from_ops", None),
            )
        ).get_obj(op)

    def curry(e_type: type[fabll.NodeT]):
        def _(*operands: F.Parameters.can_be_operand | F.Literals.LiteralValues):
            _operands = [
                mutator.make_lit(o).get_trait(F.Parameters.can_be_operand)
                if not isinstance(o, fabll.Node)
                else o
                for o in operands
            ]
            return c(e_type, *_operands).get_trait(F.Parameters.can_be_operand)

        return _

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

    MirroredExpressions: list[
        tuple[
            type[fabll.NodeT],
            type[fabll.NodeT],
            Callable[
                [list[F.Parameters.can_be_operand]], list[F.Parameters.can_be_operand]
            ],
        ]
    ] = [
        (
            Add,
            Subtract,
            lambda operands: [operands[0], *(Multiply_(o, -1) for o in operands[1:])],
        ),
        (
            Multiply,
            Divide,
            lambda operands: [operands[0], *(Power_(o, -1) for o in operands[1:])],
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
            lambda operands: [
                *operands,
                mutator.make_lit(0.5).get_trait(F.Parameters.can_be_operand),
            ],
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
        Convertible.bind_typegraph(mutator.tg).get_or_create_type().node(): (
            Target,
            Converter,
        )
        for Target, Convertible, Converter in MirroredExpressions
    }

    exprs = mutator.get_typed_expressions(sort_by_depth=True)
    for e in exprs:
        e_expr = e.get_trait(F.Expressions.is_expression)
        e_type = not_none(e.get_type_node()).node()
        if e_type in _UnsupportedOperations:
            replacement = _UnsupportedOperations[e_type]
            rep = e_expr.compact_repr(mutator.print_context)
            if replacement is None:
                logger.warning(f"{type(e)}({rep}) not supported by solver, skipping")
                mutator.remove(e.get_trait(F.Parameters.is_parameter_operatable))
                continue

            logger.warning(
                f"{type(e)}({rep}) not supported by solver, converting to {replacement}"
            )

        from_ops = [e.get_trait(F.Parameters.is_parameter_operatable)]
        # TODO move up, by implementing Parameter Target
        # Min, Max
        if e.isinstance(F.Expressions.Min, F.Expressions.Max):
            p = (
                F.Parameters.NumericParameter.bind_typegraph(mutator.tg)
                .create_instance(mutator.G_out)
                .setup(units=e.get_trait(F.Units.HasUnit).get_unit())
            )
            mutator.register_created_parameter(
                p.get_trait(F.Parameters.is_parameter), from_ops=from_ops
            )
            union = (
                Union.bind_typegraph(mutator.tg)
                .create_instance(mutator.G_out)
                .setup(*[mutator.get_copy(o) for o in e_expr.get_operands()])
            )
            mutator.create_expression(
                IsSubset,
                p.get_trait(F.Parameters.can_be_operand),
                union.get_trait(F.Parameters.can_be_operand),
                from_ops=from_ops,
                assert_=True,
            )
            if e.isinstance(F.Expressions.Min):
                mutator.create_expression(
                    GreaterOrEqual,
                    union.get_trait(F.Parameters.can_be_operand),
                    p.get_trait(F.Parameters.can_be_operand),
                    from_ops=from_ops,
                )
            else:
                mutator.create_expression(
                    GreaterOrEqual,
                    p.get_trait(F.Parameters.can_be_operand),
                    union.get_trait(F.Parameters.can_be_operand),
                    from_ops=from_ops,
                )
            mutator._mutate(
                e.get_trait(F.Parameters.is_parameter_operatable),
                p.get_trait(F.Parameters.is_parameter_operatable),
            )
            continue

        if e_type not in lookup:
            continue

        # Rest
        Target, Converter = lookup[e_type]

        setattr(c, "from_ops", from_ops)
        mutator.mutate_expression(
            e_expr,
            Converter(e_expr.get_operands()),
            expression_factory=Target,
        )
