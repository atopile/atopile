# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from itertools import combinations
from typing import cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.library.Expressions as Expressions
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.util import (
    EquivalenceClasses,
    groupby,
    not_none,
)

logger = logging.getLogger(__name__)

Add = F.Expressions.Add
GreaterOrEqual = F.Expressions.GreaterOrEqual
Is = F.Expressions.Is
IsSubset = F.Expressions.IsSubset
Multiply = F.Expressions.Multiply
Power = F.Expressions.Power

# TODO: mark terminal=False where applicable


@algorithm("Check literal contradiction", terminal=False)
def check_literal_contradiction(mutator: Mutator):
    """
    Check if a literal is contradictory
    """
    # TODO should be invariant

    pass


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
        ops: set[F.Parameters.is_parameter_operatable] = {
            # Literal expressions are basically literals
            o
            for o in is_expr.is_expression.get().get_operand_operatables()
            if not mutator.utils.is_literal_expression(o.as_operand.get())
        }
        # eq between non-literal operands
        full_eq.add_eq(*ops)
    p_eq_classes = full_eq.get(only_multi=True)

    # Make new param repre for alias classes
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
            mutator.get_copy_po(_repr_po)
            continue

        # Merge param alias classes
        representative = mutator.utils.merge_parameters(eq_class_params)

        for p in eq_class_params:
            mutator._mutate(
                p.as_parameter_operatable.get(),
                representative.as_parameter_operatable.get(),
            )

    for eq_class in p_eq_classes:
        eq_class_params = [p for p in eq_class if (p_po := p.as_parameter.try_get())]
        eq_class_exprs = {p_e for p in eq_class if (p_e := p.as_expression.try_get())}

        if eq_class_params:
            p_0 = eq_class_params[0]
            # See len(alias_class_params) == 1 case above
            if not mutator.has_been_mutated(p_0):
                continue
            representative = mutator.get_mutated(p_0)
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
            mutator.soft_replace(e_po, representative)
            if mutator.utils.are_aliased(e_po, *eq_class_params):
                continue
            mutator.create_check_and_insert_expression(
                F.Expressions.Is,
                e.as_operand.get(),
                representative.as_operand.get(),
                from_ops=list(eq_class),
                assert_=True,
                terminate=True,
            )


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


@algorithm("Predicate flat terminate", terminal=False)
def predicate_flat_terminate(mutator: Mutator):
    """
    ```
    P!(A, Lit) -> P!!(A, Lit)
    P!(Lit1, Lit2) -> P!!(Lit1, Lit2)
    ```

    Terminates all (dis)proven predicates that contain no expressions.
    """
    predicates = mutator.get_expressions(required_traits=(F.Expressions.is_predicate,))
    for p_e in predicates:
        p_po = p_e.as_parameter_operatable.get()
        if any(p_e.get_operands_with_trait(F.Expressions.is_expression)):
            continue

        # only (dis)proven
        if mutator.utils.try_extract_superset(p_po) is None:
            continue

        mutator.predicate_terminate(p_e.get_sibling_trait(F.Expressions.is_predicate))


@algorithm("Convert aliased singletons into literals", terminal=False)
def convert_operable_aliased_to_single_into_literal(mutator: Mutator):
    """
    A{S|5} + B -> ([5]) + B
    A{S|True} ^ B -> [True] ^ B
    """

    # TODO explore alt strat:
    # - find all lit aliases
    # - get all operations of each po
    # - iterate through those exprs
    # Attention: dont immediately replace, because we might have multiple literals

    exprs = mutator.get_expressions(sort_by_depth=True)
    for e in exprs:
        e_po = e.as_parameter_operatable.get()
        # A{S|Xs} ss! Xs
        if mutator.utils.is_set_literal_expression(e_po, allow_superset_exprs=True):
            continue

        e_ops = e.get_operands()
        # preserve non-replaceable operands
        # A{S|5} + B + C + 10 -> 5, B, C, 10
        ops = [
            lit.as_operand.get()
            if (lit := mutator.utils.is_replacable_by_literal(op))
            else op
            for op in e_ops
        ]

        if ops == e_ops:
            continue

        mutator.mutate_expression(e, operands=ops)


@algorithm("Isolate lone parameters", terminal=False)
def isolate_lone_params(mutator: Mutator):
    """
    If an expression is aliased to a literal, and only one parameter in the expression
    is not aliased to a literal, isolate the lone parameter on one side of the
    expression.

    Inversion operations must be constructed using canonical operators only.

    A + B is Lit1, B is Lit2, A further uncorrelated B -> A is Lit1 + (Lit2 * -1)
    """

    def _isolate_param(
        param: F.Parameters.is_parameter_operatable,
        op_with_param: F.Parameters.is_parameter_operatable,
        op_without_param: F.Parameters.can_be_operand,
        from_expr: F.Expressions.is_expression,
    ) -> tuple[F.Parameters.can_be_operand, F.Parameters.can_be_operand]:
        if not (op_with_param_e := op_with_param.as_expression.try_get()):
            return op_with_param.as_operand.get(), op_without_param

        def op_or_create_expr(
            operation: type[fabll.NodeT], *operands: F.Parameters.can_be_operand
        ) -> F.Parameters.can_be_operand:
            if len(operands) == 1:
                return operands[0]

            return mutator.create_check_and_insert_expression(
                operation,
                *operands,
                from_ops=[from_expr.as_parameter_operatable.get()],
            ).out_operand

        retained_ops = [
            op
            for op in op_with_param_e.get_operands()
            if param in mutator.utils.find_unique_params(op)
        ]

        moved_ops = [
            op
            for op in op_with_param_e.get_operands()
            if param not in mutator.utils.find_unique_params(op)
        ]

        if not moved_ops:
            return op_with_param.as_operand.get(), op_without_param

        op_node = fabll.Traits(op_with_param).get_obj_raw()
        if op_node.isinstance(F.Expressions.Add):
            return (
                op_or_create_expr(Add, *retained_ops),
                op_or_create_expr(
                    Add,
                    op_without_param,
                    *[
                        op_or_create_expr(
                            Multiply,
                            op,
                            mutator.make_singleton(-1)
                            .is_literal.get()
                            .as_operand.get(),
                        )
                        for op in moved_ops
                    ],
                ),
            )
        elif op_node.isinstance(F.Expressions.Multiply):
            return (
                op_or_create_expr(Multiply, *retained_ops),
                op_or_create_expr(
                    Multiply,
                    op_without_param,
                    op_or_create_expr(
                        Power,
                        op_or_create_expr(Multiply, *moved_ops),
                        mutator.make_singleton(-1).is_literal.get().as_operand.get(),
                    ),
                ),
            )
        elif op_node.isinstance(F.Expressions.Power):
            return (
                op_with_param_e.get_operands()[0],
                op_or_create_expr(
                    Power,
                    op_without_param,
                    mutator.make_singleton(-1).is_literal.get().as_operand.get(),
                ),  # TODO: fix exponent
            )
        else:
            return op_with_param.as_operand.get(), op_without_param

    def isolate_param(
        expr: F.Expressions.is_expression, param: F.Parameters.is_parameter_operatable
    ) -> (tuple[F.Parameters.can_be_operand, F.Parameters.can_be_operand]) | None:
        assert len(expr.get_operands()) == 2
        lhs, rhs = expr.get_operands()

        param_in_lhs = param in mutator.utils.find_unique_params(lhs)
        param_in_rhs = param in mutator.utils.find_unique_params(rhs)

        if param_in_lhs and param_in_rhs:
            # TODO
            # supporting this situation means committing to a strategy and sticking to
            # it
            # otherwise we might just make and undo changes until we run out of
            # iterations
            return None

        assert param_in_lhs or param_in_rhs

        op_with_param = lhs if param_in_lhs else rhs
        op_without_param = rhs if param_in_lhs else lhs

        while True:
            new_op_with_param, new_op_without_param = _isolate_param(
                param,
                op_with_param.as_parameter_operatable.force_get(),
                op_without_param,
                from_expr=expr,
            )

            if new_op_with_param.is_same(
                op_with_param
            ) and new_op_without_param.is_same(op_without_param):
                break

            op_with_param, op_without_param = new_op_with_param, new_op_without_param

            if op_with_param.is_same(param.as_operand.get()):
                return op_with_param, op_without_param

            # TODO: check for no further progress

    exprs = mutator.get_typed_expressions(Is, sort_by_depth=True)
    for expr in exprs:
        expr_e = expr.is_expression.get()
        expr_po = expr.is_expression.get().as_parameter_operatable.get()
        if mutator.utils.try_extract_superset(expr_po) is None:
            continue

        # TODO why? are we trying to do only arithmetic?
        # Then why not do isinstance(expr, Arithmetic)?
        if any(
            lit.op_setic_equals_singleton(True)
            for lit in expr_e.get_operand_literals().values()
        ):
            continue

        unaliased_params = {
            p
            for p in mutator.utils.find_unique_params(expr_po.as_operand.get())
            if mutator.utils.try_extract_superset(p) is None
        }

        # only handle single free var
        if len(unaliased_params) != 1:
            continue

        param = unaliased_params.pop()

        if param.as_operand.get() in expr_e.get_operands() and not any(
            op is not param and mutator.utils.find_unique_params(op) == {param}
            for op in expr_e.get_operands()
        ):
            # already isolated
            continue

        if (result := isolate_param(expr_e, param)) is None:
            continue

        mutator.mutate_expression(expr_e, operands=result)


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


@algorithm("Predicate unconstrained operands deduce", terminal=True)
def predicate_unconstrained_operands_deduce(mutator: Mutator):
    """
    A op! B | A or B unconstrained -> A op!$ B
    """

    preds = mutator.get_expressions(required_traits=(F.Expressions.is_predicate,))
    for p_e in preds:
        p = p_e.get_sibling_trait(F.Expressions.is_predicate)
        if mutator.is_predicate_terminated(p):
            continue
        if mutator.utils.is_literal_expression(p_e.as_operand.get()):
            continue

        for op in p_e.get_operand_operatables():
            if mutator.utils.no_other_predicates(
                op,
                p_e.as_assertable.force_get(),
                unfulfilled_only=True,
            ):
                mutator.create_check_and_insert_expression(
                    F.Expressions.IsSubset,
                    p_e.as_operand.get(),
                    mutator.make_singleton(True).can_be_operand.get(),
                    terminate=True,
                    assert_=True,
                )
                mutator.predicate_terminate(p)
                break


# Estimation algorithms ----------------------------------------------------------------
@algorithm("Upper estimation", terminal=False)
def upper_estimation_of_expressions_with_subsets(mutator: Mutator):
    """
    If any operand in an expression has a subset literal,
    we can add a subset to the expression.

    ```
    A + B{S|{1..5}} -> (A + B{S|{1..5}}) , (A + B{S|{1..5}}) ss! (A + {1..5})
    TODO supersets (check correlation)
    ```

    No need to check:
    ```
    A + B | A alias B ; never happens (after eq classes)
    A + B | B ss! singleton; never happens (after aliased_single_into_literal)
    TODO: A ss! B{S|X}
    TODO: A{S|Y} ss! B
    ```
    """

    return  # TODO

    new_literal_supersets = {
        (
            op.get_subset_operand().as_parameter_operatable.force_get()
        ): op.get_superset_operand().as_literal.force_get()
        for op in mutator.utils.get_literal_subsets(new_only=True)
    }

    new_exprs = {
        k: v
        for k, v in new_literal_supersets.items()
        if not mutator.utils.is_correlatable_literal(v)
    }

    exprs = {e for alias in new_exprs.keys() for e in alias.get_operations()}
    exprs.update((fabll.Traits(e).get_obj_raw() for e in mutator.non_copy_mutated))
    exprs = F.Expressions.is_expression.sort_by_depth(exprs, ascending=True)

    for expr in exprs:
        # In Is automatically by eq classes
        if expr.isinstance(F.Expressions.Is, F.Expressions.IsSubset):
            continue
        expr_e = expr.get_trait(F.Expressions.is_expression)
        # Taken care of by singleton fold
        if any(
            mutator.utils.is_replacable_by_literal(op) is not None
            for op in expr_e.get_operands()
        ):
            continue
        mapped_ops, operands_with_superset = (
            mutator.utils.map_operands_extracted_supersets(expr_e)
        )
        if not operands_with_superset:
            continue

        # TODO make this more efficient (include in extract)
        lit_ss_origins = {
            e.is_expression.get().as_parameter_operatable.get()
            for p in operands_with_superset
            for e in p.get_operations(IsSubset, predicates_only=True)
            if e.is_expression.get().get_operand_literals()
        }

        expr_po = expr.get_trait(F.Parameters.is_parameter_operatable)
        from_ops = [
            expr_po,
            *lit_ss_origins,
        ]

        # Make new expr with subset literals
        new_expr = mutator.create_check_and_insert_expression(
            mutator.utils.hack_get_expr_type(expr),
            *mapped_ops,
            from_ops=from_ops,
        )

        # Subset old expr to subset estimated one
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            expr_e,
            new_expr.as_operand.get(),
            from_ops=from_ops,
        )
