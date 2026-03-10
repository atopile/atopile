# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable, cast

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
from faebryk.libs.util import OrderedSet

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
        rhs_candidates = OrderedSet(
            AliasClass.of(target).expressions(
                excluded_traits=(F.Expressions.is_setic,),
                exclude_operand=target_po,
            )
        )
        if (expr := target_po.as_expression.try_get()) and expr.try_get_sibling_trait(
            F.Expressions.is_predicate
        ) is not None:
            rhs_candidates.add(expr)

        target_is_predicate = any(
            rhs.try_get_sibling_trait(F.Expressions.is_predicate) is not None
            for rhs in rhs_candidates
        )

        for rhs in rhs_candidates:
            if rhs.try_get_sibling_trait(F.Expressions.is_setic) is not None:
                continue
            if target_is_predicate != (
                rhs.try_get_sibling_trait(F.Expressions.is_predicate) is not None
            ):
                continue
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


_Bounds = tuple[float, float]


class _GuaranteedIntervalEvaluation:
    @staticmethod
    def eval_with_uncertainty(
        mutator: Mutator, expr: F.Expressions.is_expression, allow_alias: bool
    ) -> tuple[F.Literals.Numbers, _Bounds, bool] | None:
        parts = [
            _summarize_with_uncertainty(mutator, operand, allow_alias=allow_alias)
            for operand in expr.get_operands()
        ]

        if any(part is None for part in parts):
            return None

        parts = cast(list[tuple[F.Literals.Numbers, _Bounds, bool]], parts)

        if expr.expr_isinstance(Power) and expr.expr_cast(Power).is_reciprocal():
            return _GuaranteedIntervalEvaluation.eval_reciprocal_with_uncertainty(
                mutator, parts
            )
        elif expr.expr_isinstance(Add):
            return _GuaranteedIntervalEvaluation.eval_add_with_uncertainty(
                mutator, parts
            )
        elif expr.expr_isinstance(Multiply):
            return _GuaranteedIntervalEvaluation.eval_multiply_with_uncertainty(
                mutator, parts
            )

    @staticmethod
    def fold_nary_image_enclosures(
        mutator: Mutator,
        expr_t: type[Add] | type[Multiply],
        image_enclosures: list[F.Literals.Numbers],
    ) -> F.Literals.Numbers | None:
        operands = [
            image_enclosure.is_literal.get().as_operand.get()
            for image_enclosure in image_enclosures
        ]
        out = exec_pure_literal_operands(
            mutator.G_transient, mutator.tg_in, expr_t, operands
        )
        return MutatorUtils.is_numeric_literal(out)

    @staticmethod
    def partition_uncertainty_parts(
        parts: list[tuple[F.Literals.Numbers, _Bounds, bool]],
    ) -> (
        tuple[list[F.Literals.Numbers], list[F.Literals.Numbers], _Bounds | None] | None
    ):
        image_enclosures = []
        fixed_enclosures = []
        guaranteed_enclosure = None

        for (
            part_image_enclosure,
            part_guaranteed_enclosure,
            part_depends_on_uncertainty,
        ) in parts:
            if not part_image_enclosure.is_finite():
                return None
            image_enclosures.append(part_image_enclosure)
            if part_depends_on_uncertainty:
                if guaranteed_enclosure is not None:
                    return None
                guaranteed_enclosure = part_guaranteed_enclosure
            else:
                fixed_enclosures.append(part_image_enclosure)

        return image_enclosures, fixed_enclosures, guaranteed_enclosure

    @staticmethod
    def eval_reciprocal_with_uncertainty(
        mutator: Mutator,
        parts: list[tuple[F.Literals.Numbers, _Bounds, bool]],
    ) -> tuple[F.Literals.Numbers, _Bounds, bool] | None:
        base, _ = parts
        (
            base_image_enclosure,
            base_guaranteed_enclosure,
            base_depends_on_uncertainty,
        ) = base
        if (
            not base_image_enclosure.is_finite()
            or base_image_enclosure.get_min_value() <= 0
        ):
            return None

        image_enclosure = base_image_enclosure.op_invert(
            g=mutator.G_transient, tg=mutator.tg_in
        )
        guaranteed_enclosure = (
            (
                1 / base_guaranteed_enclosure[1],
                1 / base_guaranteed_enclosure[0],
            )
            if base_depends_on_uncertainty
            else (
                image_enclosure.get_min_value(),
                image_enclosure.get_max_value(),
            )
        )
        depends_on_uncertainty = base_depends_on_uncertainty
        return image_enclosure, guaranteed_enclosure, depends_on_uncertainty

    @staticmethod
    def eval_nary_with_uncertainty(
        mutator: Mutator,
        expr_t: type[Add] | type[Multiply],
        parts: list[tuple[F.Literals.Numbers, _Bounds, bool]],
        unary_assertion: str,
        combine_guaranteed_enclosure: Callable[
            [F.Literals.Numbers, _Bounds], _Bounds | None
        ],
    ) -> tuple[F.Literals.Numbers, _Bounds, bool] | None:
        partitioned = _GuaranteedIntervalEvaluation.partition_uncertainty_parts(parts)
        if partitioned is None:
            return None

        image_enclosures, fixed_enclosures, guaranteed_enclosure = partitioned
        image_enclosure = _GuaranteedIntervalEvaluation.fold_nary_image_enclosures(
            mutator, expr_t, image_enclosures
        )
        if image_enclosure is None:
            return None
        if guaranteed_enclosure is None:
            return (
                image_enclosure,
                (image_enclosure.get_min_value(), image_enclosure.get_max_value()),
                False,
            )

        fixed_image_enclosure = (
            _GuaranteedIntervalEvaluation.fold_nary_image_enclosures(
                mutator, expr_t, fixed_enclosures
            )
        )
        assert fixed_image_enclosure is not None, unary_assertion

        guaranteed_enclosure = combine_guaranteed_enclosure(
            fixed_image_enclosure, guaranteed_enclosure
        )
        if guaranteed_enclosure is None:
            return None
        return image_enclosure, guaranteed_enclosure, True

    @staticmethod
    def eval_add_with_uncertainty(
        mutator: Mutator,
        parts: list[tuple[F.Literals.Numbers, _Bounds, bool]],
    ) -> tuple[F.Literals.Numbers, _Bounds, bool] | None:
        return _GuaranteedIntervalEvaluation.eval_nary_with_uncertainty(
            mutator,
            Add,
            parts,
            "Unary Add should be eliminated before uncertainty pass",
            lambda fixed_image_enclosure, guaranteed_enclosure: (
                guaranteed_enclosure[0] + fixed_image_enclosure.get_min_value(),
                guaranteed_enclosure[1] + fixed_image_enclosure.get_max_value(),
            ),
        )

    @staticmethod
    def eval_multiply_with_uncertainty(
        mutator: Mutator, parts: list[tuple[F.Literals.Numbers, _Bounds, bool]]
    ) -> tuple[F.Literals.Numbers, tuple[float, float], bool] | None:
        def combine_guaranteed_enclosure(
            fixed_image_enclosure: F.Literals.Numbers,
            guaranteed_enclosure: _Bounds,
        ) -> _Bounds | None:
            if fixed_image_enclosure.get_min_value() <= 0:
                return None
            return (
                guaranteed_enclosure[0] * fixed_image_enclosure.get_min_value(),
                guaranteed_enclosure[1] * fixed_image_enclosure.get_max_value(),
            )

        return _GuaranteedIntervalEvaluation.eval_nary_with_uncertainty(
            mutator,
            Multiply,
            parts,
            "Unary Multiply should be eliminated before uncertainty pass",
            combine_guaranteed_enclosure,
        )


def _summarize_with_uncertainty(
    mutator: Mutator, op: F.Parameters.can_be_operand, allow_alias: bool = True
) -> tuple[F.Literals.Numbers, _Bounds, bool] | None:
    """
    Summarize one numeric operand under a single uncertainty source.

    X              -> exact summary                     if X is a literal
    L ss! A        -> uncertainty summary               if A has a lower subset
    A ss! U        -> ordinary summary                  if A has only an upper bound
    B is! f(A, C)  -> summary(B) from summary(A), summary(C)
    A is! f(...)   -> one alias-class hop, then summarize f(...)

    The result carries both the image enclosure and the guaranteed enclosure for all
    values of the single uncertainty source.
    """

    lit = MutatorUtils.is_numeric_literal(op)
    expr = op.try_get_sibling_trait(F.Expressions.is_expression)

    if lit is not None:
        # Literals are exact and do not introduce uncertainty by themselves.
        return lit, (lit.get_min_value(), lit.get_max_value()), False

    po = op.as_parameter_operatable.force_get()

    if (lower_bound := mutator.utils.try_extract_numeric_subset(po)) is not None:
        # A lower subset is the single uncertainty source this pass quantifies over.
        return (
            lower_bound,
            (lower_bound.get_max_value(), lower_bound.get_min_value()),
            True,
        )

    elif (
        not allow_alias
        and (upper_bound := mutator.utils.try_extract_numeric_superset(po)) is not None
    ):
        # Finite image enclosures are exact support bounds for the guaranteed
        # enclosure above.
        return (
            upper_bound,
            (upper_bound.get_min_value(), upper_bound.get_max_value()),
            False,
        )

    elif expr is not None:
        return _GuaranteedIntervalEvaluation.eval_with_uncertainty(
            mutator, expr, allow_alias
        )

    elif allow_alias:
        # TODO: can we avoid this?
        # One alias-class hop lets this pass see through a single flat
        # representative, while still leaving longer propagation to the
        # outer solver loop.
        for inner in AliasClass.of(op).expressions(
            excluded_traits=(F.Expressions.is_predicate, F.Expressions.is_setic),
            exclude_operand=po,
        ):
            if summary := _summarize_with_uncertainty(
                mutator, inner.as_operand.get(), allow_alias=False
            ):
                return summary

        if (
            image_enclosure := MutatorUtils.is_numeric_literal(
                mutator.utils.try_extract_superset(po, domain_default=True)
            )
        ) is None:
            return None

        return (
            image_enclosure,
            (
                image_enclosure.get_min_value(),
                image_enclosure.get_max_value(),
            ),
            False,
        )


@algorithm("Uncertainty estimation", terminal=False)
def uncertainty_estimation_single_source(mutator: Mutator):
    """
    Contract parameter upper bounds from a single uncertainty source.

    A is! f(B, C, ...)
    L ss! B
    f depends on exactly one such lower-bounded operand
    -> A ss! Y

    where Y is the guaranteed enclosure for all values of B in L, restricted to
    certain monotone expression cases
    """
    for target_po in mutator.get_parameter_operatables_of_type(
        F.Parameters.NumericParameter
    ):
        # Lower-bounded quantities are already uncertainty sources
        if target_po.try_extract_subset() is not None:
            continue

        target_op = target_po.as_operand.get()
        for expr in AliasClass.of(target_op).expressions(
            excluded_traits=(F.Expressions.is_predicate, F.Expressions.is_setic),
            exclude_operand=target_po,
        ):
            if (
                candidate := _summarize_with_uncertainty(mutator, expr.as_operand.get())
            ) is None:
                continue

            _, guaranteed_enclosure, depends_on_uncertainty = candidate

            # Only add bounds that depend on a lower subset
            if not depends_on_uncertainty:
                continue

            # No interval survives all values of the uncertainty source
            if guaranteed_enclosure[0] > guaranteed_enclosure[1]:
                continue

            lit = mutator.utils.make_number_literal_from_range(
                guaranteed_enclosure[0], guaranteed_enclosure[1]
            )

            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                target_op,
                lit.is_literal.get().as_operand.get(),
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
