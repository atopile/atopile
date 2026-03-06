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
    robust_low: F.Literals.Numbers
    robust_high: F.Literals.Numbers
    uncertainty_leaf_count: int


def _try_get_numbers_literal(
    operand: F.Parameters.can_be_operand,
) -> F.Literals.Numbers | None:
    if not (lit := operand.as_literal.try_get()):
        return None
    return fabll.Traits(lit).get_obj_raw().try_cast(F.Literals.Numbers)


def _try_get_numeric_parameter(
    po: F.Parameters.is_parameter_operatable,
) -> F.Parameters.NumericParameter | None:
    if not (param := po.as_parameter.try_get()):
        return None
    return fabll.Traits(param).get_obj_raw().try_cast(F.Parameters.NumericParameter)


def _try_get_expression_representative(
    operand: F.Parameters.can_be_operand,
) -> F.Expressions.is_expression | None:
    if direct := operand.try_get_sibling_trait(F.Expressions.is_expression):
        return direct

    if not (po := operand.as_parameter_operatable.try_get()):
        return None
    if not (param := po.as_parameter.try_get()):
        return None
    if _try_get_numeric_parameter(po) is None:
        return None
    if not param.try_get_sibling_trait(F.Expressions.is_expression_representative):
        return None

    from faebryk.core.solver.symbolic.invariants import AliasClass

    for is_ in operand.get_operations(F.Expressions.Is, predicates_only=True):
        try:
            alias = AliasClass.of(is_)
        except AssertionError:
            continue

        if not alias.representative().is_same(operand, allow_different_graph=True):
            continue

        exprs = alias.get_with_trait(F.Expressions.is_expression)
        if len(exprs) == 1:
            return next(iter(exprs))

    return None


def _expr_depends_on_target_alias(
    target_op: F.Parameters.can_be_operand,
    expr: F.Expressions.is_expression,
) -> bool:
    from faebryk.core.solver.symbolic.invariants import AliasClass

    target_alias_params = AliasClass.of(target_op, allow_non_repr=True).get_with_trait(
        F.Parameters.is_parameter
    )
    if not target_alias_params:
        return False

    def operand_depends_on_target(
        operand: F.Parameters.can_be_operand,
        seen: set[int],
    ) -> bool:
        if any(
            operand.is_same(alias_param.as_operand.get())
            for alias_param in target_alias_params
        ):
            return True

        operand_id = id(operand.instance)
        if operand_id in seen:
            return False
        seen.add(operand_id)

        if nested_expr := _try_get_expression_representative(operand):
            return any(
                operand_depends_on_target(nested, seen)
                for nested in nested_expr.get_operands()
            )

        return False

    return any(
        operand_depends_on_target(operand, set()) for operand in expr.get_operands()
    )


def _singleton_numbers(
    mutator: Mutator,
    value: float,
    unit: fabll.Node | None,
) -> F.Literals.Numbers:
    return (
        F.Literals.Numbers.bind_typegraph(tg=mutator.tg_in)
        .create_instance(g=mutator.G_transient)
        .setup_from_singleton(value=value, unit=unit)
    )


def _min_singleton(mutator: Mutator, numbers: F.Literals.Numbers) -> F.Literals.Numbers:
    return _singleton_numbers(mutator, numbers.get_min_value(), numbers.get_is_unit())


def _max_singleton(mutator: Mutator, numbers: F.Literals.Numbers) -> F.Literals.Numbers:
    return _singleton_numbers(mutator, numbers.get_max_value(), numbers.get_is_unit())


def _summary_without_uncertainty(
    mutator: Mutator, outer: F.Literals.Numbers
) -> _UncertaintySummary:
    return _UncertaintySummary(
        outer=outer,
        robust_low=_min_singleton(mutator, outer),
        robust_high=_max_singleton(mutator, outer),
        uncertainty_leaf_count=0,
    )


def _summary_for_uncertainty_leaf(
    mutator: Mutator, outer: F.Literals.Numbers
) -> _UncertaintySummary:
    return _UncertaintySummary(
        outer=outer,
        robust_low=_max_singleton(mutator, outer),
        robust_high=_min_singleton(mutator, outer),
        uncertainty_leaf_count=1,
    )


def _try_extract_numeric_superset(
    mutator: Mutator,
    po: F.Parameters.is_parameter_operatable,
) -> F.Literals.Numbers | None:
    if lit := po.try_extract_superset():
        if lit := fabll.Traits(lit).get_obj_raw().try_cast(F.Literals.Numbers):
            return lit
    if not (numeric_param := _try_get_numeric_parameter(po)):
        return None
    return numeric_param.domain_set(g=mutator.G_transient, tg=mutator.tg_in)


def _try_extract_numeric_subset(
    po: F.Parameters.is_parameter_operatable,
) -> F.Literals.Numbers | None:
    if lit := po.try_extract_subset():
        return fabll.Traits(lit).get_obj_raw().try_cast(F.Literals.Numbers)
    return None


def _strictly_positive(numbers: F.Literals.Numbers) -> bool:
    return numbers.get_min_value() > 0


def _is_finite(numbers: F.Literals.Numbers) -> bool:
    return math.isfinite(numbers.get_min_value()) and math.isfinite(
        numbers.get_max_value()
    )


def _build_interval_from_bounds(
    mutator: Mutator,
    low: F.Literals.Numbers,
    high: F.Literals.Numbers,
    *,
    unit: fabll.Node | None = None,
) -> F.Literals.Numbers:
    return (
        F.Literals.Numbers.bind_typegraph(tg=mutator.tg_in)
        .create_instance(g=mutator.G_transient)
        .setup_from_min_max(
            min=low.get_min_value(),
            max=high.get_max_value(),
            unit=unit or low.get_is_unit(),
        )
    )


def _summarize_add(
    mutator: Mutator, summaries: list[_UncertaintySummary]
) -> _UncertaintySummary | None:
    outer = summaries[0].outer.op_add_intervals(
        *(summary.outer for summary in summaries[1:]),
        g=mutator.G_transient,
        tg=mutator.tg_in,
    )
    uncertainty_leaf_count = sum(
        summary.uncertainty_leaf_count for summary in summaries
    )
    if uncertainty_leaf_count == 0:
        return _summary_without_uncertainty(mutator, outer)
    if uncertainty_leaf_count != 1 or not all(
        _is_finite(summary.outer) for summary in summaries
    ):
        return None

    dependent_index = next(
        i for i, summary in enumerate(summaries) if summary.uncertainty_leaf_count
    )
    robust_low = summaries[dependent_index].robust_low
    robust_high = summaries[dependent_index].robust_high
    for i, summary in enumerate(summaries):
        if i == dependent_index:
            continue
        robust_low = robust_low.op_add_intervals(
            _min_singleton(mutator, summary.outer),
            g=mutator.G_transient,
            tg=mutator.tg_in,
        )
        robust_high = robust_high.op_add_intervals(
            _max_singleton(mutator, summary.outer),
            g=mutator.G_transient,
            tg=mutator.tg_in,
        )

    return _UncertaintySummary(
        outer=outer,
        robust_low=robust_low,
        robust_high=robust_high,
        uncertainty_leaf_count=1,
    )


def _summarize_multiply(
    mutator: Mutator, summaries: list[_UncertaintySummary]
) -> _UncertaintySummary | None:
    outer = summaries[0].outer.op_mul_intervals(
        *(summary.outer for summary in summaries[1:]),
        g=mutator.G_transient,
        tg=mutator.tg_in,
    )
    uncertainty_leaf_count = sum(
        summary.uncertainty_leaf_count for summary in summaries
    )
    if uncertainty_leaf_count == 0:
        return _summary_without_uncertainty(mutator, outer)
    if uncertainty_leaf_count != 1 or not all(
        _strictly_positive(summary.outer) and _is_finite(summary.outer)
        for summary in summaries
    ):
        return None

    dependent_index = next(
        i for i, summary in enumerate(summaries) if summary.uncertainty_leaf_count
    )
    robust_low = summaries[dependent_index].robust_low
    robust_high = summaries[dependent_index].robust_high
    for i, summary in enumerate(summaries):
        if i == dependent_index:
            continue
        robust_low = robust_low.op_mul_intervals(
            _min_singleton(mutator, summary.outer),
            g=mutator.G_transient,
            tg=mutator.tg_in,
        )
        robust_high = robust_high.op_mul_intervals(
            _max_singleton(mutator, summary.outer),
            g=mutator.G_transient,
            tg=mutator.tg_in,
        )

    return _UncertaintySummary(
        outer=outer,
        robust_low=robust_low,
        robust_high=robust_high,
        uncertainty_leaf_count=1,
    )


def _summarize_power_inverse(
    mutator: Mutator, base_summary: _UncertaintySummary
) -> _UncertaintySummary | None:
    if not _strictly_positive(base_summary.outer) or not _is_finite(base_summary.outer):
        return None
    outer = base_summary.outer.op_invert(g=mutator.G_transient, tg=mutator.tg_in)
    if base_summary.uncertainty_leaf_count == 0:
        return _summary_without_uncertainty(mutator, outer)
    if base_summary.uncertainty_leaf_count != 1:
        return None

    return _UncertaintySummary(
        outer=outer,
        robust_low=base_summary.robust_high.op_invert(
            g=mutator.G_transient, tg=mutator.tg_in
        ),
        robust_high=base_summary.robust_low.op_invert(
            g=mutator.G_transient, tg=mutator.tg_in
        ),
        uncertainty_leaf_count=1,
    )


def _summarize_uncertainty_operand(
    mutator: Mutator,
    operand: F.Parameters.can_be_operand,
) -> _UncertaintySummary | None:
    if literal := _try_get_numbers_literal(operand):
        return _summary_without_uncertainty(mutator, literal)

    if expr := _try_get_expression_representative(operand):
        return _summarize_uncertainty_expression(mutator, expr)

    if not (po := operand.as_parameter_operatable.try_get()):
        return None

    if subset := _try_extract_numeric_subset(po):
        return _summary_for_uncertainty_leaf(mutator, subset)

    if outer := _try_extract_numeric_superset(mutator, po):
        return _summary_without_uncertainty(mutator, outer)

    return None


def _summarize_uncertainty_expression(
    mutator: Mutator,
    expr: F.Expressions.is_expression,
) -> _UncertaintySummary | None:
    operands = expr.get_operands()

    if expr.expr_isinstance(Add):
        summaries = [_summarize_uncertainty_operand(mutator, op) for op in operands]
        if any(summary is None for summary in summaries):
            return None
        return _summarize_add(mutator, [summary for summary in summaries if summary])

    if expr.expr_isinstance(Multiply):
        summaries = [_summarize_uncertainty_operand(mutator, op) for op in operands]
        if any(summary is None for summary in summaries):
            return None
        return _summarize_multiply(
            mutator, [summary for summary in summaries if summary]
        )

    if expr.expr_isinstance(Power) and len(operands) == 2:
        exponent = _try_get_numbers_literal(operands[1])
        if (
            exponent is None
            or not exponent.is_singleton()
            or exponent.get_single() != -1
        ):
            return None
        base_summary = _summarize_uncertainty_operand(mutator, operands[0])
        if base_summary is None:
            return None
        return _summarize_power_inverse(mutator, base_summary)

    return None


@algorithm("Uncertainty estimation", terminal=False)
def uncertainty_estimation_single_source(mutator: Mutator):
    """
    Derive a safe outer bound for a parameter from a canonical expression tree with a
    single uncertainty leaf.

    This pass is intentionally conservative: it only helps targets that are still
    open-ended. Once a target already has a finite outer bound, we leave further
    tightening to the ordinary upper-estimation machinery.
    """

    for eq in mutator.get_typed_expressions(
        F.Expressions.Is,
        required_traits=(F.Expressions.is_predicate,),
        include_terminated=True,
    ):
        eq_e = eq.get_trait(F.Expressions.is_expression)
        operands = eq_e.get_operands()

        param_operands = [
            op
            for op in operands
            if (po := op.as_parameter_operatable.try_get())
            and _try_get_numeric_parameter(po)
            and not op.try_get_sibling_trait(F.Expressions.is_expression_representative)
        ]
        expr_operands = [
            op for op in operands if _try_get_expression_representative(op) is not None
        ]
        if len(param_operands) != 1 or not expr_operands:
            continue

        target_op = param_operands[0]
        target_po = target_op.as_parameter_operatable.force_get()
        existing_upper = _try_extract_numeric_superset(mutator, target_po)
        if existing_upper is not None and _is_finite(existing_upper):
            continue

        candidate: F.Literals.Numbers | None = None

        for expr_op in expr_operands:
            rhs_expr = _try_get_expression_representative(expr_op)
            if rhs_expr is None:
                continue

            if _expr_depends_on_target_alias(target_op, rhs_expr):
                continue

            summary = _summarize_uncertainty_expression(mutator, rhs_expr)
            if summary is None or summary.uncertainty_leaf_count != 1:
                continue

            if summary.robust_low.get_min_value() > summary.robust_high.get_max_value():
                # This rewritten equality does not admit a non-empty common interval
                # under uncertainty semantics. That is a conservative skip, not a proof
                # of unsatisfiability of the whole alias class.
                continue

            expr_candidate = _build_interval_from_bounds(
                mutator,
                summary.robust_low,
                summary.robust_high,
            )
            candidate = (
                expr_candidate
                if candidate is None
                else fabll.Traits(
                    candidate.is_literal.get().op_setic_intersect(
                        expr_candidate.is_literal.get(),
                        g=mutator.G_transient,
                        tg=mutator.tg_in,
                    )
                ).get_obj(F.Literals.Numbers)
            )

        if candidate is None:
            continue

        if existing_upper is not None:
            candidate = fabll.Traits(
                candidate.is_literal.get().op_setic_intersect(
                    existing_upper.is_literal.get(),
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
