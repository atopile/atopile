# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from functools import reduce
from typing import NamedTuple, Sequence

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    S_LOG,
    Contradiction,
    ContradictionByLiteral,
)

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

        expr: F.Expressions.is_expression | None = None
        builder: (
            tuple[type[fabll.NodeT], Sequence[F.Parameters.can_be_operand]] | None
        ) = None
        discard: bool = False

    @staticmethod
    def subset(
        mutator: Mutator,
        new_operands: Sequence[F.Parameters.can_be_operand],
    ) -> Result:
        """
        A ss! X, A ss! Y -> A ss! X ∩ Y
        X ss! A, Y ss! A -> X ∪ Y ss! A
        """

        ops = {
            i: op
            for i, v in enumerate(new_operands)
            if (op := v.as_parameter_operatable.try_get())
        }

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

            assert len(superset_ss) == 1
            superset_ss, superset_lit = superset_ss[0]
            new_superset = new_operands[1].as_literal.force_get()
            merged_superset = superset_lit.op_intersect_intervals(
                new_superset, g=mutator.G_transient, tg=mutator.tg_in
            )
            if superset_lit.equals(merged_superset):
                return SubsumptionCheck.Result(expr=superset_ss.is_expression.get())
            mutator.mark_irrelevant(superset_ss.is_parameter_operatable.get())
            return SubsumptionCheck.Result(
                builder=(IsSubset, [subset_op, merged_superset])
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

            assert len(subset_ss) == 1
            subset_ss, subset_lit = subset_ss[0]
            new_subset = new_operands[0].as_literal.force_get()
            merged_subset = subset_lit.op_union_intervals(
                new_subset, g=mutator.G_transient, tg=mutator.tg_in
            )
            if subset_lit.equals(merged_subset):
                return SubsumptionCheck.Result(expr=subset_ss.is_expression.get())
            mutator.mark_irrelevant(subset_ss.is_parameter_operatable.get())
            return SubsumptionCheck.Result(
                builder=(IsSubset, [superset_op, merged_subset])
            )

        assert False, "Unreachable"

    @staticmethod
    def or_(
        mutator: Mutator,
        new_operands: Sequence[F.Parameters.can_be_operand],
    ) -> Result:
        """
        Or!(A, B, C), Or!(A, B) -> Or!(A, B)
        Or!(A, B, False/{True, False}) -> Or!(A, B)
        Or!(A, B, True) -> discard (no information)
        """

        if any(
            lit.equals_singleton(True)
            for op in new_operands
            if (lit := op.as_literal.try_get())
        ):
            return SubsumptionCheck.Result(discard=True)

        # filter out False/{True, False}
        new_operands = [
            op for op in new_operands if not (lit := op.as_literal.try_get())
        ]

        def _operands_are_subset(
            candidate_operands: Sequence[F.Parameters.can_be_operand],
            new_operands: Sequence[F.Parameters.can_be_operand],
        ) -> bool:
            """
            Check if candidate operands are a subset of new operands (by identity).
            Used for Or subsumption: Or(A, B) subsumes Or(A, B, C).
            """
            if len(candidate_operands) > len(new_operands):
                return False

            def _get_uuid(op: F.Parameters.can_be_operand) -> int | None:
                if (po := op.as_parameter_operatable.try_get()) is not None:
                    return po.instance.node().get_uuid()
                if (lit := op.as_literal.try_get()) is not None:
                    return lit.instance.node().get_uuid()
                return None

            new_uuids = {_get_uuid(op) for op in new_operands}
            return all(_get_uuid(op) in new_uuids for op in candidate_operands)

        ors = [
            mutator.get_operations(
                op.as_parameter_operatable.force_get(),
                types=F.Expressions.Or,
                predicates_only=True,
            )
            for op in new_operands
        ]
        could_be_subsumed = reduce(lambda x, y: x & y, ors)

        for candidate in could_be_subsumed:
            if _operands_are_subset(
                candidate.get_trait(F.Expressions.is_expression).get_operands(),
                new_operands,
            ):
                mutator.mark_irrelevant(candidate.is_parameter_operatable.get())

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
                return SubsumptionCheck.Result(expr=candidate_expr)

        return SubsumptionCheck.Result()


def find_subsuming_expression(
    mutator: Mutator,
    expr_factory: type[fabll.NodeT],
    operands: Sequence[F.Parameters.can_be_operand],
    is_predicate: bool,
) -> SubsumptionCheck.Result:
    # TODO pass through is_predicate
    # need to handle non predicates being subsumed by predicates

    match expr_factory:
        case F.Expressions.IsSubset:
            return SubsumptionCheck.subset(mutator, operands)
        case F.Expressions.Or:
            return SubsumptionCheck.or_(mutator, operands)
        case _:
            return SubsumptionCheck.Result()


def find_congruent_expression[T: fabll.NodeT](
    mutator: Mutator,
    expr_factory: type[T],
    *operands: F.Parameters.can_be_operand,
    allow_uncorrelated: bool = False,
    dont_match: list[F.Expressions.is_expression] | None = None,
) -> T | None:
    """
    Careful: Disregards whether asserted in root expression!
    """
    # TODO look in old & new graph

    non_lits = [
        op_po for op in operands if (op_po := op.as_parameter_operatable.try_get())
    ]
    literal_expr = all(
        mutator.utils.is_literal(op) or mutator.utils.is_literal_expression(op)
        for op in operands
    )
    dont_match_set = set(dont_match or [])
    if literal_expr:
        lit_ops = {
            op
            for op in mutator.get_typed_expressions(
                expr_factory, created_only=False, include_terminated=True
            )
            if op.get_trait(F.Expressions.is_expression) not in dont_match_set
            and mutator.utils.is_literal_expression(
                op.get_trait(F.Parameters.can_be_operand)
            )
            # check congruence
            and F.Expressions.is_expression.are_pos_congruent(
                op.get_trait(F.Expressions.is_expression).get_operands(),
                operands,
                g=mutator.G_transient,
                tg=mutator.tg_in,
                allow_uncorrelated=allow_uncorrelated,
            )
        }
        if lit_ops:
            return next(iter(lit_ops))
        return None

    # TODO: might have to check in repr_map
    candidates = [
        expr_t
        for expr in non_lits[0].get_operations()
        if (expr_t := expr.try_cast(expr_factory))
        and expr_t.get_trait(F.Expressions.is_expression) not in dont_match_set
    ]

    for c in candidates:
        if c.get_trait(F.Expressions.is_expression).is_congruent_to_factory(
            expr_factory,
            operands,
            g=mutator.G_transient,
            tg=mutator.tg_in,
            allow_uncorrelated=allow_uncorrelated,
        ):
            return c
    return None


class InsertExpressionResult(NamedTuple):
    out_operand: F.Parameters.can_be_operand
    is_new: bool


class ExpressionBuilder(NamedTuple):
    factory: type[fabll.NodeT]
    operands: list[F.Parameters.can_be_operand]
    assert_: bool
    terminate: bool


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
        and lit.is_empty()
        and (po := operands[0].as_parameter_operatable.try_get())
    ):
        raise Contradiction(
            "Empty superset for parameter operatable",
            [po],
            mutator,
        )


def insert_expression(
    mutator: Mutator,
    builder: ExpressionBuilder,
) -> InsertExpressionResult:
    """
    Invariants
    Sequencing sensitive!
    * no pure literal expressions
    * P!{S|True} -> P!$, P!{S|False} -> Contradiction
    * no A >! X or X >! A (create A ss! X or X ss! A)
    * ✓ no congruence (function is kinda shit, TODO)
    * minimal subsumption
    * - intersected supersets (single superset)
    * no (A ss! True) ss! True
    * ✓ no empty supersets
    * ✓ canonical
    """

    from faebryk.core.solver.symbolic.pure_literal import exec_pure_literal_operands

    factory, operands, assert_, terminate = builder
    assert not terminate or assert_, "terminate ⟹ assert"

    # * no pure literal expressions
    # folding to literal will result in ss/sup in mutator.mutate_expression
    if lit_fold := exec_pure_literal_operands(
        mutator.G_transient, mutator.tg_in, factory, operands
    ):
        return InsertExpressionResult(lit_fold.as_operand.get(), True)

    # * P!{S|True} -> P$, P!{S|False} -> Contradiction
    # TODO

    # * no A >! X or X >! A (create A ss! X or X ss! A)
    # TODO

    # * no congruence
    if congruent := find_congruent_expression(
        mutator,
        factory,
        *operands,
    ):
        if assert_:
            congruent_assertable = congruent.get_trait(F.Expressions.is_assertable)
            mutator.assert_(congruent_assertable)
        if terminate:
            congruent_predicate = congruent.get_trait(F.Expressions.is_predicate)
            mutator.predicate_terminate(congruent_predicate)
        congruent_op = congruent.get_trait(F.Parameters.can_be_operand)
        return InsertExpressionResult(congruent_op, False)

    # * minimal subsumption
    # Check for semantic subsumption (only for predicates)
    if assert_ or factory.bind_typegraph(
        mutator.tg_in
    ).check_if_instance_of_type_has_trait(F.Expressions.is_assertable):
        subsume_res = find_subsuming_expression(
            mutator, factory, operands, is_predicate=assert_
        )
        if subsume_res.expr:
            # TODO
            pass
        elif subsume_res.discard:
            # TODO
            pass
        elif subsume_res.builder:
            factory, operands = subsume_res.builder

    # * no (A ss! True) ss! True
    # TODO

    # * no empty supersets
    _no_empty_superset(mutator, builder)

    # * canonical (covered by create)
    expr = mutator._create_and_insert_expression(
        factory,
        *operands,
        assert_=assert_,
    )
    return InsertExpressionResult(expr.get_trait(F.Parameters.can_be_operand), True)
