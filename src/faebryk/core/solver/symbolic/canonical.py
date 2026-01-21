# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from cmath import pi
from typing import Callable

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import (
    ExpressionBuilder,
    MutationMap,
    MutationStage,
    Mutator,
    Transformations,
    solver_relevant,
)
from faebryk.core.solver.utils import S_LOG, MutatorUtils
from faebryk.libs.util import indented_container, not_none

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


def strip_irrelevant(
    g: graph.GraphView,
    tg: fbrk.TypeGraph,
    relevant: list[F.Parameters.can_be_operand],
    print_context: F.Parameters.ReprContext | None,
    iteration: int,
) -> MutationStage:
    g_out, tg_out = MutationMap._bootstrap_copy(g, tg)
    relevant_root_predicates = MutatorUtils.get_relevant_predicates(
        *relevant,
    )
    for root_expr in relevant_root_predicates:
        root_expr.copy_into(g_out)

    nodes_uuids = {p.instance.node().get_uuid() for p in relevant}
    for p_out in fabll.Traits.get_implementors(
        F.Parameters.can_be_operand.bind_typegraph(tg_out)
    ):
        if p_out.instance.node().get_uuid() not in nodes_uuids:
            continue
        fabll.Traits.create_and_add_instance_to(p_out, solver_relevant)

    print_context = print_context or F.Parameters.ReprContext()
    all_ops_out = F.Parameters.is_parameter_operatable.bind_typegraph(
        tg_out
    ).get_instances(g=g_out)

    mapping = {
        F.Parameters.is_parameter_operatable.bind_instance(
            g.bind(node=op.instance.node())
        ): op
        for op in all_ops_out
    }
    # copy over source name
    for p_old, p_new in mapping.items():
        if (p_new_p := p_new.as_parameter.try_get()) is None:
            continue

        print_context.override_name(
            p_new_p,
            fabll.Traits(p_old).get_obj_raw().get_full_name(include_uuid=False),
        )

    if S_LOG:
        logger.debug(
            "Relevant root predicates: "
            + indented_container(
                [
                    p.as_expression.get().compact_repr(
                        context=print_context,
                        no_lit_suffix=True,
                        use_name=True,
                    )
                    for p in relevant_root_predicates
                ]
            )
        )
        expr_count = len(
            fabll.Traits.get_implementors(
                F.Expressions.is_expression.bind_typegraph(tg_out)
            )
        )
        param_count = len(
            fabll.Traits.get_implementors(
                F.Parameters.is_parameter.bind_typegraph(tg_out)
            )
        )
        lit_count = len(
            fabll.Traits.get_implementors(F.Literals.is_literal.bind_typegraph(tg_out))
        )
        logger.debug(
            f"|lits|={lit_count}, |exprs|={expr_count}, |params|={param_count} {g_out}"
        )

    return MutationStage(
        tg_in=tg,
        tg_out=tg_out,
        algorithm="strip_irrelevant",
        iteration=iteration,
        print_ctx=print_context,
        transformations=Transformations(
            print_ctx=print_context,
            mutated=mapping,
        ),
        G_in=g,
        G_out=g_out,
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
        if unit := param.try_get_units():
            assert unit._extract_multiplier() == 1.0, (
                "Parameter units must not use scalar multiplier"
            )
            assert unit._extract_offset() == 0.0, "Parameter units must not use offset"
        # VA allowed, W allowed, mW not allowed
        mutator.mutate_parameter(
            param.is_parameter.get(),
            # make units dimensionless
            # strip domain
        )

    exprs = mutator.get_expressions(sort_by_depth=True)

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
    # Preserve depth-sorted order (important: operands must be processed before parents)
    exprs = [e for e in exprs if e not in unit_exprs_all]
    for u_expr in unit_exprs_all:
        # can disable root check because we never want to repr_map unit expressions
        mutator.remove(u_expr.as_parameter_operatable.get(), no_check_roots=True)

    # Also remove UnitExpression nodes (like As = Ampere*Second).
    # These have is_parameter_operatable trait but aren't expressions or parameters,
    # so they would cause errors during _copy_unmutated.
    for unit_expr in fabll.Traits.get_implementors(
        F.Units.is_unit_expression.bind_typegraph(mutator.tg_in), mutator.G_in
    ):
        mutator.remove(
            unit_expr.get_sibling_trait(F.Parameters.is_parameter_operatable),
            no_check_roots=True,
        )

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

        operands = [_strip_units(o) for o in e.get_operands()]
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
    existing_params: set[F.Parameters.is_parameter],
) -> F.Parameters.is_parameter:
    """
    Selects or creates a parameter to serve as an representative for an expression.
    """

    mutated = {
        k: mutator.get_mutated(k_po)
        for k in existing_params
        if mutator.has_been_mutated((k_po := k.as_parameter_operatable.get()))
    }

    expr_repr = expr.compact_repr(mutator.print_ctx)
    assert len(mutated) <= 1
    if mutated:
        p = next(iter(mutated.values())).as_parameter.force_get()
        logger.debug(
            f"Using mutated {p.compact_repr(mutator.print_ctx)} for {expr_repr}"
        )
    elif existing_params:
        p_old = next(iter(existing_params))
        p = mutator.mutate_parameter(p_old)
        logger.debug(
            f"Using and mutating {p.compact_repr(mutator.print_ctx)} for {expr_repr}"
        )
    else:
        p = expr.create_representative()
        p = mutator.register_created_parameter(
            p,
            from_ops=[expr.as_parameter_operatable.get()],
        )
        logger.debug(
            f"Using created {p.compact_repr(mutator.print_ctx)} for {expr_repr}"
        )

    for p_old in existing_params:
        p_old_po = p_old.as_parameter_operatable.get()
        if mutator.has_been_mutated(p_old_po):
            continue
        mutator._mutate(
            p_old.as_parameter_operatable.get(), p.as_parameter_operatable.get()
        )

    return p


@algorithm("Flatten expressions", single=True, terminal=False)
def flatten_expressions(mutator: Mutator):
    """
    Flatten nested expressions: f(g(A)) -> f(B), B is! g(A)
    """

    for e in mutator.get_expressions(sort_by_depth=True):
        e_po = e.as_parameter_operatable.get()
        e_op = e.as_operand.get()
        aliases = e_op.get_operations(F.Expressions.Is, predicates_only=True)
        # parents = e_op.get_operations() - aliases

        # no aliases for predicates
        if e.try_get_sibling_trait(F.Expressions.is_predicate):
            logger.debug(
                f"No aliases for predicate {e.compact_repr(mutator.print_ctx)}"
            )
            mutator.soft_replace(
                e_po, mutator.make_singleton(True).can_be_operand.get()
            )
            continue

        alias_params = {
            p
            for alias in aliases
            for p in alias.is_expression.get().get_operands_with_trait(
                F.Parameters.is_parameter
            )
        }

        representative = _create_alias_parameter_for_expression(
            mutator, e, existing_params=alias_params
        )
        representative_op = representative.as_operand.get()

        mutator.soft_replace(e_po, representative_op)
        # alias is added by mutate_expression / invariant
