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
    * ✓ no pure literal expressions
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

    # * no pure literal expressions
    # folding to literal will result in ss/sup in mutator.mutate_expression
    if lit_fold := exec_pure_literal_operands(
        mutator.G_transient, mutator.tg_in, builder.factory, builder.operands
    ):
        logger.debug(f"Folded ({builder}) to literal {lit_fold.pretty_str()}")
        return InsertExpressionResult(lit_fold.as_operand.get(), True)

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
        logger.debug(f"Found congruent expression {congruent_op.pretty_repr()}")
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


class TestInvariants:
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
        mutator = TestInvariants._setup_mutator()

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
