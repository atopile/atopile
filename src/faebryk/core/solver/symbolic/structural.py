# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import math
from typing import NamedTuple

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.symbolic.invariants import AliasClass
from faebryk.core.solver.symbolic.pure_literal import (
    exec_pure_literal_operands,
)
from faebryk.core.solver.utils import (
    Contradiction,
    MutatorUtils,
)

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
    return exec_pure_literal_operands(
        mutator.G_transient,
        mutator.tg_in,
        mutator.utils.hack_get_expr_type(expr_e),
        mapped_operands,
    )


def _intersect_literals(
    mutator: Mutator,
    left: F.Literals.is_literal,
    right: F.Literals.is_literal,
) -> F.Literals.is_literal:
    return left.op_setic_intersect(
        right,
        g=mutator.G_transient,
        tg=mutator.tg_in,
    )


def _evaluate_outer(
    mutator: Mutator,
    node: F.Parameters.can_be_operand,
) -> F.Literals.is_literal | None:
    if lit := node.as_literal.try_get():
        return lit

    if expr := node.try_get_sibling_trait(F.Expressions.is_expression):
        if expr.try_get_sibling_trait(F.Expressions.is_setic) is not None:
            return None

        mapped_operands: list[F.Parameters.can_be_operand] = []
        for operand in expr.get_operands():
            if not (lit := _evaluate_outer(mutator, operand)):
                return None
            mapped_operands.append(lit.as_operand.get())

        return _fold_pure_literal_exprs(mutator, expr, mapped_operands)

    if not (po := node.as_parameter_operatable.try_get()):
        return None

    return mutator.utils.try_extract_superset(po, domain_default=True)


@algorithm("Upper estimation", terminal=False)
def upper_estimation_of_expressions_with_supersets(mutator: Mutator):
    """
    Fold predicate expressions and aliased target params from current outer bounds.
    """
    for expr in mutator.get_expressions(
        required_traits=(F.Expressions.is_expression,),
        include_terminated=True,
    ):
        if expr.expr_isinstance(F.Expressions.Is):
            continue
        if expr.expr_isinstance(F.Expressions.IsSubset):
            continue
        if expr.expr_isinstance(F.Expressions.IsSuperset):
            continue
        if expr.try_get_sibling_trait(F.Expressions.is_setic) is not None:
            continue
        if expr.try_get_sibling_trait(F.Expressions.is_predicate) is None:
            continue
        if not (out := _evaluate_outer(mutator, expr.as_operand.get())):
            continue
        if out.op_setic_equals_singleton(True):
            continue
        expr_po = expr.as_parameter_operatable.get()
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            expr.as_operand.get(),
            out.as_operand.get(),
            from_ops=[expr_po],
            assert_=True,
        )

    for target_po in mutator.get_parameter_operatables():
        if target_po.try_get_sibling_trait(F.Expressions.is_predicate) is not None:
            continue
        target = target_po.as_operand.get()
        alias = AliasClass.of(target)
        alias_params = alias.get_with_trait(F.Parameters.is_parameter)
        if len(alias_params) != 1:
            continue
        if not next(iter(alias_params)).as_operand.get().is_same(target):
            continue

        if not (candidate := mutator.utils.try_extract_superset(target_po, domain_default=True)):
            continue

        changed = False
        for rhs in alias.get_with_trait(F.Expressions.is_expression):
            if rhs.try_get_sibling_trait(F.Expressions.is_predicate) is not None:
                continue
            if rhs.try_get_sibling_trait(F.Expressions.is_setic) is not None:
                continue
            if target_po in rhs.get_operand_leaves_operatable():
                continue
            if not (out := _evaluate_outer(mutator, rhs.as_operand.get())):
                continue
            changed = True
            candidate = _intersect_literals(mutator, candidate, out)

        if not changed:
            continue
        if candidate.op_setic_equals_singleton(True):
            continue
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            target,
            candidate.as_operand.get(),
            from_ops=[target_po],
            assert_=True,
        )

class _UncertaintySummary(NamedTuple):
    outer: F.Literals.Numbers
    robust_min: float
    robust_max: float
    source_count: int


def _make_summary(
    outer: F.Literals.Numbers, source_count: int = 0
) -> _UncertaintySummary:
    if outer.is_empty():
        return _UncertaintySummary(outer, math.inf, -math.inf, source_count)
    robust_min = outer.get_min_value()
    robust_max = outer.get_max_value()
    if source_count:
        robust_min, robust_max = robust_max, robust_min
    return _UncertaintySummary(outer, robust_min, robust_max, source_count)


def _intersect_summaries(
    mutator: Mutator, left: _UncertaintySummary, right: _UncertaintySummary
) -> _UncertaintySummary:
    outer = fabll.Traits(
        left.outer.is_literal.get().op_setic_intersect(
            right.outer.is_literal.get(),
            g=mutator.G_transient,
            tg=mutator.tg_in,
        )
    ).get_obj(F.Literals.Numbers)
    return _UncertaintySummary(
        outer,
        max(left.robust_min, right.robust_min),
        min(left.robust_max, right.robust_max),
        max(left.source_count, right.source_count),
    )


def _fold_numeric_expression(
    mutator: Mutator,
    expr_t: type[Add] | type[Multiply],
    outers: list[F.Literals.Numbers],
) -> F.Literals.Numbers:
    out = exec_pure_literal_operands(
        mutator.G_transient,
        mutator.tg_in,
        expr_t,
        [outer.is_literal.get().as_operand.get() for outer in outers],
    )
    assert out is not None
    return fabll.Traits(out).get_obj(F.Literals.Numbers)


def _summarize_uncertainty(
    mutator: Mutator,
    node: F.Parameters.can_be_operand,
    allow_alias: bool = True,
):
    if literal := MutatorUtils.is_numeric_literal(node):
        return _make_summary(literal)
    if expr := node.try_get_sibling_trait(F.Expressions.is_expression):
        operands = expr.get_operands()
        parts: list[_UncertaintySummary] = []
        for operand in operands:
            if not (
                part := _summarize_uncertainty(
                    mutator,
                    operand,
                    allow_alias=allow_alias,
                )
            ):
                return None
            parts.append(part)

        if expr.expr_isinstance(Power):
            exponent = (
                MutatorUtils.is_numeric_literal(operands[1])
                if len(operands) == 2
                else None
            )
            base = (
                parts[0]
                if exponent and exponent.is_singleton() and exponent.get_single() == -1
                else None
            )
            if (
                base is None
                or base.outer.is_empty()
                or not base.outer.is_finite()
                or base.outer.get_min_value() <= 0
            ):
                return None
            return _make_summary(
                base.outer.op_invert(g=mutator.G_transient, tg=mutator.tg_in),
                source_count=base.source_count,
            )

        expr_t = (
            Add
            if expr.expr_isinstance(Add)
            else Multiply
            if expr.expr_isinstance(Multiply)
            else None
        )
        if expr_t is None:
            return None

        if any(part.outer.is_empty() or not part.outer.is_finite() for part in parts):
            return None
        source_count = sum(part.source_count for part in parts)
        if source_count > 1:
            return None

        outer = _fold_numeric_expression(
            mutator,
            expr_t,
            [part.outer for part in parts],
        )
        if source_count == 0:
            return _make_summary(outer)

        moving = next(part for part in parts if part.source_count)
        fixed = [part.outer for part in parts if not part.source_count]
        assert fixed, "Unary Add/Multiply should be eliminated before uncertainty pass"
        fixed_outer = _fold_numeric_expression(mutator, expr_t, fixed)
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
        return None

    if po := node.as_parameter_operatable.try_get():
        if subset := MutatorUtils.is_numeric_literal(mutator.utils.try_extract_subset(po)):
            return _make_summary(subset, source_count=1)

        outer = MutatorUtils.is_numeric_literal(
            mutator.utils.try_extract_superset(po, domain_default=True)
        )
        candidate = None if outer is None else _make_summary(outer)
        if not allow_alias or (outer is not None and outer.is_finite()):
            return candidate

        for expr in AliasClass.of(po.as_operand.get()).get_with_trait(
            F.Expressions.is_expression
        ):
            if po in expr.get_operand_leaves_operatable():
                continue
            if not (
                summary := _summarize_uncertainty(
                    mutator,
                    expr.as_operand.get(),
                    allow_alias=False,
                )
            ):
                continue
            candidate = (
                summary
                if candidate is None
                else _intersect_summaries(mutator, candidate, summary)
            )
        return candidate

    return None


@algorithm("Uncertainty estimation", terminal=False)
def uncertainty_estimation_single_source(mutator: Mutator):
    """Robustly narrow params from a single lower-bound uncertainty source."""

    for target_po in mutator.get_parameter_operatables():
        if not (param := target_po.as_parameter.try_get()):
            continue
        if fabll.Traits(param).get_obj_raw().try_cast(F.Parameters.NumericParameter) is None:
            continue

        target = target_po.as_operand.get()
        alias = AliasClass.of(target)
        alias_params = alias.get_with_trait(F.Parameters.is_parameter)
        if len(alias_params) != 1:
            continue
        if not next(iter(alias_params)).as_operand.get().is_same(target):
            continue

        if mutator.utils.try_extract_subset(target_po) is not None:
            continue

        outer = MutatorUtils.is_numeric_literal(
            mutator.utils.try_extract_superset(target_po, domain_default=True)
        )
        if outer is None:
            continue

        candidate = None
        for expr in alias.get_with_trait(F.Expressions.is_expression):
            if expr.try_get_sibling_trait(F.Expressions.is_predicate):
                continue
            if expr.try_get_sibling_trait(F.Expressions.is_setic):
                continue
            if target_po in expr.get_operand_leaves_operatable():
                continue

            summary = _summarize_uncertainty(mutator, expr.as_operand.get())
            if summary is None or summary.source_count != 1:
                continue
            candidate = (
                summary
                if candidate is None
                else _intersect_summaries(mutator, candidate, summary)
            )

        if candidate is None:
            continue

        candidate = _intersect_summaries(mutator, candidate, _make_summary(outer))
        if candidate.outer.is_empty():
            raise Contradiction(
                "Uncertainty lower bound not contained in target upper bound",
                involved=[target_po],
                mutator=mutator,
            )
        if candidate.robust_min > candidate.robust_max:
            continue
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            target_po.as_operand.get(),
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
