# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from dataclasses import dataclass

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.symbolic.pure_literal import (
    exec_pure_literal_operands,
)
from faebryk.core.solver.utils import Contradiction, MutatorUtils
from faebryk.libs.util import OrderedSet

logger = logging.getLogger(__name__)

Add = F.Expressions.Add
GreaterOrEqual = F.Expressions.GreaterOrEqual
Is = F.Expressions.Is
IsSubset = F.Expressions.IsSubset
Multiply = F.Expressions.Multiply
Power = F.Expressions.Power

# TODO: mark terminal=False where applicable


@algorithm("Transitive subset", terminal=False)
def transitive_subset(mutator: Mutator):
    """
    ```
    A ss! B, B ss! C -> new A ss! C
    B not lit
    ```
    """

    # NOTE: if we hit X ss! A ss! Y, it will create X ss! Y which is only useful
    #   for contradiction checking.
    # The invariant helper will make sure to terminate that expression and keep it
    #  in the graph so we don't keep on creating it.

    # for all A ss! B | B not lit
    for ss in mutator.get_typed_expressions(
        F.Expressions.IsSubset,
        include_terminated=True,
        required_traits=(F.Expressions.is_predicate,),
    ):
        ss_e = ss.is_expression.get()
        A, B = ss_e.get_operands()
        if not (B_po := B.as_parameter_operatable.try_get()):
            continue

        # all B ss! C
        for C, e in mutator.utils.get_op_supersets(B_po).items():
            # performance optimization
            if C.is_same(A):
                continue
            # create A ss! C
            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                A,
                C,
                from_ops=[
                    ss.is_parameter_operatable.get(),
                    e.is_parameter_operatable.get(),
                ],
                assert_=True,
            )


# Terminal -----------------------------------------------------------------------------
@algorithm("Remove unconstrained", terminal=True)
def remove_unconstrained(mutator: Mutator):
    """
    Remove all expressions that are not involved in any predicates
    or expressions with side effects
    Note: Not possible for Parameters, want to keep those around for REPR
    """
    # TODO rebuild
    return


@algorithm("Predicate unconstrained operands deduce", terminal=True)
def predicate_unconstrained_operands_deduce(mutator: Mutator):
    """
    A op! B | A or B unconstrained -> A op!$ B
    """
    # TODO rebuild (get_expressions_involved_in doesn't work that easily like this)
    # need to take classes into account
    return
    # TODO make generator

    # test for this exists in test_solver_util.py
    def get_expressions_involved_in[T: fabll.NodeT](
        p: F.Parameters.is_parameter_operatable,
        type_filter: type[T] = fabll.Node,
        include_root: bool = False,
        up_only: bool = True,
        require_trait: type[fabll.NodeT] | None = None,
    ) -> OrderedSet[T]:
        dependants = p.get_operations(recursive=True)
        if e := p.as_expression.try_get():
            if include_root:
                dependants.add(fabll.Traits(e).get_obj_raw())

            if not up_only:
                dependants.update(
                    fabll.Traits(op).get_obj_raw()
                    for op in e.get_operands_with_trait(
                        F.Expressions.is_expression, recursive=True
                    )
                )

        res: OrderedSet[T] = OrderedSet(
            t
            for p in dependants
            if (t := p.try_cast(type_filter))
            and (not require_trait or p.has_trait(require_trait))
        )
        return res

    def get_predicates_involved_in[T: fabll.NodeT](
        p: F.Parameters.is_parameter_operatable,
        type_filter: type[T] = fabll.Node,
    ) -> OrderedSet[T]:
        return MutatorUtils.get_expressions_involved_in(
            p, type_filter, require_trait=F.Expressions.is_predicate
        )

    def no_other_predicates(
        po: F.Parameters.is_parameter_operatable,
        *other: F.Expressions.is_assertable,
        unfulfilled_only: bool = False,
    ) -> bool:
        no_other_predicates = (
            len(
                [
                    x
                    for x in get_predicates_involved_in(po).difference(other)
                    if not unfulfilled_only
                    or not (
                        (expr := x.try_get_trait(F.Expressions.is_expression))
                        and mutator.is_terminated(expr)
                    )
                ]
            )
            == 0
        )
        return no_other_predicates and not po.has_implicit_predicates_recursive()

    preds = mutator.get_expressions(required_traits=(F.Expressions.is_predicate,))
    for p_e in preds:
        if mutator.utils.is_literal_expression(p_e.as_operand.get()):
            continue

        for op in p_e.get_operand_operatables():
            if no_other_predicates(
                op,
                p_e.as_assertable.force_get(),
                unfulfilled_only=True,
            ):
                mutator.terminate(p_e)
                break


# Estimation algorithms ----------------------------------------------------------------


def _fold_pure_literal_exprs(
    mutator: Mutator,
    expr_e: F.Expressions.is_expression,
    mapped_operands: list[F.Parameters.can_be_operand],
) -> F.Literals.is_literal | None:
    # Theoretically this is a shortcut, since invariants should deal with this.
    # But either that's generally not possible without the context or I'm too stupid
    # to implement it. So we rely on this shortcut for now.
    return exec_pure_literal_operands(
        mutator.G_transient,
        mutator.tg_in,
        mutator.utils.hack_get_expr_type(expr_e),
        mapped_operands,
    )


@algorithm("Upper estimation", terminal=False)
def upper_estimation_of_expressions_with_supersets(mutator: Mutator):
    """
    If any operand in an expression has a superset literal,
    we can estimate the expression to the function applied to the superset literals.

    ```
    f(A{⊆|X}, B{⊆|Y}, C, ...)
        => f(A{⊆|X}, B{⊆|Y}, C, Z, ...) ⊆! f(X, Y, C, Z, ...)

    ```
    - f not setic
    - X,Y not singleton
    """

    supersetted_ops = {
        subset_po.as_operand.get(): lit_superset
        for ss in mutator.get_typed_expressions(
            F.Expressions.IsSubset,
            required_traits=(F.Expressions.is_predicate,),
            include_terminated=True,
        )
        if (lit_superset := ss.get_superset_operand().as_literal.try_get())
        and (
            subset_po := (
                subset_op := ss.get_subset_operand()
            ).as_parameter_operatable.try_get()
        )
        # singletons get taken care of by
        # `convert_operable_aliased_to_single_into_literal`
        and not mutator.utils.is_correlatable_literal(lit_superset)
        # TODO theoretically not possible with invariants
        and not mutator.utils.is_literal_expression(subset_op)
    }

    exprs = {
        e
        for op in supersetted_ops.keys()
        for e in mutator.get_operations(op.as_parameter_operatable.force_get())
        # setic expressions can't get subset estimated
        if not e.has_trait(F.Expressions.is_setic)
    }

    for expr in exprs:
        expr_e = expr.get_trait(F.Expressions.is_expression)
        operands = expr_e.get_operands()
        # check if any operand has a superset literal
        mapped_operands = [
            supersetted_ops[op].as_operand.get() if op in supersetted_ops else op
            for op in operands
        ]
        if mapped_operands == operands:
            continue

        expr_po = expr.get_trait(F.Parameters.is_parameter_operatable)
        from_ops = [expr_po]

        if all(mutator.utils.is_literal(op) for op in mapped_operands):
            out = _fold_pure_literal_exprs(mutator, expr_e, mapped_operands)
        else:
            # Make new expr with subset literals
            res = mutator.create_check_and_insert_expression(
                mutator.utils.hack_get_expr_type(expr_e),
                *mapped_operands,
                from_ops=from_ops,
                allow_uncorrelated_congruence_match=True,
            )
            out = res.out

        if out is None:
            continue

        expr_superset = out.as_operand.get()

        # Subset old expr to subset estimated one
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            expr_e.as_operand.get(),
            expr_superset,
            from_ops=from_ops,
            assert_=True,
        )


@dataclass(frozen=True)
class _UncertaintySummary:
    outer: F.Literals.Numbers
    low: F.Literals.Numbers
    high: F.Literals.Numbers
    count: int

    @classmethod
    def from_outer(
        cls, mutator: Mutator, outer: F.Literals.Numbers, *, uncertainty: bool = False
    ) -> "_UncertaintySummary":
        nums = F.Literals.Numbers.bind_typegraph(tg=mutator.tg_in)
        return cls(
            outer=outer,
            low=nums.create_instance(g=mutator.G_transient).setup_from_singleton(
                value=outer.get_max_value() if uncertainty else outer.get_min_value(),
                unit=outer.get_is_unit(),
            ),
            high=nums.create_instance(g=mutator.G_transient).setup_from_singleton(
                value=outer.get_min_value() if uncertainty else outer.get_max_value(),
                unit=outer.get_is_unit(),
            ),
            count=int(uncertainty),
        )


def _numeric_parameter(po: F.Parameters.is_parameter_operatable):
    param = po.as_parameter.try_get()
    return (
        None
        if param is None
        else fabll.Traits(param).get_obj_raw().try_cast(F.Parameters.NumericParameter)
    )


def _represented_expression(
    operand: F.Parameters.can_be_operand, *, exclude_eq: F.Expressions.Is | None = None
) -> F.Expressions.is_expression | None:
    if (expr := _direct_expression(operand)) is not None:
        return expr
    if operand.as_parameter_operatable.try_get() is None:
        return None
    for is_ in operand.get_operations(F.Expressions.Is, predicates_only=True):
        if exclude_eq is not None and is_.is_same(exclude_eq):
            continue
        eq = is_.is_expression.get()
        params = eq.get_operands_with_trait(F.Parameters.is_parameter)
        exprs = [
            expr
            for expr in eq.get_operands_with_trait(F.Expressions.is_expression)
            if not expr.has_trait(F.Expressions.is_predicate)
        ]
        if len(params) == len(exprs) == 1 and next(
            iter(params)
        ).as_operand.get().is_same(operand):
            return exprs[0]
    return None


def _direct_expression(operand: F.Parameters.can_be_operand):
    expr = operand.try_get_sibling_trait(F.Expressions.is_expression)
    return None if expr is None or expr.has_trait(F.Expressions.is_predicate) else expr


def _summarize_uncertainty(
    mutator: Mutator,
    operand: F.Parameters.can_be_operand,
    seen: tuple[F.Parameters.can_be_operand, ...] = (),
):
    if literal := MutatorUtils.is_numeric_literal(operand):
        return _UncertaintySummary.from_outer(mutator, literal)
    po = operand.as_parameter_operatable.try_get()
    if po is None:
        return None
    if subset := MutatorUtils.is_numeric_literal(po.try_extract_subset()):
        return _UncertaintySummary.from_outer(mutator, subset, uncertainty=True)
    outer = MutatorUtils.is_numeric_literal(po.try_extract_superset()) or (
        numeric_param.domain_set(g=mutator.G_transient, tg=mutator.tg_in)
        if (numeric_param := _numeric_parameter(po))
        else None
    )
    if any(prev.is_same(operand) for prev in seen):
        return None if outer is None else _UncertaintySummary.from_outer(mutator, outer)
    if expr := _represented_expression(operand):
        if summary := _summarize_uncertainty_expression(
            mutator, expr, (*seen, operand)
        ):
            return summary
    return None if outer is None else _UncertaintySummary.from_outer(mutator, outer)


def _summarize_uncertainty_expression(
    mutator: Mutator,
    expr: F.Expressions.is_expression,
    seen: tuple[F.Parameters.can_be_operand, ...] = (),
):
    parts = [_summarize_uncertainty(mutator, op, seen) for op in expr.get_operands()]
    if any(part is None for part in parts):
        return None
    parts = [part for part in parts if part]

    if expr.expr_isinstance(Power):
        exponent = (
            MutatorUtils.is_numeric_literal(expr.get_operands()[1])
            if len(expr.get_operands()) == 2
            else None
        )
        base = (
            parts[0]
            if exponent and exponent.is_singleton() and exponent.get_single() == -1
            else None
        )
        if (
            base is None
            or base.outer.get_min_value() <= 0
            or not math.isfinite(base.outer.get_min_value())
            or not math.isfinite(base.outer.get_max_value())
        ):
            return None
        outer = base.outer.op_invert(g=mutator.G_transient, tg=mutator.tg_in)
        return _UncertaintySummary(
            outer=outer,
            low=base.high.op_invert(g=mutator.G_transient, tg=mutator.tg_in),
            high=base.low.op_invert(g=mutator.G_transient, tg=mutator.tg_in),
            count=base.count,
        )

    if not expr.expr_isinstance(Add) and not expr.expr_isinstance(Multiply):
        return None
    if sum(part.count for part in parts) > 1:
        return None
    valid = (
        (
            lambda n: (
                math.isfinite(n.get_min_value()) and math.isfinite(n.get_max_value())
            )
        )
        if expr.expr_isinstance(Add)
        else (
            lambda n: (
                n.get_min_value() > 0
                and math.isfinite(n.get_min_value())
                and math.isfinite(n.get_max_value())
            )
        )
    )
    if not all(valid(part.outer) for part in parts):
        return None
    op = (
        F.Literals.Numbers.op_add_intervals
        if expr.expr_isinstance(Add)
        else F.Literals.Numbers.op_mul_intervals
    )
    outer = op(
        parts[0].outer,
        *(part.outer for part in parts[1:]),
        g=mutator.G_transient,
        tg=mutator.tg_in,
    )
    if all(part.count == 0 for part in parts):
        return _UncertaintySummary.from_outer(mutator, outer)
    low, high = next((part.low, part.high) for part in parts if part.count == 1)
    for part in parts:
        if part.count == 1:
            continue
        nums = F.Literals.Numbers.bind_typegraph(tg=mutator.tg_in)
        low = op(
            low,
            nums.create_instance(g=mutator.G_transient).setup_from_singleton(
                value=part.outer.get_min_value(), unit=part.outer.get_is_unit()
            ),
            g=mutator.G_transient,
            tg=mutator.tg_in,
        )
        high = op(
            high,
            nums.create_instance(g=mutator.G_transient).setup_from_singleton(
                value=part.outer.get_max_value(), unit=part.outer.get_is_unit()
            ),
            g=mutator.G_transient,
            tg=mutator.tg_in,
        )
    return _UncertaintySummary(outer=outer, low=low, high=high, count=1)


def _depends_on_target(
    target_op: F.Parameters.can_be_operand, expr: F.Expressions.is_expression
):
    from faebryk.core.solver.symbolic.invariants import AliasClass

    target_aliases = [
        alias.as_operand.get()
        for alias in AliasClass.of(target_op, allow_non_repr=True).get_with_trait(
            F.Parameters.is_parameter
        )
    ]
    if not target_aliases:
        return False

    seen: list[F.Parameters.can_be_operand] = []
    stack = list(expr.get_operands())
    while stack:
        operand = stack.pop()
        if any(alias.is_same(operand) for alias in target_aliases):
            return True
        if any(prev.is_same(operand) for prev in seen):
            continue
        seen.append(operand)
        if nested := _represented_expression(operand):
            stack.extend(nested.get_operands())
    return False


def _is_input_parameter_target(
    mutator: Mutator, po: F.Parameters.is_parameter_operatable
) -> bool:
    return any(
        source in mutator.mutation_map.input_operables
        and source.as_parameter.try_get() is not None
        for source in mutator.mutation_map.map_backward(po)
    )


@algorithm("Uncertainty estimation", terminal=False)
def uncertainty_estimation_single_source(mutator: Mutator):
    """
    Derive a safe outer bound for a parameter from a canonical expression tree with a
    single uncertainty leaf.
    """

    for eq in mutator.get_typed_expressions(
        F.Expressions.Is,
        required_traits=(F.Expressions.is_predicate,),
        include_terminated=True,
    ):
        operands = eq.is_expression.get().get_operands()
        targets = [
            (operand, po)
            for operand in operands
            if _direct_expression(operand) is None
            and (po := operand.as_parameter_operatable.try_get())
            and _numeric_parameter(po)
        ]
        rhs_exprs = []
        for operand in operands:
            if not (expr := _direct_expression(operand)):
                continue
            if any(expr.is_same(prev) for prev in rhs_exprs):
                continue
            rhs_exprs.append(expr)
        if len(targets) != 1 or not rhs_exprs:
            continue

        target_op, target_po = targets[0]
        if target_po.try_extract_subset() is not None:
            continue
        if not _is_input_parameter_target(mutator, target_po):
            continue
        upper = MutatorUtils.is_numeric_literal(target_po.try_extract_superset())
        if upper is None and (numeric_param := _numeric_parameter(target_po)):
            upper = numeric_param.domain_set(g=mutator.G_transient, tg=mutator.tg_in)
        candidate = None
        for rhs_expr in rhs_exprs:
            if _depends_on_target(target_op, rhs_expr):
                continue
            summary = _summarize_uncertainty_expression(mutator, rhs_expr)
            if (
                summary is None
                or summary.count != 1
                or summary.low.get_min_value() > summary.high.get_max_value()
            ):
                continue
            rhs_candidate = (
                F.Literals.Numbers.bind_typegraph(tg=mutator.tg_in)
                .create_instance(g=mutator.G_transient)
                .setup_from_min_max(
                    min=summary.low.get_min_value(),
                    max=summary.high.get_max_value(),
                    unit=summary.low.get_is_unit(),
                )
            )
            candidate = (
                rhs_candidate
                if candidate is None
                else fabll.Traits(
                    candidate.is_literal.get().op_setic_intersect(
                        rhs_candidate.is_literal.get(),
                        g=mutator.G_transient,
                        tg=mutator.tg_in,
                    )
                ).get_obj(F.Literals.Numbers)
            )
        if candidate is None:
            continue
        if upper is not None:
            candidate = fabll.Traits(
                candidate.is_literal.get().op_setic_intersect(
                    upper.is_literal.get(),
                    g=mutator.G_transient,
                    tg=mutator.tg_in,
                )
            ).get_obj(F.Literals.Numbers)
        if candidate.is_empty():
            raise Contradiction(
                "Uncertainty lower bound not contained in target upper bound",
                involved=[eq.get_trait(F.Parameters.is_parameter_operatable)],
                mutator=mutator,
            )
        if (
            upper is not None
            and candidate.op_setic_is_subset_of(
                upper, g=mutator.G_transient, tg=mutator.tg_in
            )
            and upper.op_setic_is_subset_of(
                candidate, g=mutator.G_transient, tg=mutator.tg_in
            )
        ):
            continue
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            target_op,
            candidate.is_literal.get().as_operand.get(),
            from_ops=[eq.get_trait(F.Parameters.is_parameter_operatable)],
            assert_=True,
        )


@algorithm("Correlated contradiction", terminal=False)
def correlated_contradiction(mutator: Mutator):
    """
    Detect Anticorrelated(A,B) + Not(Anticorrelated(A,B)) both predicates.

    If an Anticorrelated expression is asserted and also wrapped in a Not that is itself
    asserted, the two assertions contradict each other.
    """

    Anticorrelated = F.Expressions.Anticorrelated
    Not = F.Expressions.Not
    is_predicate = F.Expressions.is_predicate

    for corr in mutator.get_typed_expressions(
        Anticorrelated, include_terminated=False, include_irrelevant=False
    ):
        corr_e = corr.get_trait(F.Expressions.is_expression)
        if not corr_e.try_get_sibling_trait(is_predicate):
            continue
        corr_op = corr.get_trait(F.Parameters.can_be_operand)
        for not_expr in corr_op.get_operations(
            types=Not, recursive=False, predicates_only=False
        ):
            if not_expr.has_trait(is_predicate):
                raise Contradiction(
                    "Anticorrelated and Not(Anticorrelated) both asserted",
                    involved=[
                        corr_op.as_parameter_operatable.force_get(),
                        not_expr.get_trait(F.Parameters.is_parameter_operatable),
                    ],
                    mutator=mutator,
                )
