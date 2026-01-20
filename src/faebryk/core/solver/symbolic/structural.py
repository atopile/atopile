# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import combinations

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import MutatorUtils
from faebryk.libs.util import EquivalenceClasses, OrderedSet

logger = logging.getLogger(__name__)

Add = F.Expressions.Add
GreaterOrEqual = F.Expressions.GreaterOrEqual
Is = F.Expressions.Is
IsSubset = F.Expressions.IsSubset
Multiply = F.Expressions.Multiply
Power = F.Expressions.Power

# TODO: mark terminal=False where applicable


@algorithm("Alias classes", terminal=False)
def resolve_alias_classes(mutator: Mutator):
    """
    Resolve alias classes
    Ignores literals
    ```
    A alias B
    B alias C
    C alias D + E
    D + E < 5
    D + E is 3
    D + E + F < 10
    -> A,B,C => R, R alias D + E, R < 5, R is 3, R + F < 10

    # Notes:
    D is 2, E is 5 -> D + E is 7, D + E is R, R is 3
    (D + E) - (D + E) -> R - R
    (D + E) + E -> R + E

    Careful: Aliases to literals will not be resolved due to loss
    of correlation information
    ```
    """
    return

    # A is B, B is C, D is E, F, G is (A+B)
    # -> [{A, B, C}, {D, E}, {F}, {G, (A+B)}]
    param_ops = mutator.get_parameter_operatables()
    full_eq = EquivalenceClasses[F.Parameters.is_parameter_operatable](param_ops)
    is_exprs = mutator.get_typed_expressions(
        F.Expressions.Is,
        include_terminated=True,
        required_traits=(F.Expressions.is_predicate,),
    )
    for is_expr in is_exprs:
        ops: OrderedSet[F.Parameters.is_parameter_operatable] = OrderedSet(
            # Literal expressions are basically literals
            o
            for o in is_expr.is_expression.get().get_operand_operatables()
            if not mutator.utils.is_literal_expression(o.as_operand.get())
        )
        # eq between non-literal operands
        full_eq.add_eq(*ops)
    p_eq_classes = full_eq.get(only_multi=True)

    for eq_class in p_eq_classes:
        eq_class_params = [p_po for p in eq_class if (p_po := p.as_parameter.try_get())]
        eq_class_exprs = {p_e for p in eq_class if (p_e := p.as_expression.try_get())}

        if not eq_class_params:
            continue

        if len(eq_class_params) == 1:
            # check if all in eq_class already aliased
            # Then no need to to create new representative
            _repr = eq_class_params[0]
            _repr_po = _repr.as_parameter_operatable.get()
            iss = _repr_po.get_operations(F.Expressions.Is)
            iss_exprs = {
                o
                for e in iss
                for o in e.is_expression.get().get_operands_with_trait(
                    F.Expressions.is_expression
                )
            }
            if eq_class_exprs.issubset(iss_exprs):
                # check if all predicates are already propagated
                class_expressions = {
                    e
                    for operand in eq_class_exprs
                    for e in operand.as_parameter_operatable.get().get_operations()
                    # skip POps Is, because they create the alias classes
                    # or literal aliases (done by distribute algo)
                    if not (
                        (
                            e_expr := e.get_trait(F.Expressions.is_expression)
                        ).expr_isinstance(F.Expressions.Is)
                        and e.try_get_trait(F.Expressions.is_predicate)
                    )
                    # skip literal subsets (done by distribute algo)
                    and not (
                        e_expr.expr_isinstance(F.Expressions.IsSubset)
                        and e_expr.get_operand_literals()
                        and e.try_get_trait(F.Expressions.is_predicate)
                    )
                }
                if not class_expressions:
                    continue
            # else
            mutator.copy_operand(_repr_po)
            continue

        # Merge param alias classes
        representative = mutator.utils.merge_parameters(eq_class_params)

        for p in eq_class_params:
            p_po = p.as_parameter_operatable.get()
            mutator._mutate(
                p_po,
                representative.as_parameter_operatable.get(),
            )

    for eq_class in p_eq_classes:
        # Use same pattern as first loop: get is_parameter objects
        eq_class_params = [p_po for p in eq_class if (p_po := p.as_parameter.try_get())]
        eq_class_exprs = {p_e for p in eq_class if (p_e := p.as_expression.try_get())}

        if eq_class_params:
            p_0 = eq_class_params[0]
            # Convert to is_parameter_operatable to check mutation status
            # (matches what first loop uses as key in _mutate)
            p_0_po = p_0.as_parameter_operatable.get()
            # See len(alias_class_params) == 1 case above
            if not mutator.has_been_mutated(p_0_po):
                continue
            representative = mutator.get_mutated(p_0_po)
        else:
            # If not params or lits in class, create a new param as representative
            # for expressions

            representative = mutator.register_created_parameter(
                (next(iter(eq_class_exprs)))
                .get_parameter_type()
                .bind_typegraph(mutator.tg_out)
                .create_instance(g=mutator.G_out)
                .setup()
                .is_parameter.get(),
                from_ops=list(eq_class),
            ).as_parameter_operatable.get()

        for e in eq_class_exprs:
            e_po = e.as_parameter_operatable.get()
            # IMPORTANT: Create Is predicate BEFORE soft_replace
            # Otherwise soft_replace makes e_po -> representative, and the Is becomes
            # Is(representative, representative) which is reflexive and gets folded to True
            mutator.create_check_and_insert_expression(
                F.Expressions.Is,
                e.as_operand.get(),
                representative.as_operand.get(),
                from_ops=list(eq_class),
                assert_=True,
                terminate=False,  # Don't terminate so superset can propagate
            )
            # Then soft_replace for other uses of this expression
            mutator.soft_replace(e_po, representative)


@algorithm("Transitive subset", terminal=False)
def transitive_subset(mutator: Mutator):
    """
    ```
    A ss! B, B ss! C -> new A ss! C
    B not lit
    ```
    """

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
        for e in op.get_operations()
        # setic expressions can't get subset estimated
        if not e.has_trait(F.Expressions.is_setic)
    }
    exprs = F.Expressions.is_expression.sort_by_depth(exprs, ascending=True)

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

        # Make new expr with subset literals
        res = mutator.create_check_and_insert_expression(
            mutator.utils.hack_get_expr_type(expr_e),
            *mapped_operands,
            from_ops=from_ops,
            allow_uncorrelated_congruence_match=True,
        )
        if res.out_operand is None:
            continue
        expr_superset = res.out_operand

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
    anticorrelated_pairs = MutatorUtils.get_anticorrelated_pairs(mutator.tg_in)

    # Step 3: Find expressions involving subsetted operands
    exprs = {
        e
        for op in subsetted_ops.keys()
        for e in op.get_operations()
        # setic expressions can't get subset estimated
        if not e.has_trait(F.Expressions.is_setic)
    }
    exprs = F.Expressions.is_expression.sort_by_depth(exprs, ascending=True)

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

        # Step 5: Make new expr with subset literals
        res = mutator.create_check_and_insert_expression(
            mutator.utils.hack_get_expr_type(expr_e),
            *mapped_operands,
            from_ops=from_ops,
            allow_uncorrelated_congruence_match=True,
        )
        if res.out_operand is None:
            continue
        expr_subset = res.out_operand

        # Step 6: Superset old expr to subset estimated one
        # new_expr ⊆ original_expr (inverse of upper estimation)
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            expr_subset,
            expr_e.as_operand.get(),
            from_ops=from_ops,
            assert_=True,
        )
