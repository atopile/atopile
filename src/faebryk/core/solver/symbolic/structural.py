# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import combinations

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

        # fold pure literal expressions
        # Theoretically this is a shortcut, since invariants should deal with this.
        # But either that's generally not possible without the context or I'm too stupid
        # to implement it. So we rely on this shortcut for now.
        if all(mutator.utils.is_literal(op) for op in mapped_operands):
            out = exec_pure_literal_operands(
                mutator.G_transient,
                mutator.tg_in,
                mutator.utils.hack_get_expr_type(expr_e),
                mapped_operands,
            )
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


@algorithm("Lower estimation", terminal=False)
def lower_estimation_of_expressions_with_subsets(mutator: Mutator):
    """
    If any operand in an expression has a subset literal (lower bound)
    and all parameters are known uncorrelated,
    we can estimate the expression to the function applied to the subset literals.

    ```
    f(A{⊇|X}, B{⊇|Y}, C, ...) ∧ ¬!(A ~ B ~ C)
        => f(A{⊇|X}, B{⊇|Y}, C, Z, ...) ⊇! f(X, Y, C, Z, ...)

    ```
    - f not setic
    - X,Y not singleton (singletons handled by literal alias conversion)

    Note: After canonicalization, IsSuperset(param, literal) becomes IsSubset(literal, param).
    So we look for IsSubset where:
    - subset operand (first) is a literal (the picked/lower bound value)
    - superset operand (second) is a parameter (which is bounded below)
    """
    # Step 1: Build map of operands with subset (lower bound) literals
    # After canonicalization: IsSubset(literal, param) means literal ⊆ param
    # (i.e., param ⊇ literal)
    # This is the INVERSE of upper_estimation which looks for IsSubset(param, literal)
    subsetted_ops: dict[F.Parameters.can_be_operand, F.Literals.is_literal] = {}
    for ss in mutator.get_typed_expressions(
        F.Expressions.IsSubset,
        required_traits=(F.Expressions.is_predicate,),
        include_terminated=True,
    ):
        subset_op, superset_op = ss.get_subset_operand(), ss.get_superset_operand()

        if not (lit_subset := subset_op.as_literal.try_get()):
            continue
        if not (op_superset := superset_op.as_parameter_operatable.try_get()):
            continue
        # singletons get taken care of by
        # `convert_operable_aliased_to_single_into_literal`
        if mutator.utils.is_correlatable_literal(lit_subset):
            continue
        # Skip if the superset is already a literal expression
        # (e.g., the result of a literal computation)
        if mutator.utils.is_literal_expression(superset_op):
            continue

        subsetted_ops[op_superset.as_operand.get()] = lit_subset

    if not subsetted_ops:
        return

    # Step 2: Build anticorrelated pairs set for correlation checking
    anticorrelated_pairs = MutatorUtils.get_anticorrelated_pairs(
        mutator.tg_in, mutator.G_in
    )

    # Step 3: Find expressions involving subsetted operands
    exprs = {
        e
        for op in subsetted_ops.keys()
        for e in mutator.get_operations(op.as_parameter_operatable.force_get())
        # setic expressions can't get subset estimated
        if not e.has_trait(F.Expressions.is_setic)
    }

    for expr in exprs:
        expr_e = expr.get_trait(F.Expressions.is_expression)
        operands = expr_e.get_operands()

        # Check if any operand has a subset literal
        mapped_operands = [
            subsetted_ops[op].as_operand.get() if op in subsetted_ops else op
            for op in operands
        ]
        if mapped_operands == operands:
            continue

        # Step 4: Check uncorrelation condition
        # Find all unique parameters in the expression
        params_in_expr = MutatorUtils.get_params_for_expr(expr_e)
        if len(params_in_expr) > 1:
            # Check if all parameter pairs are uncorrelated
            all_uncorrelated = all(
                frozenset([p1, p2]) in anticorrelated_pairs
                for p1, p2 in combinations(params_in_expr, 2)
            )
            if not all_uncorrelated:
                # Can't apply lower estimation - parameters may be correlated
                continue

        expr_po = expr.get_trait(F.Parameters.is_parameter_operatable)
        from_ops = [expr_po]

        # fold pure literal expressions
        # Theoretically this is a shortcut, since invariants should deal with this.
        # But either that's generally not possible without the context or I'm too stupid
        # to implement it. So we rely on this shortcut for now.
        if all(mutator.utils.is_literal(op) for op in mapped_operands):
            out = exec_pure_literal_operands(
                mutator.G_transient,
                mutator.tg_in,
                mutator.utils.hack_get_expr_type(expr_e),
                mapped_operands,
            )
        else:
            # Step 5: Make new expr with subset literals
            res = mutator.create_check_and_insert_expression(
                mutator.utils.hack_get_expr_type(expr_e),
                *mapped_operands,
                from_ops=from_ops,
                allow_uncorrelated_congruence_match=True,
            )
            out = res.out
        if out is None:
            continue

        expr_subset = out.as_operand.get()

        # Step 6: Superset old expr to subset estimated one
        # new_expr ⊆ original_expr (inverse of upper estimation)
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            expr_subset,
            expr_e.as_operand.get(),
            from_ops=from_ops,
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
