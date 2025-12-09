# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from cmath import pi
from typing import Callable

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


@algorithm("Alias predicates to true", single=True, terminal=False)
def alias_predicates_to_true(mutator: Mutator):
    """
    Alias predicates to True since we need to assume they are true.
    """

    # TODO do we need this? can this go into mutator for all predicates?
    # or alternatively move it to the canonicalize

    for predicate in mutator.get_expressions(required_traits=(is_predicate,)):
        new_predicate = mutator.mutate_expression(predicate)
        mutator.utils.alias_to(
            new_predicate.as_operand.get(),
            mutator.make_lit(True).can_be_operand.get(),
        )


@algorithm("Canonicalize", single=True, terminal=False)
def convert_to_canonical_operations(mutator: Mutator):
    """

    Canonicalize expression types:
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

    Canonicalize literals in expressions and parameters:
    - remove units for NumberLike
    - NumberLike -> Quantity_Interval_Disjoint
    - bool -> BoolSet
    - Enum -> P_Set[Enum]
    """

    UnsupportedOperations: dict[type[fabll.NodeT], type[fabll.NodeT] | None] = {
        GreaterThan: GreaterOrEqual,
        LessThan: LessOrEqual,
        Cardinality: None,
    }
    _UnsupportedOperations = {
        k.bind_typegraph(mutator.tg_in).get_or_create_type().node().get_uuid(): v
        for k, v in UnsupportedOperations.items()
    }

    def c(
        op: type[fabll.NodeT], *operands: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        return mutator.create_expression(
            op,
            *operands,
            from_ops=getattr(c, "from_ops", None),
        ).as_operand.get()

    def curry(e_type: type[fabll.NodeT]):
        def _(*operands: F.Parameters.can_be_operand | F.Literals.LiteralValues):
            _operands = [
                mutator.make_lit(o).can_be_operand.get()
                if not isinstance(o, fabll.Node)
                else o
                for o in operands
            ]
            return c(e_type, *_operands)

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
                mutator.make_lit(0.5).can_be_operand.get(),
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
        Convertible.bind_typegraph(mutator.tg_in)
        .get_or_create_type()
        .node()
        .get_uuid(): (
            Target,
            Converter,
        )
        for Target, Convertible, Converter in MirroredExpressions
    }

    def _strip_units(
        operand: F.Parameters.can_be_operand,
    ) -> F.Parameters.can_be_operand:
        if np := fabll.Traits(operand).get_obj_raw().try_cast(F.Literals.Numbers):
            return (
                np.convert_to_dimensionless(g=mutator.G_transient, tg=mutator.tg_out)
                .is_literal.get()
                .as_operand.get()
            )
        return operand

    # Canonicalize parameters
    for param in mutator.get_parameters_of_type(F.Parameters.NumericParameter):
        mutator.mutate_parameter(
            param.is_parameter.get(),
            # make units dimensionless
            units=mutator.utils.dimensionless(),
        )

    exprs = mutator.get_expressions(sort_by_depth=True)
    for e in exprs:
        e_type = not_none(fabll.Traits(e).get_obj_raw().get_type_node()).node()
        e_type_uuid = e_type.get_uuid()
        e_po = e.as_parameter_operatable.get()
        if e_type_uuid in _UnsupportedOperations:
            replacement = _UnsupportedOperations[e_type_uuid]
            rep = e.compact_repr(mutator.output_print_context)
            if replacement is None:
                logger.warning(f"{type(e)}({rep}) not supported by solver, skipping")
                mutator.remove(e.as_parameter_operatable.get())
                continue

            logger.warning(
                f"{type(e)}({rep}) not supported by solver, converting to {replacement}"
            )

        operands = [_strip_units(o) for o in e.get_operands()]
        from_ops = [e_po]
        # TODO move up, by implementing Parameter Target
        # Min, Max
        if e.isinstance(F.Expressions.Min, F.Expressions.Max):
            p = (
                F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
                .create_instance(mutator.G_out)
                .setup(
                    units=mutator.utils.dimensionless(),
                )
            )
            p_p = p.is_parameter.get()
            p_po = p.is_parameter_operatable.get()
            p_op = p_po.as_operand.get()
            mutator.register_created_parameter(p_p, from_ops=from_ops)
            union = (
                Union.bind_typegraph(mutator.tg_out)
                .create_instance(mutator.G_out)
                .setup(*[mutator.get_copy(o) for o in operands])
            )
            mutator.create_expression(
                IsSubset,
                p_op,
                union.is_expression.get().as_operand.get(),
                from_ops=from_ops,
                assert_=True,
            )
            if e.isinstance(F.Expressions.Min):
                mutator.create_expression(
                    GreaterOrEqual,
                    union.is_expression.get().as_operand.get(),
                    p_op,
                    from_ops=from_ops,
                )
            else:
                mutator.create_expression(
                    GreaterOrEqual,
                    p_op,
                    union.is_expression.get().as_operand.get(),
                    from_ops=from_ops,
                )
            mutator._mutate(e_po, p_po)
            continue

        # Canonical-expressions need to be mutated to strip the units
        if e_type_uuid not in lookup:
            mutator.mutate_expression(e, operands)
            continue

        # Rest
        Target, Converter = lookup[e_type_uuid]

        setattr(c, "from_ops", from_ops)
        mutator.mutate_expression(
            e,
            Converter(operands),
            expression_factory=Target,
            # TODO: copy-pasted this from convert_to_canonical_literals
            # need to ignore existing because non-canonical literals
            # are congruent to canonical
            # ignore_existing=True,
        )
