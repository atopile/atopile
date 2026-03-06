# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import math
from dataclasses import dataclass

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator, is_simplification_target
from faebryk.core.solver.symbolic.invariants import AliasClass
from faebryk.core.solver.symbolic.pure_literal import (
    exec_pure_literal_operands,
)
from faebryk.core.solver.utils import Contradiction, MutatorUtils

Add = F.Expressions.Add
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
    """
    Summary of an operand under uncertainty-source semantics.

    `outer` is the ordinary interval image of the operand.
    `robust_min/robust_max` encode the interval common to every realization of the
    single uncertainty source flowing through this summary. For exact operands this
    is just `[min(outer), max(outer)]`. For uncertainty sources we reverse the
    endpoints so later `max(min), min(max)` intersections compute the robust overlap
    rather than the forward image.
    """

    outer: F.Literals.Numbers
    robust_min: float
    robust_max: float
    source_count: int

    @classmethod
    def from_outer(
        cls, outer: F.Literals.Numbers, source_count: int = 0
    ) -> "_UncertaintySummary":
        if outer.is_empty():
            return cls(
                outer=outer,
                robust_min=math.inf,
                robust_max=-math.inf,
                source_count=source_count,
            )
        robust_min = outer.get_min_value()
        robust_max = outer.get_max_value()
        if source_count == 1:
            robust_min, robust_max = robust_max, robust_min
        return cls(
            outer=outer,
            robust_min=robust_min,
            robust_max=robust_max,
            source_count=source_count,
        )

    @property
    def is_empty(self) -> bool:
        return self.outer.is_empty() or self.robust_min > self.robust_max

    @property
    def is_finite(self) -> bool:
        return (
            not self.outer.is_empty()
            and math.isfinite(self.outer.get_min_value())
            and math.isfinite(self.outer.get_max_value())
        )

    @classmethod
    def intersect(
        cls,
        mutator: Mutator,
        *summaries: "_UncertaintySummary",
        outer: F.Literals.Numbers | None = None,
    ) -> "_UncertaintySummary":
        merged_outer = summaries[0].outer
        for summary in summaries[1:]:
            merged_outer = fabll.Traits(
                merged_outer.is_literal.get().op_setic_intersect(
                    summary.outer.is_literal.get(),
                    g=mutator.G_transient,
                    tg=mutator.tg_in,
                )
            ).get_obj(F.Literals.Numbers)
        if outer is not None:
            merged_outer = fabll.Traits(
                merged_outer.is_literal.get().op_setic_intersect(
                    outer.is_literal.get(),
                    g=mutator.G_transient,
                    tg=mutator.tg_in,
                )
            ).get_obj(F.Literals.Numbers)
        return cls(
            outer=merged_outer,
            robust_min=max(summary.robust_min for summary in summaries),
            robust_max=min(summary.robust_max for summary in summaries),
            source_count=max(summary.source_count for summary in summaries),
        )


def _summarize_uncertainty_operand(
    mutator: Mutator,
    operand: F.Parameters.can_be_operand,
    seen: tuple[F.Parameters.can_be_operand, ...] = (),
):
    if literal := MutatorUtils.is_numeric_literal(operand):
        return _UncertaintySummary.from_outer(literal)
    if not (po := operand.as_parameter_operatable.try_get()):
        return None
    if subset := MutatorUtils.is_numeric_literal(mutator.utils.try_extract_subset(po)):
        return _UncertaintySummary.from_outer(subset, source_count=1)

    outer = MutatorUtils.is_numeric_literal(
        mutator.utils.try_extract_superset(po, domain_default=True)
    )
    if (
        outer is not None
        and math.isfinite(outer.get_min_value())
        and math.isfinite(outer.get_max_value())
    ):
        return _UncertaintySummary.from_outer(outer)
    if seen:
        return None if outer is None else _UncertaintySummary.from_outer(outer)

    alias_class = AliasClass.of(operand)
    target_rep = alias_class.representative()
    summaries = []
    for expr in alias_class.get_with_trait(F.Expressions.is_expression):
        if expr.has_trait(F.Expressions.is_predicate):
            continue
        if any(
            target_rep.is_same(leaf.as_operand.get())
            for leaf in expr.get_operand_leaves_operatable()
        ):
            continue
        summary = _summarize_uncertainty_expression(
            mutator,
            expr,
            (*seen, operand),
        )
        if summary is not None:
            summaries.append(summary)
    if summaries:
        return _UncertaintySummary.intersect(mutator, *summaries, outer=outer)
    return None if outer is None else _UncertaintySummary.from_outer(outer)


def _summarize_uncertainty_expression(
    mutator: Mutator,
    expr: F.Expressions.is_expression,
    seen: tuple[F.Parameters.can_be_operand, ...] = (),
):
    operands = expr.get_operands()
    parts: list[_UncertaintySummary] = []
    for op in operands:
        if not (part := _summarize_uncertainty_operand(mutator, op, seen=seen)):
            return None
        parts.append(part)

    if expr.expr_isinstance(Power):
        exponent = (
            MutatorUtils.is_numeric_literal(operands[1]) if len(operands) == 2 else None
        )
        base = (
            parts[0]
            if exponent and exponent.is_singleton() and exponent.get_single() == -1
            else None
        )
        if (
            base is None
            or not base.is_finite
            or base.outer.get_min_value() <= 0
            or base.robust_min <= 0
            or base.robust_max <= 0
        ):
            return None
        return _UncertaintySummary.from_outer(
            base.outer.op_invert(g=mutator.G_transient, tg=mutator.tg_in),
            source_count=base.source_count,
        )

    if expr.expr_isinstance(Add):
        expr_t = Add
    elif expr.expr_isinstance(Multiply):
        expr_t = Multiply
    else:
        return None

    uncertain = sum(part.source_count for part in parts)
    if uncertain > 1 or not all(part.is_finite for part in parts):
        return None

    outer = exec_pure_literal_operands(
        mutator.G_transient,
        mutator.tg_in,
        expr_t,
        [part.outer.is_literal.get().as_operand.get() for part in parts],
    )
    assert outer is not None
    outer = fabll.Traits(outer).get_obj(F.Literals.Numbers)
    if uncertain == 0:
        return _UncertaintySummary.from_outer(outer)

    moving = next(part for part in parts if part.source_count == 1)
    fixed = [part.outer for part in parts if part.source_count == 0]
    if not fixed:
        return _UncertaintySummary(
            outer=outer,
            robust_min=moving.robust_min,
            robust_max=moving.robust_max,
            source_count=1,
        )

    fixed_outer = exec_pure_literal_operands(
        mutator.G_transient,
        mutator.tg_in,
        expr_t,
        [outer.is_literal.get().as_operand.get() for outer in fixed],
    )
    assert fixed_outer is not None
    fixed_outer = fabll.Traits(fixed_outer).get_obj(F.Literals.Numbers)
    if expr_t is Add:
        return _UncertaintySummary(
            outer=outer,
            robust_min=moving.robust_min + fixed_outer.get_min_value(),
            robust_max=moving.robust_max + fixed_outer.get_max_value(),
            source_count=1,
        )
    if fixed_outer.get_min_value() > 0:
        return _UncertaintySummary(
            outer=outer,
            robust_min=moving.robust_min * fixed_outer.get_min_value(),
            robust_max=moving.robust_max * fixed_outer.get_max_value(),
            source_count=1,
        )
    if fixed_outer.get_max_value() < 0:
        return _UncertaintySummary(
            outer=outer,
            robust_min=moving.robust_max * fixed_outer.get_min_value(),
            robust_max=moving.robust_min * fixed_outer.get_max_value(),
            source_count=1,
        )
    return None


@algorithm("Uncertainty estimation", terminal=False)
def uncertainty_estimation_single_source(mutator: Mutator):
    """
    Derive a robust upper bound for a simplification target from a single lower
    bound uncertainty source in one of its aliased expressions.

    If a target is related to an uncertainty source `U` through `target = f(...)`,
    this computes `target ⊆ ⋂_{u in U} f(u, Q)` where `Q` are the ordinary outer
    bounds of the remaining operands. Unsupported expressions or multiple
    uncertainty sources are skipped.
    """

    is_predicate = F.Expressions.is_predicate
    for target_po in mutator.get_parameter_operatables():
        if target_po.try_get_sibling_trait(is_simplification_target) is None:
            continue
        if mutator.utils.try_extract_subset(target_po) is not None:
            continue
        outer = MutatorUtils.is_numeric_literal(
            mutator.utils.try_extract_superset(target_po, domain_default=True)
        )
        if outer is None:
            continue
        target_op = target_po.as_operand.get()
        alias_class = AliasClass.of(target_op)
        target_rep = alias_class.representative()
        summaries = []
        for expr in alias_class.get_with_trait(F.Expressions.is_expression):
            if expr.has_trait(is_predicate):
                continue
            if any(
                target_rep.is_same(leaf.as_operand.get())
                for leaf in expr.get_operand_leaves_operatable()
            ):
                continue
            summary = _summarize_uncertainty_expression(mutator, expr)
            if (
                summary is not None
                and summary.source_count == 1
                and not summary.is_empty
            ):
                summaries.append(summary)
        if not summaries:
            continue
        candidate = _UncertaintySummary.intersect(mutator, *summaries, outer=outer)
        if candidate.is_empty:
            raise Contradiction(
                "Uncertainty lower bound not contained in target upper bound",
                involved=[target_po],
                mutator=mutator,
            )
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            target_op,
            mutator.utils.make_number_literal_from_range(
                candidate.robust_min,
                candidate.robust_max,
            )
            .is_literal.get()
            .as_operand.get(),
            from_ops=[target_po],
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
