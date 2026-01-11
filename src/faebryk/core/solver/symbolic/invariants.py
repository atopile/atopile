# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from functools import reduce
from typing import NamedTuple, Sequence

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import SolverAlgorithm
from faebryk.core.solver.mutator import MutationMap, Mutator
from faebryk.core.solver.utils import (
    S_LOG,
    Contradiction,
)
from faebryk.libs.util import not_none

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
        builder: tuple[type[fabll.NodeT], list[F.Parameters.can_be_operand]] | None = (
            None
        )
        discard: bool = False

    @staticmethod
    def subset(
        mutator: Mutator,
        new_operands: Sequence[F.Parameters.can_be_operand],
        is_predicate: bool,
    ) -> Result:
        """
        A ss! X, A ss! Y -> A ss! X ∩ Y
        X ss! A, Y ss! A -> X ∪ Y ss! A
        """

        if not is_predicate:
            # TODO properly implement
            return SubsumptionCheck.Result()

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
                builder=(
                    IsSubset,
                    [subset_op.as_operand.get(), merged_superset.as_operand.get()],
                )
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
                builder=(
                    IsSubset,
                    [merged_subset.as_operand.get(), superset_op.as_operand.get()],
                )
            )

        assert False, "Unreachable"

    @staticmethod
    def or_(
        mutator: Mutator,
        new_operands: Sequence[F.Parameters.can_be_operand],
        is_predicate: bool,
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
            if is_predicate:
                return SubsumptionCheck.Result(discard=True)
            else:
                # other algorithm will deal with this (no invariant)
                return SubsumptionCheck.Result()

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

        if is_predicate:
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
    match expr_factory:
        case F.Expressions.IsSubset:
            return SubsumptionCheck.subset(mutator, operands, is_predicate)
        case F.Expressions.Or:
            return SubsumptionCheck.or_(mutator, operands, is_predicate)
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
    # TODO: i dont think we should return cbo, even in fold case we return expr
    out_operand: F.Parameters.can_be_operand | None
    """
    None if expression dropped. Can only happen for predicates
    """
    is_new: bool


class ExpressionBuilder(NamedTuple):
    factory: type[fabll.NodeT]
    operands: list[F.Parameters.can_be_operand]
    assert_: bool
    terminate: bool

    def __str__(self):
        _str = _pretty_factory(
            self.factory,
            self.operands,
            assert_=self.assert_,
            terminate=self.terminate,
        )
        return _str


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


def _no_predicate_literals(
    mutator: Mutator,
    builder: ExpressionBuilder,
) -> ExpressionBuilder | None:
    """
    P!{S/P|False} -> Contradiction
    P {S|True} -> P!
    P!{P|True} -> P!
    """

    # FIXME: important
    #  if we assert an expression then we need to uphold the invariant
    #   that it's not used as operand

    factory, operands, assert_, _ = builder
    if not (factory is F.Expressions.IsSubset and assert_):
        return builder

    if not (
        lits := {
            i: lit for i, o in enumerate(operands) if (lit := o.as_literal.try_get())
        }
    ):
        return builder

    # P!{S|False} -> Contradiction
    if operands[0].try_get_sibling_trait(F.Expressions.is_predicate) and any(
        lit.equals_singleton(False) for lit in lits.values()
    ):
        raise Contradiction(
            "P!{S/P|False}",
            involved=[],
            mutator=mutator,
        )

    if any(lit.equals_singleton(True) for lit in lits.values()):
        # P!{S/P|True} -> P!
        if any(op.try_get_sibling_trait(F.Expressions.is_predicate) for op in operands):
            logger.debug(
                f"Remove predicate literal {_pretty_factory(factory, operands)}"
            )
            return None
        # P {S|True} -> P!
        if pred := operands[0].try_get_sibling_trait(F.Expressions.is_assertable):
            logger.debug(f"Assert implicit predicate {pred}")
            mutator.assert_(pred)
            return None

    return builder


def _no_literal_inequalities(
    mutator: Mutator,
    builder: ExpressionBuilder,
) -> ExpressionBuilder:
    """
    Convert GreaterOrEqual expressions with literals to IsSubset constraints:
    - A >= X (X is literal) -> A ss [X.max(), +∞)
    - X >= A (X is literal) -> A ss (-∞, X.min()]

    This transformation is semantically equivalent:
    - "A is at least X" becomes "A is a subset of [X, infinity)"
    - "A is at most X" becomes "A is a subset of (-infinity, X]"
    """
    import math

    factory, operands, assert_, terminate = builder

    if factory is not F.Expressions.GreaterOrEqual:
        return builder

    lits = {i: lit for i, o in enumerate(operands) if (lit := o.as_literal.try_get())}

    if not lits:
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
    logger.debug(
        f"Converting {_pretty_factory(factory, operands)} ->"
        f" {_pretty_factory(IsSubset, new_operands)}"
    )
    return ExpressionBuilder(
        IsSubset,
        new_operands,
        assert_,
        terminate,
    )


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

    if new_operands != operands:
        logger.debug(
            f"Predicate operands: {_pretty_factory(builder.factory, operands)}) ->"
            f" {_pretty_factory(builder.factory, new_operands)})"
        )
    operands = new_operands

    return ExpressionBuilder(
        builder.factory, operands, builder.assert_, builder.terminate
    )


def _pretty_factory(
    factory: type[fabll.Node] | None = None,
    operands: Sequence[F.Parameters.can_be_operand] | None = None,
    assert_: bool = False,
    terminate: bool = False,
) -> str:
    # TODO: merge this with compact repr
    if operands is not None:
        ops = ", ".join(op.pretty() for op in operands)
    else:
        ops = ""
    if factory:
        fac = f"{factory.__name__}"
        if assert_:
            fac += "!"
        if terminate:
            fac += "$"
        if operands is not None:
            return f"{fac}({ops})"
        else:
            return fac
    else:
        return ops


def insert_expression(
    mutator: Mutator,
    builder: ExpressionBuilder,
) -> InsertExpressionResult:
    """
    Invariants
    Sequencing sensitive!
    * ✓ don't use predicates as operands: Op(P!, ...) -> Op(True, ...)
    * ✓ fold pure literal expressions: E(X, Y) -> E{S/P|...}(X, Y)
    * ✓ P{S|True} -> P!, P!{S/P|False} -> Contradiction, P!{S|True} -> P!
    * ✓ no A >! X or X >! A (create A ss! X or X ss! A)
    * ✓ no congruence (function is kinda shit, TODO)
    * ✓ minimal subsumption
    * ✓ - intersected supersets (single superset)
    * ✓ no empty supersets
    * ✓ canonical
    """

    from faebryk.core.solver.symbolic.pure_literal import exec_pure_literal_operands

    assert not builder.terminate or builder.assert_, "terminate ⟹ assert"

    # * Op(P!, ...) -> Op(True, ...)
    builder = _no_predicate_operands(mutator, builder)

    # * fold pure literal expressions
    # folding to literal will result in ss/sup in mutator.mutate_expression
    if lit_fold := exec_pure_literal_operands(
        mutator.G_transient, mutator.tg_in, builder.factory, builder.operands
    ):
        logger.debug(f"Folded ({builder}) to literal {lit_fold.pretty_str()}")
        # TODO terminate expression
        new_expr = mutator._create_and_insert_expression(
            builder.factory,
            *builder.operands,
            assert_=builder.assert_,
            terminate=builder.terminate,
        )
        new_expr_op = new_expr.get_trait(F.Parameters.can_be_operand)
        lit_op = lit_fold.as_operand.get()
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            new_expr_op,
            lit_op,
            terminate=True,
            assert_=True,
        )
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            lit_op,
            new_expr_op,
            terminate=True,
            assert_=True,
        )
        return InsertExpressionResult(new_expr_op, True)

    # P!{S/P|False} -> Contradiction
    # P {S|True} -> P!
    # P!{P|True} -> P!
    builder_ = _no_predicate_literals(mutator, builder)
    if builder_ is None:
        return InsertExpressionResult(None, False)
    builder = builder_

    # * no A >! X or X >! A (create A ss! X or X ss! A)
    builder = _no_literal_inequalities(mutator, builder)

    # * no congruence
    if congruent := find_congruent_expression(
        mutator,
        builder.factory,
        *builder.operands,
    ):
        if builder.assert_:
            congruent_assertable = congruent.get_trait(F.Expressions.is_assertable)
            mutator.assert_(congruent_assertable)
        if builder.terminate:
            congruent_predicate = congruent.get_trait(F.Expressions.is_predicate)
            mutator.predicate_terminate(congruent_predicate)
        congruent_op = congruent.get_trait(F.Parameters.can_be_operand)
        logger.debug(
            f"Found congruent expressionf for {builder}: {congruent_op.pretty()}"
        )
        return InsertExpressionResult(congruent_op, False)

    # * minimal subsumption
    # Check for semantic subsumption (only for predicates)
    if builder.assert_ or builder.factory.bind_typegraph(
        mutator.tg_in
    ).check_if_instance_of_type_has_trait(F.Expressions.is_assertable):
        subsume_res = find_subsuming_expression(
            mutator, builder.factory, builder.operands, is_predicate=builder.assert_
        )
        if subsuming_expr := subsume_res.expr:
            logger.debug(f"Subsume replaced: {subsuming_expr.pretty_repr()}")
            return InsertExpressionResult(subsuming_expr.as_operand.get(), False)
        elif subsume_res.discard:
            logger.debug(f"Subsume discard: {builder}")
            return InsertExpressionResult(None, False)
        elif subsume_res.builder:
            factory, operands = subsume_res.builder
            builder = ExpressionBuilder(
                factory, operands, builder.assert_, builder.terminate
            )
            logger.debug(f"Subsume adjust {builder}")

    # * no empty supersets
    _no_empty_superset(mutator, builder)

    # * canonical (covered by create)
    expr = mutator._create_and_insert_expression(
        builder.factory,
        *builder.operands,
        assert_=builder.assert_,
    )
    return InsertExpressionResult(expr.get_trait(F.Parameters.can_be_operand), True)


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
        ).get_operands()[0].get_sibling_trait(F.Literals.is_literal).equals_singleton(
            True
        )

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
            .equals(
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
            new_operands=[p_op, lit2.can_be_operand.get()],
            is_predicate=True,
        )

        # Subsumption should return a builder with intersected range
        assert subsume_result.builder is not None
        _, new_operands = subsume_result.builder
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
        assert first_lit is not None and first_lit.equals_singleton(True)

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
            assert lit is not None and lit.equals_singleton(True)

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
            new_operands=[p_op, lit2.can_be_operand.get()],
            is_predicate=True,
        )

        # Should return builder with intersected range [50, 60]
        assert subsume_result.builder is not None
        _, new_operands = subsume_result.builder
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
