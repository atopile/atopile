# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from cmath import pi
from typing import Callable, Iterable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import ExpressionBuilder, Mutator
from faebryk.core.solver.utils import S_LOG
from faebryk.libs.util import not_none

Add = F.Expressions.Add
And = F.Expressions.And
Cardinality = F.Expressions.Cardinality
Ceil = F.Expressions.Ceil
Cos = F.Expressions.Cos
Divide = F.Expressions.Divide
Floor = F.Expressions.Floor
GreaterOrEqual = F.Expressions.GreaterOrEqual
GreaterThan = F.Expressions.GreaterThan
Implies = F.Expressions.Implies
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
Xor = F.Expressions.Xor

logger = logging.getLogger(__name__)
if S_LOG:
    logger.setLevel(logging.DEBUG)


def _strip_units(
    mutator: Mutator,
    operand: F.Parameters.can_be_operand,
) -> F.Parameters.can_be_operand:
    if np := fabll.Traits(operand).get_obj_raw().try_cast(F.Literals.Numbers):
        return (
            np.convert_to_dimensionless(g=mutator.G_transient, tg=mutator.tg_out)
            .is_literal.get()
            .as_operand.get()
        )
    if (
        numparam := fabll.Traits(operand)
        .get_obj_raw()
        .try_cast(F.Parameters.NumericParameter)
    ):
        if unit := numparam.try_get_units():
            assert unit._extract_multiplier() == 1.0, (
                "Parameter units must not use scalar multiplier"
            )
            assert unit._extract_offset() == 0.0, "Parameter units must not use offset"

    return operand


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
    - remove units for Numbers
    - bool -> BoolSet
    - Enum -> P_Set[Enum]
    - remove unit expressions
    """

    UnsupportedOperations: dict[type[fabll.NodeT], type[fabll.NodeT] | None] = {
        GreaterThan: GreaterOrEqual,
        LessThan: LessOrEqual,
        Cardinality: None,
    }
    _UnsupportedOperations = {
        fabll.TypeNodeBoundTG.get_or_create_type_in_tg(mutator.tg_in, k)
        .node()
        .get_uuid(): v
        for k, v in UnsupportedOperations.items()
    }

    def c(
        op: type[fabll.NodeT], *operands: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand | None:
        return mutator.create_check_and_insert_expression(
            op,
            *operands,
            from_ops=getattr(c, "from_ops", None),
        ).out_operand

    def curry(e_type: type[fabll.NodeT]):
        def _(*operands: F.Parameters.can_be_operand | F.Literals.LiteralValues | None):
            _operands = [
                mutator.make_singleton(o).can_be_operand.get()
                if not isinstance(o, fabll.Node)
                else o
                for o in operands
                if o is not None
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
                [list[F.Parameters.can_be_operand]],
                list[F.Parameters.can_be_operand | None],
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
                mutator.make_singleton(0.5).can_be_operand.get(),
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

    exprs = mutator.get_expressions()

    for e in exprs:
        e_type = not_none(fabll.Traits(e).get_obj_raw().get_type_node()).node()
        e_type_uuid = e_type.get_uuid()
        e_po = e.as_parameter_operatable.get()

        if e_type_uuid in _UnsupportedOperations:
            replacement = _UnsupportedOperations[e_type_uuid]
            rep = e.compact_repr(mutator.print_ctx)
            if replacement is None:
                logger.warning(f"{type(e)}({rep}) not supported by solver, skipping")
                mutator.remove(e.as_parameter_operatable.get())
                continue

            logger.warning(
                f"{type(e)}({rep}) not supported by solver, converting to {replacement}"
            )

        operands = e.get_operands()
        from_ops = [e_po]

        # Canonical-expressions need to be mutated to strip the units
        if e_type_uuid not in lookup:
            mutator.mutate_expression(e, operands)
            continue

        # Rest
        Target, Converter = lookup[e_type_uuid]

        setattr(c, "from_ops", from_ops)
        converted = [op for op in Converter(operands) if op]
        mutator.mutate_expression(
            e,
            converted,
            expression_factory=Target,
            # TODO: copy-pasted this from convert_to_canonical_literals
            # need to ignore existing because non-canonical literals
            # are congruent to canonical
            # ignore_existing=True,
        )


def _create_alias_parameter_for_expression(
    mutator: Mutator,
    expr: F.Expressions.is_expression,
    expr_copy: F.Expressions.is_expression,
    existing_params: set[F.Parameters.is_parameter],
) -> F.Parameters.is_parameter:
    """
    Selects or creates a parameter to serve as an representative for an expression.
    """

    if S_LOG:
        expr_repr = expr.compact_repr(mutator.print_ctx)
    expr_po = expr.as_parameter_operatable.get()

    mutated = {
        k: mutator.get_mutated(k_po)
        for k in existing_params
        if mutator.has_been_mutated((k_po := k.as_parameter_operatable.get()))
    }

    if mutated:
        assert len(mutated) == 1
        p = next(iter(mutated.values())).as_parameter.force_get()
        if S_LOG:
            logger.debug(
                f"Using mutated {p.compact_repr(mutator.print_ctx)} for {expr_repr}"
            )
    elif existing_params:
        p_old = next(iter(existing_params))
        p = mutator.mutate_parameter(p_old)
        if S_LOG:
            logger.debug(
                f"Using and mutating {p.compact_repr(mutator.print_ctx)} for {expr_repr}"
            )
    else:
        p = mutator.register_created_parameter(
            expr_copy.create_representative(alias=False),
            from_ops=[expr_po],
        )
        if S_LOG:
            logger.debug(
                f"Using created {p.compact_repr(mutator.print_ctx)} for {expr_repr}"
            )
    is_expr = mutator._create_and_insert_expression(
        ExpressionBuilder(
            F.Expressions.Is,
            [expr_copy.as_operand.get(), p.as_operand.get()],
            assert_=True,
            terminate=True,
        )
    )
    mutator.transformations.created[is_expr.is_parameter_operatable.get()] = [expr_po]

    for p_old in existing_params:
        p_old_po = p_old.as_parameter_operatable.get()
        if mutator.has_been_mutated(p_old_po):
            continue
        mutator._mutate(
            p_old.as_parameter_operatable.get(), p.as_parameter_operatable.get()
        )

    return p


def _remove_unit_expressions(
    mutator: Mutator, exprs: Iterable[F.Expressions.is_expression]
) -> list[F.Expressions.is_expression]:
    # Filter expressions that compute ON unit types themselves (e.g. Second^1, Ampere*Second). #noqa: E501
    # These have is_unit trait as operands (the unit type IS the operand).
    # NOT expressions like `A is {0.1..0.6}As` where operands HAVE units - those
    # should pass through and have their units stripped by _strip_units().
    unit_computation_leaves = {
        e for e in exprs if e.get_operands_with_trait(F.Units.is_unit)
    }
    unit_exprs_all = {
        parent.get_trait(F.Expressions.is_expression)
        for e in unit_computation_leaves
        for parent in e.as_operand.get().get_operations(recursive=True)
    } | unit_computation_leaves
    exprs = [e for e in exprs if e not in unit_exprs_all]
    for u_expr in unit_exprs_all:
        mutator.remove(u_expr.as_parameter_operatable.get(), no_check_roots=True)

    # Also remove UnitExpression nodes (like As = Ampere*Second).
    # These have is_parameter_operatable trait but aren't expressions or parameters,
    # so they would cause errors during copy_operand.
    for unit_expr in fabll.Traits.get_implementors(
        F.Units.is_unit_expression.bind_typegraph(mutator.tg_in), mutator.G_in
    ):
        mutator.remove(
            unit_expr.get_sibling_trait(F.Parameters.is_parameter_operatable),
            no_check_roots=True,
        )
    return exprs


@algorithm("Flatten expressions", single=True, terminal=False)
def flatten_expressions(mutator: Mutator):
    """
    Flatten nested expressions: f(g(A)) -> f(B), B is! g(A)
    """

    # Don't use standard mutation interfaces here because they will trigger invariant checks

    # Strategy
    # - strip unit expressions
    # - go from leaf expressionsto root
    # - operand map
    #  - strip unit from lits
    #  - map exprs to repr
    #  - copy param (strip unit etc)
    # - copy expr

    exprs = F.Expressions.is_expression.sort_by_depth_expr(mutator.get_expressions())

    exprs = _remove_unit_expressions(mutator, exprs)
    expr_reprs: dict[F.Expressions.is_expression, F.Parameters.can_be_operand] = {}

    def _map_operand(
        mutator: Mutator, o: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        o = _strip_units(mutator, o)
        if o_e := o.try_get_sibling_trait(F.Expressions.is_expression):
            o = expr_reprs[o_e]
        elif (
            o_p := o.try_get_sibling_trait(F.Parameters.is_parameter)
        ) and mutator.has_been_mutated(o_p.as_parameter_operatable.get()):
            return mutator.get_mutated(
                o_p.as_parameter_operatable.get()
            ).as_operand.get()
        return o

    for e in exprs:
        e_po = e.as_parameter_operatable.get()
        e_op = e.as_operand.get()
        # aliases are manually created
        if (
            fabll.Traits(e).get_obj_raw().isinstance(F.Expressions.Is)
            and e.try_get_sibling_trait(F.Expressions.is_predicate)
            and not e.get_operand_literals()
        ):
            continue
        # parents = e_op.get_operations() - aliases
        original_operands = e.get_operands()
        operands = [_map_operand(mutator, o) for o in original_operands]
        e_copy = mutator._mutate(
            e_po,
            mutator._create_and_insert_expression(
                ExpressionBuilder.from_e(e).with_(operands=operands)
            ).is_parameter_operatable.get(),
        ).as_expression.force_get()
        if original_operands == operands:
            mutator.transformations.copied.add(e_po)

        # no aliases for predicates
        if e.try_get_sibling_trait(F.Expressions.is_predicate):
            logger.debug(
                f"No aliases for predicate {e.compact_repr(mutator.print_ctx)}"
            )
            expr_reprs[e] = mutator.make_singleton(True).can_be_operand.get()
            continue

        aliases = e_op.get_operations(F.Expressions.Is, predicates_only=True)
        alias_params = {
            p
            for alias in aliases
            for p in alias.is_expression.get().get_operands_with_trait(
                F.Parameters.is_parameter
            )
        }

        representative_op = _create_alias_parameter_for_expression(
            mutator, e, e_copy, existing_params=alias_params
        ).as_operand.get()

        expr_reprs[e] = representative_op
        # alias is added by mutate_expression / invariant
