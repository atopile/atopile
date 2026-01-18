# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
import faebryk.library.Expressions as Expressions
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
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

            # single domain
            # TODO need to ask expression output for type
            # .... thats annoying though
            representative = mutator.register_created_parameter(
                F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
                .create_instance(g=mutator.G_out)
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
    ```
    """
    # for all A ss! B | B not lit
    for ss_op in mutator.get_typed_expressions(
        F.Expressions.IsSubset,
        include_terminated=True,
        required_traits=(F.Expressions.is_predicate,),
    ):
        ss_op_e = ss_op.is_expression.get()
        ss_op_po = ss_op.is_parameter_operatable.get()
        A, B = ss_op_e.get_operands()
        if not (B_po := B.as_parameter_operatable.try_get()):
            continue

        # all B ss! C | C not A
        for C, e in mutator.utils.get_op_supersets(B_po).items():
            if C.is_same(A):
                continue
            # create A ss! C/X
            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                A,
                C,
                from_ops=[
                    ss_op_po,
                    e.is_parameter_operatable.get(),
                ],
                assert_=True,
            )

        # all B ss! X, X lit
        # for non-lits done by eq classes
        X = mutator.utils.try_extract_superset(B_po)
        if X is not None:
            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                A,
                X.as_operand.get(),
                from_ops=[ss_op_po, B_po],
                assert_=True,
            )


@algorithm("Distribute literals across alias classes", terminal=False)
def distribute_literals_across_alias_classes(mutator: Mutator):
    """
    Distribute literals across alias classes

    E is! A, Lit ss! A -> E ss! Lit
    E is! A, A ss! Lit -> Lit ss! E

    """
    for p in mutator.get_parameter_operatables():
        superset = mutator.utils.try_extract_superset(p)
        subset = mutator.utils.try_extract_subset(p)
        if superset is None and subset is None:
            continue

        non_lit_aliases = {
            e: other_p
            for e in p.get_operations(Is, predicates_only=True)
            if not e.is_expression.get().get_operand_literals()
            for other_p in e.is_expression.get().get_operand_operatables()
            if not other_p.is_same(p)
        }
        for alias_expr, po in non_lit_aliases.items():
            alias_expr_po = alias_expr.is_expression.get().as_parameter_operatable.get()
            po_op = po.as_operand.get()
            if superset is not None:
                superset_op = superset.as_operand.get()
                mutator.create_check_and_insert_expression(
                    F.Expressions.IsSubset,
                    po_op,
                    superset_op,
                    from_ops=[p, alias_expr_po],
                    assert_=True,
                )
            if subset is not None:
                subset_op = subset.as_operand.get()
                mutator.create_check_and_insert_expression(
                    F.Expressions.IsSubset,
                    subset_op,
                    po_op,
                    from_ops=[p, alias_expr_po],
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
    objs = mutator.get_typed_expressions()
    for obj in objs:
        obj_po = obj.get_trait(F.Parameters.is_parameter_operatable)
        if obj.try_get_trait(F.Expressions.is_predicate):
            continue
        if obj.has_trait(Expressions.has_side_effects):
            continue
        if any(
            e.try_get_trait(F.Expressions.is_predicate)
            or e.has_trait(Expressions.has_side_effects)
            for e in mutator.utils.get_expressions_involved_in(obj_po)
        ):
            continue
        mutator.remove(obj_po)


@algorithm("Predicate unconstrained operands deduce", terminal=True)
def predicate_unconstrained_operands_deduce(mutator: Mutator):
    """
    A op! B | A or B unconstrained -> A op!$ B
    """

    preds = mutator.get_expressions(required_traits=(F.Expressions.is_predicate,))
    for p_e in preds:
        if mutator.utils.is_literal_expression(p_e.as_operand.get()):
            continue

        for op in p_e.get_operand_operatables():
            if mutator.utils.no_other_predicates(
                op,
                p_e.as_assertable.force_get(),
                unfulfilled_only=True,
            ):
                mutator.terminate(p_e)
                break


# Estimation algorithms ----------------------------------------------------------------
@algorithm("Upper estimation", terminal=False)
def upper_estimation_of_expressions_with_subsets(mutator: Mutator):
    """
    If any operand in an expression has a superset literal,
    we can estimate the expression to the function applied to the superset literals.

    ```
    f(A{S|X}, B{S|Y}, C, ...)
        => f(A{S|X}, B{S|Y}, C, Z, ...) ⊆! f(X, Y, C, Z, ...)

    ```
    - f not setic
    - X not singleton

    TODO supersets (check correlation)
    """

    supersetted_ops = {
        op_subset.as_operand.get(): lit_superset
        for ss in mutator.get_typed_expressions(
            F.Expressions.IsSubset,
            required_traits=(F.Expressions.is_predicate,),
            include_terminated=True,
        )
        if (lit_superset := ss.get_superset_operand().as_literal.try_get())
        and (op_subset := ss.get_subset_operand().as_parameter_operatable.try_get())
        # singletons get taken care of by `convert_operable_aliased_to_single_into_literal`
        and not mutator.utils.is_correlatable_literal(lit_superset)
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
