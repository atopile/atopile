# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import NamedTuple, cast

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
from faebryk.libs.util import OrderedSet, not_none

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
        target_is_predicate = (
            target_po.try_get_sibling_trait(F.Expressions.is_predicate) is not None
        )

        for rhs in AliasClass.of(target).expressions(
            excluded_traits=(
                (F.Expressions.is_setic,)
                if target_is_predicate
                else (F.Expressions.is_predicate, F.Expressions.is_setic)
            ),
            exclude_operand=target_po,
        ):
            if (
                target_is_predicate
                and rhs.try_get_sibling_trait(F.Expressions.is_predicate) is None
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


class _UncertaintySummary(NamedTuple):
    """
    Robust `ss!` summary of one numeric expression.

    ```
    outer      := ordinary image of the expression
    robust_min := lower endpoint valid for all values of the single uncertainty source
    robust_max := upper endpoint valid for all values of the single uncertainty source
    uncertain  := the expression depends on that source
    ```

    If `uncertain` is false, `robust_min..robust_max` is just `outer`.
    """

    outer: F.Literals.Numbers
    robust_min: float
    robust_max: float
    uncertain: bool

    @classmethod
    def from_outer(
        cls, outer: F.Literals.Numbers, uncertain: bool = False
    ) -> "_UncertaintySummary":
        lo, hi = outer.get_min_value(), outer.get_max_value()
        return cls(outer, hi if uncertain else lo, lo if uncertain else hi, uncertain)

    @classmethod
    def _from_nary(
        cls,
        mutator: Mutator,
        expr_t: type[Add] | type[Multiply],
        parts: list["_UncertaintySummary"],
    ) -> (
        tuple[
            F.Literals.Numbers, "_UncertaintySummary | None", F.Literals.Numbers | None
        ]
        | None
    ):
        def _fold_outers(outers: list[F.Literals.Numbers]) -> F.Literals.Numbers | None:
            operands = [outer.is_literal.get().as_operand.get() for outer in outers]
            out = exec_pure_literal_operands(
                mutator.G_transient, mutator.tg_in, expr_t, operands
            )
            return MutatorUtils.is_numeric_literal(out)

        if (
            any(not part.outer.is_finite() for part in parts)
            or sum(part.uncertain for part in parts) > 1
        ):
            return None
        outer = _fold_outers([part.outer for part in parts])
        if outer is None:
            return None
        moving = next((part for part in parts if part.uncertain), None)
        if moving is None:
            return outer, None, None
        fixed_outer = _fold_outers([part.outer for part in parts if not part.uncertain])
        assert fixed_outer is not None, (
            f"Unary {expr_t.__name__} should be eliminated before uncertainty pass"
        )
        return outer, moving, fixed_outer

    @classmethod
    def from_reciprocal(
        cls,
        mutator: Mutator,
        expr: F.Expressions.is_expression,
        parts: list["_UncertaintySummary"],
    ) -> "_UncertaintySummary | None":
        """
        ```
        A is! B^-1
        B ss! [l, h], 0 < l <= h
        -> A ss! [1/h, 1/l]
        ```
        """
        exponent = (
            MutatorUtils.is_numeric_literal(expr.get_operands()[1])
            if len(parts) == 2
            else None
        )
        base = (
            parts[0]
            if exponent and exponent.is_singleton() and exponent.get_single() == -1
            else None
        )
        if (
            base is None
            or not base.outer.is_finite()
            or base.outer.get_min_value() <= 0
        ):
            return None
        return cls.from_outer(
            base.outer.op_invert(g=mutator.G_transient, tg=mutator.tg_in),
            uncertain=base.uncertain,
        )

    @classmethod
    def from_add(
        cls,
        mutator: Mutator,
        expr: F.Expressions.is_expression,
        parts: list["_UncertaintySummary"],
    ) -> "_UncertaintySummary | None":
        """
        ```
        A is! B + C + ...
        B ss! X, C ss! Y, ...
        at most one of B, C, ... uncertain
        -> A ss! X + Y + ...
        ```
        """
        prepared = cls._from_nary(mutator, Add, parts)
        if prepared is None:
            return None
        outer, moving, fixed_outer = prepared
        if moving is None:
            return cls.from_outer(outer)
        assert fixed_outer is not None
        return cls(
            outer=outer,
            robust_min=moving.robust_min + fixed_outer.get_min_value(),
            robust_max=moving.robust_max + fixed_outer.get_max_value(),
            uncertain=True,
        )

    @classmethod
    def from_multiply(
        cls,
        mutator: Mutator,
        expr: F.Expressions.is_expression,
        parts: list["_UncertaintySummary"],
    ) -> "_UncertaintySummary | None":
        """
        ```
        A is! B * C * ...
        B ss! X, C ss! Y, ...
        at most one of B, C, ... uncertain
        fixed factors in (0, +inf)
        -> A ss! X * Y * ...
        ```
        """
        prepared = cls._from_nary(mutator, Multiply, parts)
        if prepared is None:
            return None
        outer, moving, fixed_outer = prepared
        if moving is None:
            return cls.from_outer(outer)
        assert fixed_outer is not None
        if fixed_outer.get_min_value() <= 0:
            return None
        return cls(
            outer=outer,
            robust_min=moving.robust_min * fixed_outer.get_min_value(),
            robust_max=moving.robust_max * fixed_outer.get_max_value(),
            uncertain=True,
        )


def _summarize_operand_uncertainty(
    mutator: Mutator, operand: F.Parameters.can_be_operand, allow_alias: bool
) -> _UncertaintySummary | None:
    """
    Summarize one operand for single-source robust estimation.

    lit            -> exact summary
    L ss! A        -> uncertainty summary
    A ss! U        -> ordinary summary
    A is! f(...)   -> one alias-class hop, then summarize f(...)
    """
    # Literals are exact and do not introduce uncertainty by themselves.
    if literal := MutatorUtils.is_numeric_literal(operand):
        return _UncertaintySummary.from_outer(literal)

    if (po := operand.as_parameter_operatable.try_get()) is None:
        return None

    # A lower subset is the single uncertainty source this pass quantifies over.
    if subset := MutatorUtils.is_numeric_literal(mutator.utils.try_extract_subset(po)):
        return _UncertaintySummary.from_outer(subset, uncertain=True)

    outer = MutatorUtils.is_numeric_literal(
        mutator.utils.try_extract_superset(po, domain_default=True)
    )

    # Finite outers are exact support bounds for the robust combination above them.
    if outer and (outer.is_finite() or not allow_alias):
        return _UncertaintySummary.from_outer(outer)

    # One alias-class hop lets this pass see through a single flat representative,
    # while still leaving longer propagation to the outer solver loop.
    for inner in AliasClass.of(operand).expressions(
        excluded_traits=(F.Expressions.is_predicate, F.Expressions.is_setic),
        exclude_operand=po,
    ):
        if summary := _summarize_with_uncertainty(mutator, inner, allow_alias=False):
            return summary

    return _UncertaintySummary.from_outer(not_none(outer))


def _summarize_with_uncertainty(
    mutator: Mutator, expr: F.Expressions.is_expression, allow_alias: bool = True
) -> _UncertaintySummary | None:
    """
    Summarize a numeric expression under a single uncertainty source.

    X is lit       -> exact summary
    L ss! A        -> one uncertainty source
    A ss! U        -> ordinary summary
    B is! f(A, C)  -> summary(B) from summary(A), summary(C)

    The result carries both the ordinary image and the interval guaranteed for all
    values of the single uncertainty source.
    """

    if expr.expr_isinstance(Power):
        # TODO: check exponent
        func = _UncertaintySummary.from_reciprocal
    elif expr.expr_isinstance(Add):
        func = _UncertaintySummary.from_add
    elif expr.expr_isinstance(Multiply):
        func = _UncertaintySummary.from_multiply
    else:
        return None

    parts = [
        _summarize_operand_uncertainty(mutator, operand, allow_alias=allow_alias)
        for operand in expr.get_operands()
    ]
    if None in parts:
        return None
    parts = cast(list[_UncertaintySummary], parts)

    return func(mutator, expr, parts)


@algorithm("Uncertainty estimation", terminal=False)
def uncertainty_estimation_single_source(mutator: Mutator):
    """
    Robustly tighten representative parameters from a single uncertainty source.

    A is! f(B, C, ...)
    L ss! B
    f depends on exactly one such lower-bounded operand
    -> A ss! Y

    where Y is the interval guaranteed for all values of B in L, restricted to certain
    monotone expression cases
    """
    for target_po in mutator.get_parameter_operatables_of_type(
        F.Parameters.NumericParameter
    ):
        # Lower-bounded quantities are already uncertainty sources
        if target_po.try_extract_subset() is not None:
            continue

        target = target_po.as_operand.get()
        for other in AliasClass.of(target).expressions(
            excluded_traits=(F.Expressions.is_predicate, F.Expressions.is_setic),
            exclude_operand=target_po,
        ):
            candidate = _summarize_with_uncertainty(mutator, other)

            # Only add bounds that depend on a lower subset
            if not candidate or not candidate.uncertain:
                continue

            # No interval survives all values of the uncertainty source
            if candidate.robust_min > candidate.robust_max:
                continue

            lit_op = (
                mutator.utils.make_number_literal_from_range(
                    candidate.robust_min, candidate.robust_max
                )
                .is_literal.get()
                .as_operand.get()
            )

            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                target,
                lit_op,
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
