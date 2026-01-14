# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto
from functools import reduce
from typing import NamedTuple, Sequence, cast

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import SolverAlgorithm
from faebryk.core.solver.mutator import MutationMap, Mutator, is_terminated
from faebryk.core.solver.utils import (
    S_LOG,
    Contradiction,
    ContradictionByLiteral,
    pretty_expr,
)
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.util import indented_container, not_none

logger = logging.getLogger(__name__)
if S_LOG:
    logger.setLevel(logging.DEBUG)

IsSubset = F.Expressions.IsSubset


class SubsumptionCheck:
    """
    Semantic subsumption check — assumes structural match already passed.

    Predicate types with no subsumption cases:
    - Is: same values would be congruent (not subsuming), different don't subsume
    - IsBitSet: same bit+value would be congruent, different bits don't subsume

    Valid but expensive/complex cases intentionally skipped:
    - Not:
        - Not(A) subsumes Not(B) if B subsumes A (contraposition, recursive)
        - P subsumes Not(Q) when P implies ~Q (requires negation semantics)
        - Not(P) subsumes Q when ~P implies Q (requires negation semantics)
    - Nested logical expressions:
        - Not(Not(X)) ≡ X (handled by is_involutory normalization elsewhere)
        - De Morgan's laws for Not(Or(...))
    - Or:
        - Non-Or P subsumes Or(A, B, ...) if P subsumes any operand (recursive)
        - Or(A, B) subsumes non-Or P if all operands subsume P (recursive)
    """

    # TODO consider not returning subsuming expression:
    # - baically never useful
    # - very hard to find sometimes (ambiguity, performance/api)

    class Result(NamedTuple):
        """
        All default = NoOp
        """

        class _DISCARD:
            def __repr__(self) -> str:
                return "<DISCARD>"

        most_constrained_expr: "F.Expressions.is_expression | ExpressionBuilder | _DISCARD | None" = None  # noqa: E501
        subsumed: list[F.Expressions.is_expression] | None = None

    @staticmethod
    def subset(
        mutator: Mutator,
        builder: "ExpressionBuilder",
    ) -> Result:
        """
        A ss! X, A ss! Y -> A ss! X ∩ Y
        X ss! A, Y ss! A -> X ∪ Y ss! A
        """

        if not builder.assert_:
            # TODO properly implement
            return SubsumptionCheck.Result()

        ops = builder.indexed_pos()

        if len(ops) != 1:
            return SubsumptionCheck.Result()

        if subset_op := ops.get(0):
            superset_ss = [
                (ss, lit)
                for ss in mutator.get_operations(
                    subset_op, types=F.Expressions.IsSubset, predicates_only=True
                )
                if (
                    lit := ss.get_superset_operand().try_get_sibling_trait(
                        F.Literals.is_literal
                    )
                )
            ]
            if not superset_ss:
                return SubsumptionCheck.Result()

            assert len(superset_ss) == 1, (
                "multiple extant supersets violates invariant: "
                f"{[(ss.pretty_repr(), lit.pretty_repr()) for ss, lit in superset_ss]}",
            )
            superset_ss, superset_lit = superset_ss[0]
            new_superset = builder.operands[1].as_literal.force_get()
            merged_superset = superset_lit.op_setic_intersect(
                new_superset, g=mutator.G_transient, tg=mutator.tg_in
            )
            if superset_lit.op_setic_equals(merged_superset):
                return SubsumptionCheck.Result(superset_ss.is_expression.get())
            return SubsumptionCheck.Result(
                ExpressionBuilder(
                    IsSubset,
                    [subset_op.as_operand.get(), merged_superset.as_operand.get()],
                    assert_=True,
                    terminate=False,
                ),
                subsumed=[superset_ss.is_expression.get()],
            )

        elif superset_op := ops.get(1):
            subset_ss = [
                (ss, lit)
                for ss in mutator.get_operations(
                    superset_op, types=F.Expressions.IsSubset, predicates_only=True
                )
                if (
                    lit := ss.get_subset_operand().try_get_sibling_trait(
                        F.Literals.is_literal
                    )
                )
            ]
            if not subset_ss:
                return SubsumptionCheck.Result()

            assert len(subset_ss) == 1, (
                f"multiple extant subsets violates invariant: {subset_ss}"
            )
            subset_ss, subset_lit = subset_ss[0]
            new_subset = builder.operands[0].as_literal.force_get()
            merged_subset = subset_lit.op_setic_union(
                new_subset, g=mutator.G_transient, tg=mutator.tg_in
            )
            if subset_lit.op_setic_equals(merged_subset):
                return SubsumptionCheck.Result(
                    most_constrained_expr=subset_ss.is_expression.get()
                )

            return SubsumptionCheck.Result(
                ExpressionBuilder(
                    IsSubset,
                    [merged_subset.as_operand.get(), superset_op.as_operand.get()],
                    assert_=True,
                    terminate=False,
                ),
                subsumed=[subset_ss.is_expression.get()],
            )

        assert False, "Unreachable"

    @staticmethod
    def or_(
        mutator: Mutator,
        builder: "ExpressionBuilder",
    ) -> Result:
        """
        Or!(A, B, C), Or!(A, B) -> Or!(A, B)
        Or!(A, B, False/{True, False}) -> Or!(A, B)
        Or!(A, B, True) -> discard (no information)
        """

        if any(
            lit.op_setic_equals_singleton(True)
            for lit in builder.indexed_lits().values()
        ):
            if builder.assert_:
                return SubsumptionCheck.Result(SubsumptionCheck.Result._DISCARD())
            else:
                # other algorithm will deal with this (no invariant)
                return SubsumptionCheck.Result()

        # filter out False/{True, False}
        new_operands = [po.as_operand.get() for po in builder.indexed_pos().values()]

        def _operands_are_subset(
            candidate_operands: Sequence[F.Parameters.can_be_operand],
            new_operands: Sequence[F.Parameters.can_be_operand],
        ) -> bool:
            """
            Check if new operands are a subset of candidate operands (by identity).
            Used for Or subsumption: Or(A, B) subsumes Or(A, B, C).
            """
            if len(new_operands) > len(candidate_operands):
                return False

            def _get_uuid(op: F.Parameters.can_be_operand) -> int | None:
                if (po := op.as_parameter_operatable.try_get()) is not None:
                    return po.instance.node().get_uuid()
                if (lit := op.as_literal.try_get()) is not None:
                    return lit.instance.node().get_uuid()
                return None

            candidate_uuids = {_get_uuid(op) for op in candidate_operands}
            return all(_get_uuid(op) in candidate_uuids for op in new_operands)

        ors = [
            mutator.get_operations(
                op.as_parameter_operatable.force_get(),
                types=F.Expressions.Or,
                predicates_only=True,
            )
            for op in new_operands
        ]
        if not ors:
            return SubsumptionCheck.Result()

        could_be_subsumed = reduce(lambda x, y: x & y, ors)

        subsumed: list[F.Expressions.is_expression] = []
        if builder.assert_:
            for candidate in could_be_subsumed:
                candidate_expr = candidate.get_trait(F.Expressions.is_expression)
                if _operands_are_subset(candidate_expr.get_operands(), new_operands):
                    subsumed.append(candidate_expr)
        if subsumed:
            return SubsumptionCheck.Result(subsumed=subsumed)

        could_subsume = reduce(lambda x, y: x | y, ors) - could_be_subsumed
        # returning first subsuming expression
        # careful: Or(A, B, C, D) is subsumed by Or(A, B) or Or(C, D)
        # TODO: think whether it's ok to return any of the ambiguous cases
        for candidate in could_subsume:
            candidate_expr = candidate.get_trait(F.Expressions.is_expression)
            if _operands_are_subset(
                new_operands,
                candidate_expr.get_operands(),
            ):
                return SubsumptionCheck.Result(most_constrained_expr=candidate_expr)

        return SubsumptionCheck.Result()


def find_subsuming_expression(
    mutator: Mutator,
    builder: "ExpressionBuilder",
) -> SubsumptionCheck.Result:
    # TODO use right graph
    match builder.factory:
        case F.Expressions.IsSubset:
            return SubsumptionCheck.subset(mutator, builder)
        case F.Expressions.Or:
            return SubsumptionCheck.or_(mutator, builder)
        case _:
            return SubsumptionCheck.Result()


def find_congruent_expression[T: F.Expressions.ExpressionNodes](
    mutator: Mutator,
    builder: "ExpressionBuilder[T]",
    allow_uncorrelated_congruence_match: bool = False,
) -> T | None:
    """
    Careful: Disregards asserted (on purpose)!
    """
    allow_uncorrelated = (
        builder.assert_
        or allow_uncorrelated_congruence_match
        # TODO use setic trait instead
        or builder.factory in [F.Expressions.IsSubset]
    )
    non_lits = list(builder.indexed_pos().values())
    if not non_lits:
        lit_ops = {
            op
            for op in builder.factory.bind_typegraph(mutator.tg_in).get_instances(
                mutator.G_out
            )
            if mutator.utils.is_literal_expression(
                op.get_trait(F.Parameters.can_be_operand)
            )
            # check congruence
            and F.Expressions.is_expression.are_pos_congruent(
                op.get_trait(F.Expressions.is_expression).get_operands(),
                builder.operands,
                g=mutator.G_transient,
                tg=mutator.tg_in,
                allow_uncorrelated=allow_uncorrelated,
            )
        }
        if lit_ops:
            return next(iter(lit_ops))
        return None

    candidates = next(iter(non_lits)).get_operations(builder.factory)

    for c in candidates:
        if c.get_trait(F.Expressions.is_expression).is_congruent_to_factory(
            builder.factory,
            builder.operands,
            g=mutator.G_transient,
            tg=mutator.tg_in,
            allow_uncorrelated=allow_uncorrelated,
            check_constrained=False,
            # inductive, if subexpression was congruent to another expression
            # it would have already been merged
            # helps with performance
            recursive=False,
        ):
            return c
    return None


class InsertExpressionResult(NamedTuple):
    # TODO: i dont think we should return cbo, even in fold case we return expr
    out_operand: F.Parameters.can_be_operand | None
    """
    None if expression dropped. Can only happen for predicates
    """
    is_new: bool


class ExpressionBuilder[
    T: F.Expressions.ExpressionNodes = F.Expressions.ExpressionNodes
](NamedTuple):
    factory: type[T]
    operands: list[F.Parameters.can_be_operand]
    assert_: bool
    terminate: bool

    def indexed_ops(self) -> dict[int, F.Parameters.can_be_operand]:
        return {i: o for i, o in enumerate(self.operands)}

    def indexed_ops_with_trait[TR: fabll.NodeT](self, trait: type[TR]) -> dict[int, TR]:
        return {
            i: op
            for i, o in self.indexed_ops().items()
            if (op := o.try_get_sibling_trait(trait))
        }

    def indexed_lits(self) -> dict[int, F.Literals.is_literal]:
        return self.indexed_ops_with_trait(F.Literals.is_literal)

    def indexed_pos(self) -> dict[int, F.Parameters.is_parameter_operatable]:
        return self.indexed_ops_with_trait(F.Parameters.is_parameter_operatable)

    def __repr__(self) -> str:
        return pretty_expr(self)

    def matches(self, other: F.Expressions.is_expression) -> bool:
        return (
            fabll.Traits(other).get_obj_raw().isinstance(self.factory)
            and other.get_operands() == self.operands
            and self.terminate == other.has_trait(is_terminated)
            and self.assert_ == other.has_trait(F.Expressions.is_predicate)
        )


def _no_empty_superset(
    mutator: Mutator,
    builder: ExpressionBuilder,
) -> None:
    """
    A ss! {} => Contradiction.
    """
    factory, operands, assert_, _ = builder
    if (
        factory is IsSubset
        and assert_
        and (lit := operands[1].try_get_sibling_trait(F.Literals.is_literal))
        and lit.op_setic_is_empty()
        and (po := operands[0].as_parameter_operatable.try_get())
    ):
        raise Contradiction(
            "Empty superset for parameter operatable",
            [po],
            mutator,
        )


def _no_predicate_literals(
    mutator: Mutator, builder: ExpressionBuilder
) -> ExpressionBuilder | None:
    """
    P!{S/P|False} -> Contradiction
    P {S|True} -> P!
    P! ss! True / True ss! P! -> Drop (carries no information)
    """

    # FIXME: important
    #  if we assert an expression then we need to uphold the invariant
    #   that it's not used as operand

    factory, operands, assert_, _ = builder
    if not (factory is F.Expressions.IsSubset and assert_):
        return builder

    if not (lits := builder.indexed_lits()):
        return builder

    # P!{S|False} -> Contradiction
    if operands[0].try_get_sibling_trait(F.Expressions.is_predicate) and any(
        lit.op_setic_equals_singleton(False) for lit in lits.values()
    ):
        raise Contradiction(
            "P!{S/P|False}",
            involved=[],
            mutator=mutator,
        )

    if any(lit.op_setic_equals_singleton(True) for lit in lits.values()):
        # P!{S/P|True} -> P!
        if any(op.try_get_sibling_trait(F.Expressions.is_predicate) for op in operands):
            logger.debug(f"Remove predicate literal {pretty_expr(builder, mutator)}")
            return None
        # P {S|True} -> P!
        if pred := operands[0].try_get_sibling_trait(F.Expressions.is_assertable):
            before = pred.as_expression.get().compact_repr(mutator.print_ctx)
            mutator.assert_(pred)
            after = pred.as_expression.get().compact_repr(mutator.print_ctx)
            logger.debug(f"Assert implicit predicate `{before}` -> `{after}`")
            return None

    return builder


def _no_literal_inequalities(
    mutator: Mutator, builder: ExpressionBuilder
) -> ExpressionBuilder:
    """
    Convert GreaterOrEqual expressions with literals to IsSubset constraints:
    - A >=! X (X is literal) -> A ss! [X.max(), +∞)
    - X >=! A (X is literal) -> A ss! (-∞, X.min()]
    Important: only valid for predicates

    This transformation is semantically equivalent:
    - "A is at least X" becomes "A is a subset of [X, infinity)"
    - "A is at most X" becomes "A is a subset of (-infinity, X]"
    """
    import math

    factory, operands, assert_, terminate = builder

    if factory is not F.Expressions.GreaterOrEqual or not assert_:
        return builder

    if not (lits := builder.indexed_lits()):
        return builder

    # Case: A >=! X -> A ss! [X.max(), +∞)
    # The parameter operatable A must be >= the maximum value of literal X
    if lit := lits.get(1):
        po_operand = operands[0]
        lit_num = fabll.Traits(lit).get_obj(F.Literals.Numbers)
        bound_val = lit_num.get_max_value()
        new_superset = mutator.utils.make_number_literal_from_range(bound_val, math.inf)
    # Case: X >=! A -> A ss! (-∞, X.min()]
    # The parameter operatable A must be <= the minimum value of literal X
    else:
        lit = lits[0]
        po_operand = operands[1]
        lit_num = fabll.Traits(lit).get_obj(F.Literals.Numbers)
        bound_val = lit_num.get_min_value()
        new_superset = mutator.utils.make_number_literal_from_range(
            -math.inf, bound_val
        )

    new_operands = [po_operand, new_superset.can_be_operand.get()]
    new_builder = cast(
        ExpressionBuilder, ExpressionBuilder(IsSubset, new_operands, assert_, terminate)
    )  # TODO fuck you pyright

    logger.debug(
        f"Converting {pretty_expr(builder, mutator)} ->"
        f" {pretty_expr(new_builder, mutator)}"
    )
    return new_builder


def _no_predicate_operands(
    mutator: Mutator,
    builder: ExpressionBuilder,
) -> ExpressionBuilder:
    """
    don't use predicates as operands:
    Op(P!, ...) -> Op(True, ...)
    """
    _, operands, _, _ = builder

    new_operands = [
        mutator.make_singleton(True).can_be_operand.get()
        if op.try_get_sibling_trait(F.Expressions.is_predicate)
        else op
        for op in operands
    ]

    new_builder = ExpressionBuilder(
        builder.factory, new_operands, builder.assert_, builder.terminate
    )

    if new_operands != operands:
        logger.debug(
            f"Predicate operands: {pretty_expr(builder, mutator)} ->"
            f" {pretty_expr(new_builder, mutator)}"
        )

    return new_builder


def _fold_pure_literal_operands(
    mutator: Mutator, builder: ExpressionBuilder
) -> InsertExpressionResult | None:
    """
    Fold pure literal operands: E(X, Y) -> E{S/P|...}(X, Y)
    No pure P!
    """
    from faebryk.core.solver.symbolic.pure_literal import exec_pure_literal_operands

    if not (
        lit_fold := exec_pure_literal_operands(
            mutator.G_transient, mutator.tg_out, builder.factory, builder.operands
        )
    ):
        return None

    logger.debug(
        f"Folded ({pretty_expr(builder, mutator)}) to literal {lit_fold.pretty_str()}"
    )
    if builder.assert_:
        # P!{S|True} -> P!$
        if lit_fold.op_setic_equals_singleton(False):
            raise ContradictionByLiteral(
                "P!{S|False}",
                involved=[],
                literals=[lit_fold],
                mutator=mutator,
            )
        else:
            # True / {False,True}
            return InsertExpressionResult(None, False)

    new_expr = mutator._create_and_insert_expression(
        builder.factory,
        *builder.operands,
        assert_=builder.assert_,
        terminate=True,
    )
    new_expr_op = new_expr.get_trait(F.Parameters.can_be_operand)
    lit_op = lit_fold.as_operand.get()
    mutator.create_check_and_insert_expression(
        F.Expressions.IsSubset,
        new_expr_op,
        lit_op,
        terminate=True,
        assert_=True,
        from_ops=[],
    )
    mutator.create_check_and_insert_expression(
        F.Expressions.IsSubset,
        lit_op,
        new_expr_op,
        terminate=True,
        assert_=True,
        from_ops=[],
    )
    return InsertExpressionResult(new_expr_op, True)


def _fold_unpure_literal_operands(
    mutator: Mutator, builder: ExpressionBuilder
) -> InsertExpressionResult | None:
    """
    Fold unpure literal operands: f1(f2(X)) ⊆! eval(f1(f2(X)))
    """
    from faebryk.core.solver.symbolic.pure_literal import exec_pure_literal_operands

    # TODO use setic trait instead
    if builder.factory in [F.Expressions.IsSubset, F.Expressions.Is]:
        return None

    if not (
        not builder.indexed_ops_with_trait(F.Parameters.is_parameter)
        and all(
            mutator.utils.is_literal_expression(op.as_operand.get())
            for op in builder.indexed_ops_with_trait(
                F.Expressions.is_expression
            ).values()
        )
    ):
        return None

    lit_operands = [
        lit
        if (lit := op.try_get_sibling_trait(F.Literals.is_literal))
        # inner literal expression has already superset due to invariant
        else not_none(
            mutator.utils.try_extract_superset(op.as_parameter_operatable.force_get())
        )
        for op in builder.operands
    ]

    operands = [op.as_operand.get() for op in lit_operands]
    folded_lit = exec_pure_literal_operands(
        mutator.G_transient, mutator.tg_out, builder.factory, operands
    )
    if folded_lit is None:
        return None

    folded_lit_op = folded_lit.as_operand.get()
    new_expr = mutator._create_and_insert_expression(
        builder.factory, *operands, assert_=builder.assert_, terminate=builder.terminate
    )
    new_expr_op = new_expr.get_trait(F.Parameters.can_be_operand)
    mutator.create_check_and_insert_expression(
        F.Expressions.IsSubset,
        new_expr_op,
        folded_lit_op,
        terminate=True,
        assert_=True,
        from_ops=[],
    )

    return InsertExpressionResult(new_expr_op, True)


def _no_literal_aliases(
    mutator: Mutator,
    builder: ExpressionBuilder,
) -> ExpressionBuilder:
    """
    no literal aliases: A is! X(singleton) => A ss! X
    A is! X in general not allowed
    X is! Y is handled by literal fold
    """
    if builder.factory is not F.Expressions.Is or not (lits := builder.indexed_lits()):
        return builder

    non_lit = builder.indexed_pos()
    if not non_lit:
        return builder

    correlatable = {
        i: lit for i, lit in lits.items() if mutator.utils.is_correlatable_literal(lit)
    }
    has_non_correlatable = len(correlatable) < len(lits)
    if has_non_correlatable:
        raise ValueError(
            f"Is with literal not allowed: {pretty_expr(builder, mutator)}"
        )
    if len(correlatable) > 1:
        raise ValueError(
            f"Is with multiple literals not allowed: {pretty_expr(builder, mutator)}"
        )
    assert len(correlatable) == 1
    lit = next(iter(correlatable.values()))

    # TODO handle lit,lit; op,lit, lit,op etc, multi lit
    if len(non_lit) > 1:
        raise NotImplementedError(
            f"Is with multiple operands not allowed: {pretty_expr(builder, mutator)}"
        )
    assert len(non_lit) == 1
    non_lit_op = next(iter(non_lit.values())).as_operand.get()

    builder = ExpressionBuilder(
        F.Expressions.IsSubset,
        [non_lit_op, lit.as_operand.get()],
        builder.assert_,
        builder.terminate,
    )

    return builder


def _no_singleton_supersets(
    mutator: Mutator, builder: ExpressionBuilder
) -> ExpressionBuilder:
    """
    no singleton supersets
    f(A{S|[X]}, B, ...) -> f(X, B ...)

    not on
    - A{S|{X]} ss! X
    - X ss! A{S|{X]}
    """
    lits = builder.indexed_lits()
    if builder.factory is F.Expressions.IsSubset and builder.assert_ and lits:
        return builder

    mapped_operands = [
        lit.as_operand.get()
        if (lit := mutator.utils.is_replacable_by_literal(op))
        else op
        for op in builder.operands
    ]
    if mapped_operands == builder.operands:
        return builder

    out = ExpressionBuilder(
        builder.factory, mapped_operands, builder.assert_, builder.terminate
    )
    logger.debug(
        f"No singleton supersets: {pretty_expr(builder, mutator)} -> "
        f"{pretty_expr(out, mutator)}"
    )
    return out


def insert_expression(
    mutator: Mutator,
    builder: ExpressionBuilder,
    expr_already_exists_in_old_graph: bool = False,
    allow_uncorrelated_congruence_match: bool = False,
) -> InsertExpressionResult:
    """
    Invariants
    Sequencing sensitive!
    * ✓ terminated expressions are already copied
    * TODO: don't mutate terminated expressions?
    * TODO: terminate?
    * ✓ don't use predicates as operands: Op(P!, ...) -> Op(True, ...)
    * ✓ P{S|True} -> P!, P!{S/P|False} -> Contradiction, P!{S|True} -> P!
    * ✓ no A >! X or X >! A (create A ss! X or X ss! A)
    * ✓ no singleton supersets: f(A{S|[X]}, B, ...) -> f(X, B ...)
    * ✓ no congruence
    * ✓ minimal subsumption
    * ✓ - intersected supersets (single superset)
    * ✓ no empty supersets
    * ✓ fold pure literal expressions: E(X, Y) -> E{S/P|...}(X, Y)
    * - no pure P!
    * ✓ superset estimate lit exprs: f1(f2(A{S|X})) ⊆! f1(f2(X))
    * ✓ canonical
    * no A is X(single) => A ss! X

    ====
    - allow_uncorrelated_congruence_match: sometimes it's okay to match uncorrelated literals
        that's mostly the case for operands of setic expressions
        e.g for A ss! B, if B is congruence matching B' we can replace
    """

    # TODO: congruence check is running on new graph only,
    #  thus expression might be incorrectly marked as new

    assert not builder.terminate or builder.assert_, "terminate ⟹ assert"

    # * terminated expressions are already copied
    mutator._copy_terminated()

    # * Op(P!, ...) -> Op(True, ...)
    builder = _no_predicate_operands(mutator, builder)

    # P!{S/P|False} -> Contradiction, P!{P|True} -> P!, P {S|True} -> P!
    builder_ = _no_predicate_literals(mutator, builder)
    if builder_ is None:
        return InsertExpressionResult(None, False)
    builder = builder_

    # * no A >! X or X >! A (create A ss! X or X ss! A)
    builder = _no_literal_inequalities(mutator, builder)

    # * f(A{S|[X]}, B, ...) |-> f(X, B ...)
    builder = _no_singleton_supersets(mutator, builder)

    # * no congruence
    if congruent := find_congruent_expression(
        mutator, builder, allow_uncorrelated_congruence_match
    ):
        if builder.assert_:
            congruent_assertable = congruent.get_trait(F.Expressions.is_assertable)
            mutator.assert_(congruent_assertable)
        if builder.terminate:
            congruent_predicate = congruent.get_trait(F.Expressions.is_predicate)
            mutator.predicate_terminate(congruent_predicate)
        congruent_op = congruent.get_trait(F.Parameters.can_be_operand)
        congruent_po = congruent_op.as_parameter_operatable.force_get()
        if expr_already_exists_in_old_graph:
            if congruent_po in mutator.transformations.created:
                del mutator.transformations.created[congruent_po]
            if builder.assert_:
                congruent_assertable = congruent_po.get_sibling_trait(
                    F.Expressions.is_assertable
                )
                if congruent_assertable in mutator.transformations.asserted:
                    mutator.transformations.asserted.remove(congruent_assertable)

        logger.debug(
            f"Found congruent expression for {pretty_expr(builder, mutator)}:"
            f" {congruent_op.pretty()}"
        )
        return InsertExpressionResult(congruent_op, False)

    # * minimal subsumption
    # Check for semantic subsumption (only for assertable)
    if builder.assert_ or builder.factory.bind_typegraph(
        mutator.tg_in
    ).check_if_instance_of_type_has_trait(F.Expressions.is_assertable):
        subsume_res = find_subsuming_expression(mutator, builder)
        if subsume_res.subsumed:
            logger.debug(
                f"Subsumed: {indented_container([s.compact_repr(mutator.mutation_map.print_ctx) for s in subsume_res.subsumed])}"
            )
        for subsumed in subsume_res.subsumed or []:
            subsumed_po = subsumed.as_parameter_operatable.get()
            mutator.mark_irrelevant(subsumed_po)
            if subsumed_po in mutator.transformations.created:
                del mutator.transformations.created[subsumed_po]

        if most_constrained_expr := subsume_res.most_constrained_expr:
            match most_constrained_expr:
                case F.Expressions.is_expression():
                    orig = pretty_expr(builder, mutator)
                    new = pretty_expr(most_constrained_expr, mutator)
                    if new == orig:
                        new = "congruent"
                    logger.debug(f"Subsume replaced: {orig} -> {new}")
                    return InsertExpressionResult(
                        most_constrained_expr.as_operand.get(), False
                    )
                case ExpressionBuilder():
                    builder = most_constrained_expr
                    logger.debug(f"Subsume adjust {pretty_expr(builder, mutator)}")

                case SubsumptionCheck.Result._DISCARD():
                    logger.debug(f"Subsume discard: {pretty_expr(builder, mutator)}")
                    return InsertExpressionResult(None, False)
    # * no empty supersets
    _no_empty_superset(mutator, builder)

    # no A is! X
    builder = _no_literal_aliases(mutator, builder)

    # * fold pure literal expressions
    # needs to run last since it creates new expressions
    # folding to literal will result in ss/sup in mutator.mutate_expression
    if lit_fold := _fold_pure_literal_operands(mutator, builder):
        return lit_fold

    if lit_fold := _fold_unpure_literal_operands(mutator, builder):
        return lit_fold

    # TODO remove
    # terminate ss lit
    if (
        builder.factory is F.Expressions.IsSubset
        and builder.assert_
        and builder.indexed_lits
        and not builder.terminate
    ):
        logger.debug(f"Terminate ss lit: {pretty_expr(builder, mutator)}")
        builder = ExpressionBuilder(
            F.Expressions.IsSubset,
            builder.operands,
            builder.assert_,
            terminate=True,
        )

    # * canonical (covered by create)
    expr = mutator._create_and_insert_expression(
        builder.factory,
        *builder.operands,
        assert_=builder.assert_,
        terminate=builder.terminate,
    )
    return InsertExpressionResult(expr.get_trait(F.Parameters.can_be_operand), True)


def wrap_insert_expression(
    mutator: Mutator,
    builder: ExpressionBuilder,
    expr_already_exists_in_old_graph: bool = False,
    allow_uncorrelated_congruence_match: bool = False,
) -> InsertExpressionResult:
    res = insert_expression(
        mutator,
        builder,
        expr_already_exists_in_old_graph=expr_already_exists_in_old_graph,
        allow_uncorrelated_congruence_match=allow_uncorrelated_congruence_match,
    )
    src_dbg = f"`{pretty_expr(builder, mutator)}`"
    if res.out_operand is None:
        target_dbg = "Dropped"
    else:
        op = res.out_operand
        if (
            op_e := op.try_get_sibling_trait(F.Expressions.is_expression)
        ) and builder.matches(op_e):
            target_dbg = "COPY"
        else:
            ctx = mutator.mutation_map.print_ctx
            target_dbg = f"`{op.pretty(context=ctx)}`"

        if target_dbg == src_dbg:
            target_dbg = (
                f"NOOP (assert: {builder.assert_}, terminate: {builder.terminate})"
            )
    # TODO debug
    # if target_dbg != "COPY":
    logger.warning(f"{src_dbg} -> {target_dbg}")

    return res


class TestInvariantsSimple:
    @staticmethod
    def _setup_mutator() -> Mutator:
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        mut_map = MutationMap.bootstrap(tg, g)
        mutator = Mutator(
            mut_map,
            algo=SolverAlgorithm(
                "test",
                lambda x: None,
                single=False,
                terminal=False,
                force_copy=False,
            ),
            iteration=1,
            terminal=False,
        )
        return mutator

    @staticmethod
    def test_predicate_operands():
        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Not!(p)
        pred_res = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=True,
        )
        pred_op = not_none(pred_res.out_operand)

        # Or(Not!(p), p)
        or_res = mutator.create_check_and_insert_expression(
            F.Expressions.Or,
            pred_op,
            p_op,
            assert_=False,
            terminate=False,
        )

        # => Or(True, p)
        assert or_res.out_operand and or_res.out_operand.get_sibling_trait(
            F.Expressions.is_expression
        ).get_operands()[0].get_sibling_trait(
            F.Literals.is_literal
        ).op_setic_equals_singleton(True)

    @staticmethod
    def test_pure_literal():
        """
        Invariant: fold pure literal expressions: E(X, Y) -> E{S/P|...}(X, Y)
        Pure literal operations are computed and bound as superset constraints.
        """
        mutator = TestInvariantsSimple._setup_mutator()

        pred_res = mutator.create_check_and_insert_expression(
            F.Expressions.Add,
            mutator.utils.make_number_literal_from_range(10, 20).can_be_operand.get(),
            mutator.utils.make_number_literal_from_range(30, 40).can_be_operand.get(),
        )

        assert (
            pred_res.out_operand
            and pred_res.out_operand.as_parameter_operatable.force_get()
            .force_extract_superset()
            .op_setic_equals(
                F.Literals.Numbers.bind_typegraph(mutator.tg_in)
                .create_instance(mutator.G_transient)
                .setup_from_min_max(40, 60)
            )
        )

    # --- Invariant: P{S|True} -> P!, P!{S/P|False} -> Contradiction ---

    @staticmethod
    def test_predicate_literal_true_asserts():
        """
        Invariant: P{S|True} -> P!
        When an unasserted predicate has a True literal operand via IsSubset,
        it should become asserted.
        """
        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Create an expression (the candidate predicate)
        not_res = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=False,  # Not asserted initially
        )
        not_op = not_none(not_res.out_operand)

        # Assert IsSubset(Not(p), True) - this should trigger P{S|True} -> P!
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            not_op,
            mutator.make_singleton(True).can_be_operand.get(),
            assert_=True,
        )

        # The Not expression should now be asserted (become a predicate)
        assert not_op.try_get_sibling_trait(F.Expressions.is_predicate) is not None

    @staticmethod
    def test_predicate_literal_false_contradiction():
        """
        Invariant: P!{S/P|False} -> Contradiction
        When an asserted predicate is constrained to be subset of False, contradiction.
        Tests _no_predicate_literals directly.
        """
        import pytest

        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Create an asserted predicate Not!(p)
        not_res = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=True,
        )
        not_op = not_none(not_res.out_operand)

        # Test _no_predicate_literals directly with IsSubset(P!, False)
        false_lit = mutator.make_singleton(False).can_be_operand.get()
        builder = ExpressionBuilder(
            F.Expressions.IsSubset,
            [not_op, false_lit],
            assert_=True,
            terminate=False,
        )

        with pytest.raises(Contradiction):
            _no_predicate_literals(mutator, builder)

    @staticmethod
    def test_asserted_predicate_literal_true_drops():
        """
        Invariant: P!{S|True} -> P! (no-op, expression dropped)
        Asserting IsSubset(P!, True) is redundant and should return None.
        Tests _no_predicate_literals directly.
        """
        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Create an asserted predicate Not!(p)
        not_res = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=True,
        )
        not_op = not_none(not_res.out_operand)

        # Test _no_predicate_literals directly with IsSubset(P!, True)
        true_lit = mutator.make_singleton(True).can_be_operand.get()
        builder = ExpressionBuilder(
            F.Expressions.IsSubset,
            [not_op, true_lit],
            assert_=True,
            terminate=False,
        )

        # Should return None (expression dropped - no information added)
        result = _no_predicate_literals(mutator, builder)
        assert result is None

    # --- Invariant: no A >! X or X >! A (create A ss! X or X ss! A) ---

    @staticmethod
    def test_greater_or_equal_literal_converts_to_subset():
        """
        Invariant: no A >! X or X >! A (create A ss! X)
        A >= X (X is literal) -> A ss [X.max(), +∞)
        """
        import math

        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        # Create A >= 5 (literal on right)
        lit = mutator.utils.make_number_literal_from_range(5, 5)
        result = mutator.create_check_and_insert_expression(
            F.Expressions.GreaterOrEqual,
            p_op,
            lit.can_be_operand.get(),
            assert_=True,
        )

        # Should be converted to IsSubset with range [5, +∞)
        assert result.out_operand is not None
        expr = result.out_operand.get_sibling_trait(F.Expressions.is_expression)
        expr_obj = fabll.Traits(expr).get_obj_raw()
        assert expr_obj.isinstance(F.Expressions.IsSubset)

        # Check that the superset is [5, +∞)
        operands = expr.get_operands()
        superset_lit = operands[1].get_sibling_trait(F.Literals.is_literal)
        superset_nums = fabll.Traits(superset_lit).get_obj(F.Literals.Numbers)
        assert superset_nums.get_min_value() == 5
        assert superset_nums.get_max_value() == math.inf

    @staticmethod
    def test_literal_greater_or_equal_converts_to_subset():
        """
        Invariant: no X >! A (create A ss! X)
        X >= A (X is literal) -> A ss (-∞, X.min()]
        """
        import math

        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        # Create 10 >= A (literal on left)
        lit = mutator.utils.make_number_literal_from_range(10, 10)
        result = mutator.create_check_and_insert_expression(
            F.Expressions.GreaterOrEqual,
            lit.can_be_operand.get(),
            p_op,
            assert_=True,
        )

        # Should be converted to IsSubset with range (-∞, 10]
        assert result.out_operand is not None
        expr = result.out_operand.get_sibling_trait(F.Expressions.is_expression)
        expr_obj = fabll.Traits(expr).get_obj_raw()
        assert expr_obj.isinstance(F.Expressions.IsSubset)

        # Check that the superset is (-∞, 10]
        operands = expr.get_operands()
        superset_lit = operands[1].get_sibling_trait(F.Literals.is_literal)
        superset_nums = fabll.Traits(superset_lit).get_obj(F.Literals.Numbers)
        assert superset_nums.get_min_value() == -math.inf
        assert superset_nums.get_max_value() == 10

    # --- Invariant: no congruence ---

    @staticmethod
    def test_no_congruent_expressions():
        """
        Invariant: no congruence
        Creating the same expression twice should return the existing one.
        """
        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Create Not(p)
        res1 = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=False,
        )
        assert res1.is_new

        # Create Not(p) again - should return existing
        res2 = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=False,
        )
        assert not res2.is_new

        # Should be the same expression
        assert (
            res1.out_operand
            and res2.out_operand
            and res1.out_operand.is_same(res2.out_operand)
        )

    @staticmethod
    def test_congruent_expression_asserts_existing():
        """
        Invariant: no congruence
        Creating an asserted version of existing expression should assert it.
        """
        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Create Not(p) unasserted
        res1 = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=False,
        )
        assert res1.out_operand is not None
        is_pred = res1.out_operand.try_get_sibling_trait(F.Expressions.is_predicate)
        assert is_pred is None

        # Create Not(p) asserted - should assert the existing one
        res2 = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=True,
        )
        assert not res2.is_new

        # The existing expression should now be asserted
        is_pred = res1.out_operand.try_get_sibling_trait(F.Expressions.is_predicate)
        assert is_pred is not None

    # --- Invariant: minimal subsumption (intersected supersets) ---

    @staticmethod
    def test_subsumption_intersected_supersets():
        """
        Invariant: A ss! X, A ss! Y -> A ss! X ∩ Y
        Multiple superset constraints on same parameter should be intersected.
        Tests SubsumptionCheck.subset directly.
        """
        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        # Create first subset constraint A ss! [0, 100]
        lit1 = mutator.utils.make_number_literal_from_range(0, 100)
        res1 = mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            p_op,
            lit1.can_be_operand.get(),
            assert_=True,
        )
        assert res1.is_new

        # Now test subsumption check for A ss! [50, 150]
        lit2 = mutator.utils.make_number_literal_from_range(50, 150)
        subsume_result = SubsumptionCheck.subset(
            mutator,
            ExpressionBuilder(
                F.Expressions.IsSubset,
                [p_op, lit2.can_be_operand.get()],
                assert_=True,
                terminate=False,
            ),
        )

        # Subsumption should return a builder with intersected range
        assert isinstance(subsume_result.most_constrained_expr, ExpressionBuilder)
        new_operands = subsume_result.most_constrained_expr.operands
        new_superset = new_operands[1].get_sibling_trait(F.Literals.is_literal)
        new_superset_nums = fabll.Traits(new_superset).get_obj(F.Literals.Numbers)
        # The intersected range should be [50, 100]
        assert new_superset_nums.get_min_value() == 50
        assert new_superset_nums.get_max_value() == 100

    # --- Invariant: no empty supersets ---

    @staticmethod
    def test_no_empty_superset():
        """
        Invariant: A ss! {} => Contradiction
        Constraining a parameter to an empty set should raise Contradiction.
        Tests _no_empty_superset directly using a string literal (empty set).
        """
        import pytest

        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.StringParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Create an empty string literal set
        empty_lit = (
            F.Literals.Strings.bind_typegraph(mutator.tg_in).create_instance(
                mutator.G_transient
            )
            # Empty - no values added
        )
        assert empty_lit.is_empty()

        # Test _no_empty_superset directly
        builder = ExpressionBuilder(
            F.Expressions.IsSubset,
            [p_op, empty_lit.can_be_operand.get()],
            assert_=True,
            terminate=False,
        )

        with pytest.raises(Contradiction):
            _no_empty_superset(mutator, builder)

    @staticmethod
    def test_intersected_supersets_become_empty_contradiction():
        """
        Invariant: A ss! {} => Contradiction
        When two supersets intersect to empty, should raise Contradiction.
        Tests via SubsumptionCheck.subset detecting empty intersection.
        """
        import pytest

        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.StringParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Create A ss! {"a", "b"}
        lit1 = (
            F.Literals.Strings.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_transient)
            .setup_from_values("a", "b")
        )
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            p_op,
            lit1.can_be_operand.get(),
            assert_=True,
        )

        # Create A ss! {"c", "d"} - intersection with {"a", "b"} is empty
        lit2 = (
            F.Literals.Strings.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_transient)
            .setup_from_values("c", "d")
        )

        # The intersection should be empty, causing Contradiction
        with pytest.raises(Contradiction):
            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                p_op,
                lit2.can_be_operand.get(),
                assert_=True,
            )

    # --- Invariant: canonical ---

    @staticmethod
    def test_expression_is_canonical():
        """
        Invariant: expressions are created in canonical form.
        The is_canonical trait should be present on created expressions.
        """
        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        # Create Add(p, p) - should have is_canonical
        result = mutator.create_check_and_insert_expression(
            F.Expressions.Add,
            p_op,
            p_op,
        )

        assert result.out_operand is not None
        expr = result.out_operand.get_sibling_trait(F.Expressions.is_expression)
        # Check canonical via is_canonical trait (if the expression type has it)
        canon = expr.as_canonical.try_get()
        # Add has is_canonical trait
        assert canon is not None

    @staticmethod
    def test_is_expression_has_canonical_trait():
        """
        Invariant: canonical
        Expressions that support canonicalization have the is_canonical trait.
        """
        mutator = TestInvariantsSimple._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        # Is expression should have canonical trait
        q = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        q_op = q.can_be_operand.get()

        # Is(p, q) - Is has is_canonical trait
        is_result = mutator.create_check_and_insert_expression(
            F.Expressions.Is,
            p_op,
            q_op,
            assert_=True,
        )

        assert is_result.out_operand is not None
        expr = is_result.out_operand.get_sibling_trait(F.Expressions.is_expression)
        canon = expr.as_canonical.try_get()
        assert canon is not None


class TestInvariantsCombinations:
    """
    Tests that verify multiple invariants work correctly together.
    These catch edge cases where individual invariants might conflict or
    where complex expression chains could violate invariants.
    """

    @staticmethod
    def _setup_mutator() -> Mutator:
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        mut_map = MutationMap.bootstrap(tg, g)
        mutator = Mutator(
            mut_map,
            algo=SolverAlgorithm(
                "test",
                lambda x: None,
                single=False,
                terminal=False,
                force_copy=False,
            ),
            iteration=1,
            terminal=False,
        )
        return mutator

    @staticmethod
    def test_predicate_operand_replacement_direct():
        """
        Combines: predicate operands → True.
        Tests _no_predicate_operands directly to avoid recursion issues.
        """
        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Create asserted predicate Not!(p)
        not_res = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=True,
        )
        pred_op = not_none(not_res.out_operand)

        true_lit = mutator.make_singleton(True).can_be_operand.get()

        # Test _no_predicate_operands directly
        builder = ExpressionBuilder(
            F.Expressions.Or,
            [pred_op, true_lit],
            assert_=False,
            terminate=False,
        )

        result = _no_predicate_operands(mutator, builder)

        # First operand should now be True (predicate replaced)
        first_op = result.operands[0]
        first_lit = first_op.try_get_sibling_trait(F.Literals.is_literal)
        assert first_lit is not None and first_lit.op_setic_equals_singleton(True)

    @staticmethod
    def test_greater_or_equal_chain_intersects_to_contradiction():
        """
        Combines: GreaterOrEqual→IsSubset conversion, subsumption intersection.
        A >= 10 AND 5 >= A should:
        1. Convert A >= 10 to A ss! [10, +∞) (inequality conversion)
        2. Convert 5 >= A to A ss! (-∞, 5] (inequality conversion)
        3. Intersect to A ss! {} (subsumption intersection)
        4. Raise Contradiction (no empty supersets)
        """
        import pytest

        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        # A >= 10 → A ss! [10, +∞)
        lit10 = mutator.utils.make_number_literal_from_range(10, 10)
        mutator.create_check_and_insert_expression(
            F.Expressions.GreaterOrEqual,
            p_op,
            lit10.can_be_operand.get(),
            assert_=True,
        )

        # 5 >= A → A ss! (-∞, 5] - intersection with [10, +∞) is empty
        lit5 = mutator.utils.make_number_literal_from_range(5, 5)
        with pytest.raises(Contradiction):
            mutator.create_check_and_insert_expression(
                F.Expressions.GreaterOrEqual,
                lit5.can_be_operand.get(),
                p_op,
                assert_=True,
            )

    @staticmethod
    def test_congruence_with_assertion_propagation():
        """
        Combines: congruence detection, assertion propagation.
        1. Create Not(p) unasserted
        2. Create Not(p) asserted
        3. Both should share the same expression node
        4. The shared expression should be asserted
        """
        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # Create Not(p) unasserted
        not_res = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=False,
        )
        assert not_res.is_new
        assert not_res.out_operand is not None
        is_pred = not_res.out_operand.try_get_sibling_trait(F.Expressions.is_predicate)
        assert is_pred is None

        # Create congruent Not(p) asserted - should assert existing
        not_res2 = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p_op,
            assert_=True,
        )
        assert not not_res2.is_new

        # Original should now be asserted
        is_pred = not_res.out_operand.try_get_sibling_trait(F.Expressions.is_predicate)
        assert is_pred is not None

    @staticmethod
    def test_nested_predicate_replacement_direct():
        """
        Combines: multiple predicate operands in single expression.
        Or(P1!, P2!) should replace both predicates with True.
        Tests _no_predicate_operands directly.
        """
        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        q = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )

        # Create two asserted predicates
        not_p = mutator.create_check_and_insert_expression(
            F.Expressions.Not, p.can_be_operand.get(), assert_=True
        )
        not_q = mutator.create_check_and_insert_expression(
            F.Expressions.Not, q.can_be_operand.get(), assert_=True
        )

        # Test _no_predicate_operands directly
        builder = ExpressionBuilder(
            F.Expressions.Or,
            [not_none(not_p.out_operand), not_none(not_q.out_operand)],
            assert_=False,
            terminate=False,
        )

        result = _no_predicate_operands(mutator, builder)

        # Both operands should now be True literals
        for op in result.operands:
            lit = op.try_get_sibling_trait(F.Literals.is_literal)
            assert lit is not None and lit.op_setic_equals_singleton(True)

    @staticmethod
    def test_subsumption_with_subset_check():
        """
        Combines: subsumption, intersection check.
        Creating A ss! [0, 100] then checking subsumption for A ss! [50, 60] should:
        1. First creates new expression
        2. SubsumptionCheck.subset returns intersected range
        """
        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        # First constraint: A ss! [0, 100]
        lit1 = mutator.utils.make_number_literal_from_range(0, 100)
        res1 = mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            p_op,
            lit1.can_be_operand.get(),
            assert_=True,
        )
        assert res1.is_new

        # Test SubsumptionCheck for A ss! [50, 60]
        lit2 = mutator.utils.make_number_literal_from_range(50, 60)
        subsume_result = SubsumptionCheck.subset(
            mutator,
            ExpressionBuilder(
                F.Expressions.IsSubset,
                [p_op, lit2.can_be_operand.get()],
                assert_=True,
                terminate=False,
            ),
        )

        # Should return builder with intersected range [50, 60]
        assert isinstance(subsume_result.most_constrained_expr, ExpressionBuilder)
        new_operands = subsume_result.most_constrained_expr.operands
        new_superset = new_operands[1].get_sibling_trait(F.Literals.is_literal)
        new_superset_nums = fabll.Traits(new_superset).get_obj(F.Literals.Numbers)
        assert new_superset_nums.get_min_value() == 50
        assert new_superset_nums.get_max_value() == 60

    @staticmethod
    def test_inequality_to_subset_conversion_direct():
        """
        Combines: inequality→subset conversion.
        Tests _no_literal_inequalities directly.
        """
        import math

        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        lit5 = mutator.utils.make_number_literal_from_range(5, 5)

        # Test A >= 5 conversion
        builder = ExpressionBuilder(
            F.Expressions.GreaterOrEqual,
            [p_op, lit5.can_be_operand.get()],
            assert_=True,
            terminate=False,
        )

        result = _no_literal_inequalities(mutator, builder)

        # Should be converted to IsSubset
        assert result.factory is F.Expressions.IsSubset
        superset = result.operands[1].get_sibling_trait(F.Literals.is_literal)
        superset_nums = fabll.Traits(superset).get_obj(F.Literals.Numbers)
        assert superset_nums.get_min_value() == 5
        assert superset_nums.get_max_value() == math.inf

    @staticmethod
    def test_canonical_on_created_expression():
        """
        Combines: canonical form on expression creation.
        Ensure that created expressions have is_canonical trait.
        """
        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        # Create A ss! [0, 100]
        lit1 = mutator.utils.make_number_literal_from_range(0, 100)
        res1 = mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            p_op,
            lit1.can_be_operand.get(),
            assert_=True,
        )

        # Verify expression is canonical
        assert res1.out_operand is not None
        expr1 = res1.out_operand.get_sibling_trait(F.Expressions.is_expression)
        assert expr1.as_canonical.try_get() is not None

    @staticmethod
    def test_predicate_true_drop_with_nested_expression():
        """
        Combines: predicate literal drop, nested expressions.
        Create an expression tree, assert inner predicate to True,
        verify the redundant constraint is dropped.
        """
        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )

        # Create Not(p) - this is assertable
        not_res = mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            p.can_be_operand.get(),
            assert_=True,  # Assert it to make it a predicate
        )
        not_op = not_none(not_res.out_operand)

        # Now try to assert IsSubset(Not!(p), True) - should be dropped
        true_lit = mutator.make_singleton(True).can_be_operand.get()
        builder = ExpressionBuilder(
            F.Expressions.IsSubset,
            [not_op, true_lit],
            assert_=True,
            terminate=False,
        )

        # _no_predicate_literals should return None (drop the expression)
        result = _no_predicate_literals(mutator, builder)
        assert result is None

    @staticmethod
    def test_multiple_inequality_conversions_direct():
        """
        Combines: multiple inequality→subset conversions.
        Test conversion invariants directly.
        """
        import math

        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        p_op = p.can_be_operand.get()

        # Test A >= 20 conversion
        lit20 = mutator.utils.make_number_literal_from_range(20, 20)
        builder1 = ExpressionBuilder(
            F.Expressions.GreaterOrEqual,
            [p_op, lit20.can_be_operand.get()],
            assert_=True,
            terminate=False,
        )
        result1 = _no_literal_inequalities(mutator, builder1)
        assert result1.factory is F.Expressions.IsSubset
        superset1 = result1.operands[1].get_sibling_trait(F.Literals.is_literal)
        superset1_nums = fabll.Traits(superset1).get_obj(F.Literals.Numbers)
        assert superset1_nums.get_min_value() == 20
        assert superset1_nums.get_max_value() == math.inf

        # Test 50 >= A conversion
        lit50 = mutator.utils.make_number_literal_from_range(50, 50)
        builder2 = ExpressionBuilder(
            F.Expressions.GreaterOrEqual,
            [lit50.can_be_operand.get(), p_op],
            assert_=True,
            terminate=False,
        )
        result2 = _no_literal_inequalities(mutator, builder2)
        assert result2.factory is F.Expressions.IsSubset
        superset2 = result2.operands[1].get_sibling_trait(F.Literals.is_literal)
        superset2_nums = fabll.Traits(superset2).get_obj(F.Literals.Numbers)
        assert superset2_nums.get_min_value() == -math.inf
        assert superset2_nums.get_max_value() == 50

    @staticmethod
    def test_congruence_across_expression_types_with_same_operands():
        """
        Ensures different expression types with same operands are NOT congruent.
        Add(p, q) and Multiply(p, q) should be distinct.
        """
        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )
        q = (
            F.Parameters.NumericParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
        )

        # Create Add(p, q)
        add_res = mutator.create_check_and_insert_expression(
            F.Expressions.Add,
            p.can_be_operand.get(),
            q.can_be_operand.get(),
        )
        assert add_res.is_new

        # Create Multiply(p, q) - should be new (different type)
        mul_res = mutator.create_check_and_insert_expression(
            F.Expressions.Multiply,
            p.can_be_operand.get(),
            q.can_be_operand.get(),
        )
        assert mul_res.is_new

        # They should be different expressions
        assert add_res.out_operand is not None and mul_res.out_operand is not None
        assert not add_res.out_operand.is_same(mul_res.out_operand)

    @staticmethod
    def test_empty_superset_via_intersection():
        """
        Combines: subsumption intersection leading to empty superset.
        A ss! [0, 10] then A ss! [20, 30] should intersect to empty and contradict.
        Tests via direct subsumption check then _no_empty_superset.
        """
        import pytest

        mutator = TestInvariantsCombinations._setup_mutator()

        p = (
            F.Parameters.StringParameter.bind_typegraph(mutator.tg_out)
            .create_instance(mutator.G_out)
            .setup()
        )
        p_op = p.can_be_operand.get()

        # First constraint: A ss! {"a", "b"}
        lit1 = (
            F.Literals.Strings.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_transient)
            .setup_from_values("a", "b")
        )
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            p_op,
            lit1.can_be_operand.get(),
            assert_=True,
        )

        # Second constraint: A ss! {"c", "d"} - intersection is empty
        lit2 = (
            F.Literals.Strings.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_transient)
            .setup_from_values("c", "d")
        )

        with pytest.raises(Contradiction):
            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                p_op,
                lit2.can_be_operand.get(),
                assert_=True,
            )


class _SubsumptionResult(Enum):
    """Result types for subsumption detection."""

    NONE = auto()  # No subsumption
    FULL = auto()  # Full subsumption - returns existing expression
    MERGE = auto()  # Merge - returns ExpressionBuilder with intersection


class TestSubsumptionDetection:
    """
    Test subsumption detection for predicates.

    Subsumption means: if predicate A is true, predicate B is automatically true.
    A "subsumes" B, making B redundant.

    Result types:
    - FULL: Existing predicate fully subsumes new (new adds no information)
    - MERGE: Constraints overlap, returns intersection as ExpressionBuilder
    - NONE: No subsumption (disjoint or new is strictly tighter)

    Same-type subsumptions:
    - IsSubset: X ⊆ [0,10] fully subsumes X ⊆ [0,20] (tighter range)
    - IsSubset: X ⊆ [0,20] merges with X ⊆ [0,10] -> X ⊆ [0,10]
    """

    @staticmethod
    def _run_in_mutator(
        mut_map_or_E: MutationMap | BoundExpressions, callback, force_copy=True
    ):
        """Run callback within a mutator context, returning its result."""
        from faebryk.core.solver.algorithm import algorithm
        from faebryk.core.solver.mutator import Mutator

        if isinstance(mut_map_or_E, BoundExpressions):
            mut_map = MutationMap.bootstrap(tg=mut_map_or_E.tg, g=mut_map_or_E.g)
        else:
            mut_map = mut_map_or_E

        result = None

        @algorithm("test", force_copy=force_copy)
        def test_algo(mutator: Mutator):
            nonlocal result
            result = callback(mutator)

        Mutator(mutation_map=mut_map, algo=test_algo, iteration=1, terminal=True).run()
        return result

    @staticmethod
    def _make_pred(E, pred_spec, operand, assert_=True):
        pred_type, value = pred_spec
        match pred_type:
            case "IsSubset":
                return E.is_subset(operand, E.lit_op_range(value), assert_=assert_)
            case _:
                raise ValueError(f"Unknown predicate type: {pred_type}")

    @staticmethod
    def _make_operands(E, pred_spec, operand):
        """Create operands list for find_subsuming_expression."""
        pred_type, value = pred_spec
        literal = (
            E.lit_op_range(value) if pred_type == "IsSubset" else E.lit_op_single(value)
        )
        return [operand, literal]

    @pytest.mark.parametrize(
        "existing_pred, new_pred, expected_result",
        [
            # FULL subsumption: existing is tighter than new
            pytest.param(
                ("IsSubset", (0, 10)),
                ("IsSubset", (0, 20)),
                _SubsumptionResult.FULL,
                id="ss_full_tighter_range",
            ),
            # MERGE: existing is looser, intersection returns tighter constraint
            pytest.param(
                ("IsSubset", (0, 20)),
                ("IsSubset", (0, 10)),
                _SubsumptionResult.MERGE,
                id="ss_merge_looser_range",
            ),
            # FULL subsumption: existing is inner range of new
            pytest.param(
                ("IsSubset", (5, 15)),
                ("IsSubset", (0, 20)),
                _SubsumptionResult.FULL,
                id="ss_full_inner_range",
            ),
            # MERGE: partial overlap, intersection is [5, 10]
            pytest.param(
                ("IsSubset", (0, 10)),
                ("IsSubset", (5, 15)),
                _SubsumptionResult.MERGE,
                id="ss_merge_partial_overlap",
            ),
        ],
    )
    def test_subsumption_detection(self, existing_pred, new_pred, expected_result):
        E = BoundExpressions()
        X = E.parameter_op()
        existing_expr = self._make_pred(E, existing_pred, X, assert_=True)
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)
        new_type, _ = new_pred

        def callback(m: Mutator):
            X_canon = not_none(
                mut_map.map_forward(X.as_parameter_operatable.force_get()).maps_to
            )
            existing_canon = not_none(
                mut_map.map_forward(
                    existing_expr.as_parameter_operatable.force_get()
                ).maps_to
            )
            m.mutate_expression(existing_canon.as_expression.force_get())

            builder = ExpressionBuilder(
                F.Expressions.IsSubset,
                [
                    not_none(m.get_copy(op))
                    for op in self._make_operands(E, new_pred, X_canon.as_operand.get())
                ],
                assert_=True,
                terminate=False,
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback)

        assert result is not None
        match expected_result:
            case _SubsumptionResult.NONE:
                assert result.most_constrained_expr is None
            case _SubsumptionResult.FULL:
                assert isinstance(
                    result.most_constrained_expr, F.Expressions.is_expression
                )
            case _SubsumptionResult.MERGE:
                assert isinstance(result.most_constrained_expr, ExpressionBuilder)

    @pytest.mark.parametrize(
        "existing_pred, new_pred, same_param, assert_existing",
        [
            # Different parameter - should never match
            pytest.param(
                ("IsSubset", (0, 10)),
                ("IsSubset", (0, 20)),
                False,
                True,
                id="different_param_ss",
            ),
            # Non-predicate (not asserted) - should not be found
            pytest.param(
                ("IsSubset", (0, 10)),
                ("IsSubset", (0, 20)),
                True,
                False,
                id="non_predicate_ss",
            ),
            # Note: Disjoint ranges (e.g., [0,10] and [20,30]) are not tested here
            # because they would trigger Contradiction when intersected (empty set).
            # That behavior is tested by the empty superset invariant tests.
        ],
    )
    def test_false_positives(
        self, existing_pred, new_pred, same_param, assert_existing
    ):
        E = BoundExpressions()
        X = E.parameter_op()
        Y = E.parameter_op() if not same_param else X

        existing_expr = self._make_pred(E, existing_pred, X, assert_=assert_existing)
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)
        new_type, _ = new_pred

        def callback(m: Mutator):
            Y_canon = not_none(
                mut_map.map_forward(Y.as_parameter_operatable.force_get()).maps_to
            )
            if assert_existing:
                existing_canon = not_none(
                    mut_map.map_forward(
                        existing_expr.as_parameter_operatable.force_get()
                    ).maps_to
                )
                m.mutate_expression(existing_canon.as_expression.force_get())

            builder = ExpressionBuilder(
                F.Expressions.IsSubset,
                [
                    not_none(m.get_copy(op))
                    for op in self._make_operands(E, new_pred, Y_canon.as_operand.get())
                ],
                assert_=True,
                terminate=False,
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback)
        assert result is not None
        assert result.most_constrained_expr is None, (
            f"Should NOT detect subsumption, but found: {result}"
        )

    def test_terminated_predicate_still_found(self):
        """
        Terminated predicates SHOULD still be found as subsuming.
        Termination means the solver is done processing the predicate,
        but it still constrains the solution space.
        """
        from faebryk.core.solver.mutator import is_terminated

        E = BoundExpressions()
        X = E.parameter_op()
        existing = E.is_subset(X, E.lit_op_range((0, 10)), assert_=True)
        fabll.Traits.create_and_add_instance_to(
            node=fabll.Traits(existing).get_obj_raw(),
            trait=is_terminated,
        )
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            X_canon = not_none(
                mut_map.map_forward(X.as_parameter_operatable.force_get()).maps_to
            )
            existing_canon = not_none(
                mut_map.map_forward(
                    existing.as_parameter_operatable.force_get()
                ).maps_to
            )
            m.mutate_expression(existing_canon.as_expression.force_get())

            builder = ExpressionBuilder(
                F.Expressions.IsSubset,
                [
                    not_none(m.get_copy(X_canon.as_operand.get())),
                    not_none(m.get_copy(E.lit_op_range((0, 20)))),
                ],
                assert_=True,
                terminate=False,
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback)
        assert result is not None
        assert result.most_constrained_expr is not None

    def test_finds_predicate_created_during_algo(self):
        """Test subsumption finds predicates created during the algorithm."""
        E = BoundExpressions()
        X = E.parameter_op()
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            X_canon = not_none(
                mut_map.map_forward(X.as_parameter_operatable.force_get()).maps_to
            )
            # Create a predicate during the algorithm
            m.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                X_canon.as_operand.get(),
                not_none(m.get_copy(E.lit_op_range((0, 10)))),
                assert_=True,
            )
            # Now try to find subsumption for a looser range
            builder = ExpressionBuilder(
                F.Expressions.IsSubset,
                [
                    not_none(m.get_copy(X_canon.as_operand.get())),
                    not_none(m.get_copy(E.lit_op_range((0, 20)))),
                ],
                assert_=True,
                terminate=False,
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback, force_copy=False)
        assert result is not None
        assert result.most_constrained_expr is not None

    def test_or_subsumption_subset_operands(self):
        """Or(A, B) subsumes Or(A, B, C) - smaller Or is tighter."""
        E = BoundExpressions()
        X = E.parameter_op()

        # Create predicates A, B, C (as can_be_operand)
        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)
        pred_c = E.is_subset(X, E.lit_op_range((40, 50)), assert_=False)

        # Create Or(A, B) as existing predicate
        existing_or = F.Expressions.Or.from_operands(
            pred_a, pred_b, g=E.g, tg=E.tg, assert_=True
        )
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            existing_canon = not_none(
                mut_map.map_forward(
                    existing_or.get_trait(F.Parameters.is_parameter_operatable)
                ).maps_to
            )
            m.mutate_expression(existing_canon.as_expression.force_get())

            # Build new Or(A, B, C)
            new_operands = [not_none(m.get_copy(op)) for op in [pred_a, pred_b, pred_c]]
            builder = ExpressionBuilder(
                F.Expressions.Or, new_operands, assert_=True, terminate=False
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback)
        assert result is not None

    def test_or_subsumption_same_operands(self):
        """Or(A, B) subsumes Or(A, B) - same operands."""
        E = BoundExpressions()
        X = E.parameter_op()

        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)

        existing_or = F.Expressions.Or.from_operands(
            pred_a, pred_b, g=E.g, tg=E.tg, assert_=True
        )
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            existing_canon = not_none(
                mut_map.map_forward(
                    existing_or.get_trait(F.Parameters.is_parameter_operatable)
                ).maps_to
            )
            m.mutate_expression(existing_canon.as_expression.force_get())

            new_operands = [not_none(m.get_copy(op)) for op in [pred_a, pred_b]]
            builder = ExpressionBuilder(
                F.Expressions.Or, new_operands, assert_=True, terminate=False
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback)
        assert result is not None

    def test_or_subsumption_negative_superset(self):
        """Or(A, B, C) does NOT subsume Or(A, B) - larger Or is looser."""
        E = BoundExpressions()
        X = E.parameter_op()

        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)
        pred_c = E.is_subset(X, E.lit_op_range((40, 50)), assert_=False)

        # Create Or(A, B, C) as existing predicate
        existing_or = F.Expressions.Or.from_operands(
            pred_a, pred_b, pred_c, g=E.g, tg=E.tg, assert_=True
        )
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            existing_canon = not_none(
                mut_map.map_forward(
                    existing_or.get_trait(F.Parameters.is_parameter_operatable)
                ).maps_to
            )
            m.mutate_expression(existing_canon.as_expression.force_get())

            # Try to find subsumption for Or(A, B)
            new_operands = [not_none(m.get_copy(op)) for op in [pred_a, pred_b]]
            builder = ExpressionBuilder(
                F.Expressions.Or, new_operands, assert_=True, terminate=False
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback)
        assert result is not None
        assert result.most_constrained_expr is None

    def test_or_subsumption_negative_different_operands(self):
        """Or(A, B) does NOT subsume Or(A, C) - different operands."""
        E = BoundExpressions()
        X = E.parameter_op()

        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)
        pred_c = E.is_subset(X, E.lit_op_range((40, 50)), assert_=False)

        existing_or = F.Expressions.Or.from_operands(
            pred_a, pred_b, g=E.g, tg=E.tg, assert_=True
        )
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            existing_canon = not_none(
                mut_map.map_forward(
                    existing_or.get_trait(F.Parameters.is_parameter_operatable)
                ).maps_to
            )
            m.mutate_expression(existing_canon.as_expression.force_get())

            new_operands = [not_none(m.get_copy(op)) for op in [pred_a, pred_c]]
            builder = ExpressionBuilder(
                F.Expressions.Or, new_operands, assert_=True, terminate=False
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback)
        assert result is not None
        assert result.most_constrained_expr is None

    def test_subsumption_check_e2e(self):
        """
        End-to-end test: verify Or subsumption when expression is created
        during algorithm execution.

        Creates Or!(A, B, C) in input, then during algorithm creates Or!(A, B).
        The tighter constraint Or!(A, B) should mark Or!(A, B, C) irrelevant.
        """
        from faebryk.core.solver.mutator import is_irrelevant

        E = BoundExpressions()

        A = E.bool_parameter_op()
        B = E.bool_parameter_op()
        C = E.bool_parameter_op()

        # Create Or!(A, B, C) - looser constraint in input
        or_abc = E.or_(A, B, C, assert_=True)

        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            A_canon = not_none(
                mut_map.map_forward(A.as_parameter_operatable.force_get()).maps_to
            )
            B_canon = not_none(
                mut_map.map_forward(B.as_parameter_operatable.force_get()).maps_to
            )
            or_abc_canon = not_none(
                mut_map.map_forward(or_abc.as_parameter_operatable.force_get()).maps_to
            )

            m.mutate_expression(or_abc_canon.as_expression.force_get())

            A_out = m.get_mutated(A_canon)
            B_out = m.get_mutated(B_canon)

            m.create_check_and_insert_expression(
                F.Expressions.Or,
                A_out.as_operand.get(),
                B_out.as_operand.get(),
                assert_=True,
            )

            or_abc_copy = m.get_mutated(or_abc_canon)
            return or_abc_copy.try_get_sibling_trait(is_irrelevant) is not None

        result = self._run_in_mutator(mut_map, callback)
        assert result is True

    def test_or_with_true_literal_discard(self):
        """
        Or!(A, B, True) should return DISCARD.

        "A or B or True" is always true, so it provides no constraint.
        """
        E = BoundExpressions()
        A = E.bool_parameter_op()
        B = E.bool_parameter_op()
        true_lit = E.lit_bool(True)

        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            A_canon = not_none(
                mut_map.map_forward(A.as_parameter_operatable.force_get()).maps_to
            )
            B_canon = not_none(
                mut_map.map_forward(B.as_parameter_operatable.force_get()).maps_to
            )

            builder = ExpressionBuilder(
                F.Expressions.Or,
                [
                    not_none(m.get_copy(A_canon.as_operand.get())),
                    not_none(m.get_copy(B_canon.as_operand.get())),
                    not_none(m.get_copy(true_lit)),
                ],
                assert_=True,
                terminate=False,
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback)
        assert result is not None
        assert isinstance(
            result.most_constrained_expr, SubsumptionCheck.Result._DISCARD
        )

    def test_or_with_false_literal_filtered(self):
        """
        Or!(A, B, C, False) should filter out False and behave like Or!(A, B, C).

        When existing Or!(A, B) exists and we create Or!(A, B, C, False),
        the False is filtered out, leaving Or!(A, B, C) which is looser.
        The existing Or!(A, B) should subsume the new one.
        """
        E = BoundExpressions()
        X = E.parameter_op()

        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)
        pred_c = E.is_subset(X, E.lit_op_range((40, 50)), assert_=False)
        false_lit = E.lit_bool(False)

        # Create existing Or!(A, B) - tighter
        existing_or = F.Expressions.Or.from_operands(
            pred_a, pred_b, g=E.g, tg=E.tg, assert_=True
        )
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            existing_canon = not_none(
                mut_map.map_forward(
                    existing_or.get_trait(F.Parameters.is_parameter_operatable)
                ).maps_to
            )
            pred_a_canon = not_none(
                mut_map.map_forward(pred_a.as_parameter_operatable.force_get()).maps_to
            )
            pred_b_canon = not_none(
                mut_map.map_forward(pred_b.as_parameter_operatable.force_get()).maps_to
            )
            pred_c_canon = not_none(
                mut_map.map_forward(pred_c.as_parameter_operatable.force_get()).maps_to
            )

            m.mutate_expression(existing_canon.as_expression.force_get())
            m.mutate_expression(pred_c_canon.as_expression.force_get())

            pred_a_out = m.get_mutated(pred_a_canon)
            pred_b_out = m.get_mutated(pred_b_canon)
            pred_c_out = m.get_mutated(pred_c_canon)

            builder = ExpressionBuilder(
                F.Expressions.Or,
                [
                    pred_a_out.as_operand.get(),
                    pred_b_out.as_operand.get(),
                    pred_c_out.as_operand.get(),
                    not_none(m.get_copy(false_lit)),
                ],
                assert_=True,
                terminate=False,
            )
            return find_subsuming_expression(m, builder)

        result = self._run_in_mutator(mut_map, callback)
        assert result is not None
        assert result.most_constrained_expr is not None

    def test_or_could_subsume_returns_existing(self):
        """
        Test the could_subsume path: existing tighter Or subsumes new looser Or.

        When Or!(A, B) exists and we try to create Or!(A, B, C),
        the existing Or!(A, B) should be returned (it's tighter).

        This is distinct from could_be_subsumed which marks things irrelevant.
        """
        E = BoundExpressions()
        X = E.parameter_op()

        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)
        pred_c = E.is_subset(X, E.lit_op_range((40, 50)), assert_=False)

        # Create existing Or!(A, B) - tighter
        existing_or = F.Expressions.Or.from_operands(
            pred_a, pred_b, g=E.g, tg=E.tg, assert_=True
        )
        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)

        def callback(m: Mutator):
            existing_canon = not_none(
                mut_map.map_forward(
                    existing_or.get_trait(F.Parameters.is_parameter_operatable)
                ).maps_to
            )
            pred_a_canon = not_none(
                mut_map.map_forward(pred_a.as_parameter_operatable.force_get()).maps_to
            )
            pred_b_canon = not_none(
                mut_map.map_forward(pred_b.as_parameter_operatable.force_get()).maps_to
            )
            pred_c_canon = not_none(
                mut_map.map_forward(pred_c.as_parameter_operatable.force_get()).maps_to
            )

            m.mutate_expression(existing_canon.as_expression.force_get())
            pred_a_out = m.get_mutated(pred_a_canon)
            pred_b_out = m.get_mutated(pred_b_canon)

            m.mutate_expression(pred_c_canon.as_expression.force_get())
            pred_c_out = m.get_mutated(pred_c_canon)

            # Try to create Or!(A, B, C) - looser
            builder = ExpressionBuilder(
                F.Expressions.Or,
                [
                    pred_a_out.as_operand.get(),
                    pred_b_out.as_operand.get(),
                    pred_c_out.as_operand.get(),
                ],
                assert_=True,
                terminate=False,
            )
            result = find_subsuming_expression(m, builder)

            assert result.most_constrained_expr is not None
            assert isinstance(result.most_constrained_expr, F.Expressions.is_expression)
            return result

        result = self._run_in_mutator(mut_map, callback)
        assert result is not None
