# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from typing import Callable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.facts import IsUniversalEnclosure
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.symbolic.invariants import AliasClass
from faebryk.core.solver.symbolic.pure_literal import (
    exec_pure_literal_operands,
)
from faebryk.core.solver.utils import (
    Contradiction,
    MutatorUtils,
)
from faebryk.libs.util import OrderedSet, groupby, not_none

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
@algorithm("Upper estimation", terminal=False)
def upper_estimation_of_expressions_with_supersets(mutator: Mutator):
    """
    Forward `ss!` estimation over representative parameters.

    ```
    A is! f(B, C, ...)
    B ss! X, C ss! Y, ...
    -> A ss! f(X, Y, ...)
    ```
    """

    for target_po in mutator.get_parameter_operatables():
        target = target_po.as_operand.get()
        rhs_candidates = list(
            OrderedSet(
                list(
                    AliasClass.of(target).expressions(
                        excluded_traits=(F.Expressions.is_setic,),
                        exclude_operand=target_po,
                    )
                )
                + (
                    [expr]
                    if (
                        (expr := target_po.as_expression.try_get())
                        and expr.try_get_sibling_trait(F.Expressions.is_predicate)
                        is not None
                        and expr.try_get_sibling_trait(F.Expressions.is_setic) is None
                    )
                    else []
                )
            )
        )

        rhs_by_predicate = groupby(
            rhs_candidates,
            key=lambda rhs: (
                rhs.try_get_sibling_trait(F.Expressions.is_predicate) is not None
            ),
        )
        target_is_predicate = True in rhs_by_predicate

        for rhs in rhs_by_predicate.get(target_is_predicate, []):
            operands, _ = mutator.utils.map_operands_extracted_supersets(
                rhs, domain_default=True
            )

            # Missing an operand `ss!` means this alias cannot be folded yet.
            # Leave the expression in place and let later solver iterations try
            # again after other passes tighten its operands.
            if any(operand.as_literal.try_get() is None for operand in operands):
                continue

            out = exec_pure_literal_operands(
                mutator.G_transient,
                mutator.tg_in,
                mutator.utils.hack_get_expr_type(rhs),
                operands,
            )

            if not out:
                continue

            # `P! ss! True` is tautological and only creates churn. Keep `False`,
            # because the invariant pipeline will turn asserted `P! ss! False`
            # into a contradiction.
            if target_is_predicate and out.op_setic_equals_singleton(True):
                continue

            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                target,
                out.as_operand.get(),
                from_ops=[target_po],
                assert_=True,
            )


_Interval = tuple[float, float]
_UncertaintyResult = tuple[F.Literals.Numbers, _Interval, bool]


def _as_enclosure(lit: F.Literals.Numbers) -> _Interval:
    return lit.get_min_value(), lit.get_max_value()


class _QuantifiedEnclosureEval:
    @staticmethod
    def eval_reciprocal(
        mutator: Mutator, operand_results: list[_UncertaintyResult]
    ) -> _UncertaintyResult | None:
        base, _ = operand_results
        (
            base_existential_enclosure,
            base_universal_enclosure,
            base_depends_on_uncertainty,
        ) = base

        base_enclosure_min, base_enclosure_max = base_universal_enclosure

        if (
            base_existential_enclosure.get_min_value() <= 0
            or not base_existential_enclosure.is_finite()
        ):
            return None

        existential_enclosure = base_existential_enclosure.op_invert(
            g=mutator.G_transient, tg=mutator.tg_in
        )

        universal_enclosure = (
            (1 / base_enclosure_max, 1 / base_enclosure_min)
            if base_depends_on_uncertainty
            else _as_enclosure(existential_enclosure)
        )

        return existential_enclosure, universal_enclosure, base_depends_on_uncertainty

    @staticmethod
    def eval_nary(
        mutator: Mutator,
        expr_t: type[Add] | type[Multiply],
        operand_results: list[_UncertaintyResult],
        combine_enclosures: Callable[[_Interval, F.Literals.Numbers], _Interval],
    ) -> _UncertaintyResult | None:
        def fold_results(
            operand_results: list[_UncertaintyResult],
            depends_on_uncertainty: bool | None = None,
        ) -> F.Literals.Numbers | None:
            return MutatorUtils.is_numeric_literal(
                exec_pure_literal_operands(
                    mutator.G_transient,
                    mutator.tg_in,
                    expr_t,
                    [
                        existential_enclosure.is_literal.get().as_operand.get()
                        for (
                            existential_enclosure,
                            _,
                            operand_depends_on_uncertainty,
                        ) in operand_results
                        if depends_on_uncertainty is None
                        or operand_depends_on_uncertainty == depends_on_uncertainty
                    ],
                )
            )

        if not all(
            existential_enclosure.is_finite()
            for existential_enclosure, _, _ in operand_results
        ):
            return None

        uncertain_results = [
            universal_enclosure
            for _, universal_enclosure, depends_on_uncertainty in operand_results
            if depends_on_uncertainty
        ]
        if len(uncertain_results) > 1:
            return None

        if (existential_enclosure_out := fold_results(operand_results)) is None:
            return None

        if not uncertain_results:
            return (
                existential_enclosure_out,
                _as_enclosure(existential_enclosure_out),
                False,
            )

        [universal_enclosure] = uncertain_results
        fixed_existential_enclosure = fold_results(
            operand_results, depends_on_uncertainty=False
        )

        universal_enclosure_out = combine_enclosures(
            universal_enclosure, not_none(fixed_existential_enclosure)
        )

        return (existential_enclosure_out, universal_enclosure_out, True)

    @staticmethod
    def eval_add(
        mutator: Mutator, operand_results: list[_UncertaintyResult]
    ) -> _UncertaintyResult | None:
        def combine_enclosures(
            universal_enclosure: _Interval,
            fixed_existential_enclosure: F.Literals.Numbers,
        ) -> _Interval:
            universal_min, universal_max = universal_enclosure
            return (
                universal_min + fixed_existential_enclosure.get_min_value(),
                universal_max + fixed_existential_enclosure.get_max_value(),
            )

        return _QuantifiedEnclosureEval.eval_nary(
            mutator, Add, operand_results, combine_enclosures
        )

    @staticmethod
    def eval_multiply(
        mutator: Mutator, operand_results: list[_UncertaintyResult]
    ) -> _UncertaintyResult | None:
        def combine_enclosures(
            universal_enclosure: _Interval,
            fixed_existential_enclosure: F.Literals.Numbers,
        ) -> _Interval:
            universal_min, universal_max = universal_enclosure
            fixed_min = fixed_existential_enclosure.get_min_value()
            fixed_max = fixed_existential_enclosure.get_max_value()

            if fixed_min > 0:
                # preserve order
                return (universal_min * fixed_min, universal_max * fixed_max)
            elif fixed_max < 0:
                # reverse order
                return (universal_max * fixed_min, universal_min * fixed_max)
            else:
                # min/max over extreme products
                return (
                    min(universal_max * fixed_min, universal_min * fixed_max),
                    max(universal_min * fixed_min, universal_max * fixed_max),
                )

        return _QuantifiedEnclosureEval.eval_nary(
            mutator, Multiply, operand_results, combine_enclosures
        )


def _eval_uncertainty_expression(
    mutator: Mutator,
    expr: F.Expressions.is_expression,
    source_po: F.Parameters.is_parameter_operatable,
) -> _UncertaintyResult | None:
    """
    Evaluate one direct alias expression relative to one lower-subset source.

    A is! f(B, C, ...)
    -> eval f(B, C, ...) from the current persisted state of B, C, ...

    The expression graph is flat at this stage, so further propagation happens by
    persisting `ss!` / `ss!∀` facts and letting the outer solver loop revisit the
    next layer on a later iteration.
    """

    class _UnsupportedOperand(Exception):
        pass

    def eval_operand(operand: F.Parameters.can_be_operand) -> _UncertaintyResult:
        if lit := MutatorUtils.is_numeric_literal(operand):
            # Literals are exact and do not introduce uncertainty by themselves
            return lit, _as_enclosure(lit), False

        if nested_expr := operand.try_get_sibling_trait(F.Expressions.is_expression):
            if result := _eval_uncertainty_expression(mutator, nested_expr, source_po):
                return result
            raise _UnsupportedOperand

        po = operand.as_parameter_operatable.force_get()
        if lower_bound := mutator.utils.try_extract_numeric_subset(po):
            if not po.is_same(source_po):
                raise _UnsupportedOperand

            return (
                lower_bound,
                # Carry as (max, min) until a surrounding monotone operator converts to
                # a real interval
                (lower_bound.get_max_value(), lower_bound.get_min_value()),
                True,
            )

        if (
            existential_enclosure := mutator.utils.try_extract_numeric_superset(po)
        ) is None:
            raise _UnsupportedOperand

        if universal_enclosure := (
            mutator.utils.try_extract_numeric_universal_enclosure_for_source(
                po, source_po
            )
        ):
            return existential_enclosure, universal_enclosure, True

        return existential_enclosure, _as_enclosure(existential_enclosure), False

    try:
        operand_results = [eval_operand(operand) for operand in expr.get_operands()]
    except _UnsupportedOperand:
        return None

    if expr.expr_isinstance(Power) and expr.expr_cast(Power).is_reciprocal():
        return _QuantifiedEnclosureEval.eval_reciprocal(mutator, operand_results)
    elif expr.expr_isinstance(Add):
        return _QuantifiedEnclosureEval.eval_add(mutator, operand_results)
    elif expr.expr_isinstance(Multiply):
        return _QuantifiedEnclosureEval.eval_multiply(mutator, operand_results)


@algorithm("Uncertainty estimation", terminal=False)
def uncertainty_estimation_single_source(mutator: Mutator):
    """
    Contract parameter upper bounds from a single uncertainty source.

    A is! f(B, C, ...)
    L ss! B
    f depends on exactly one such lower-bounded operand
    -> A ss! Y

    where Y is the universal enclosure for all values of B in L, restricted to
    certain monotone expression cases
    """
    numeric_pos = OrderedSet(
        mutator.get_parameter_operatables_of_type(F.Parameters.NumericParameter)
    )
    sources = OrderedSet(
        po for po in numeric_pos if po.try_extract_subset() is not None
    )
    targets = numeric_pos.difference(sources)

    for source_po in sources:
        source_op = source_po.as_operand.get()
        for target_po in targets:
            target_op = target_po.as_operand.get()
            for expr in AliasClass.of(target_op).expressions(
                excluded_traits=(
                    F.Expressions.is_predicate,
                    F.Expressions.is_setic,
                ),
                exclude_operand=target_po,
            ):
                if not (
                    result := _eval_uncertainty_expression(mutator, expr, source_po)
                ):
                    continue

                _, universal_enclosure, depends_on_uncertainty = result

                if not depends_on_uncertainty:
                    continue

                existential_enclosure, _, _ = result
                universal_min, universal_max = universal_enclosure
                existential_enclosure_op = (
                    existential_enclosure.is_literal.get().as_operand.get()
                )

                mutator.create_check_and_insert_expression(
                    F.Expressions.IsSubset,
                    target_op,
                    existential_enclosure_op,
                    from_ops=[target_po, source_po],
                    assert_=True,
                )

                universal_min_lit = mutator.utils.make_number_literal_from_range(
                    universal_min, universal_min
                )
                universal_max_lit = mutator.utils.make_number_literal_from_range(
                    universal_max, universal_max
                )

                mutator.create_check_and_insert_expression(
                    IsUniversalEnclosure,
                    target_op,
                    source_op,
                    universal_min_lit.is_literal.get().as_operand.get(),
                    universal_max_lit.is_literal.get().as_operand.get(),
                    from_ops=[target_po, source_po],
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
