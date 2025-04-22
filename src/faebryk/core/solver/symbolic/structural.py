# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
import math
from itertools import combinations
from typing import cast

from faebryk.core.parameter import (
    Add,
    CanonicalExpression,
    ConstrainableExpression,
    Domain,
    Expression,
    GreaterOrEqual,
    HasSideEffects,
    Is,
    IsSubset,
    Multiply,
    Parameter,
    ParameterOperatable,
    Power,
)
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    Contradiction,
    ContradictionByLiteral,
    SolverLiteral,
    make_lit,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.sets.sets import BoolSet, P_Set
from faebryk.libs.util import (
    EquivalenceClasses,
    cast_assert,
    groupby,
)

logger = logging.getLogger(__name__)


# TODO: mark terminal=False where applicable


@algorithm("Check literal contradiction", terminal=False)
def check_literal_contradiction(mutator: Mutator):
    """
    Check if a literal is contradictory
    """

    mutator.get_literal_mappings(new_only=False, allow_subset=True)


@algorithm("Convert inequality with literal to subset", terminal=False)
def convert_inequality_with_literal_to_subset(mutator: Mutator):
    # TODO if not! A <= x it can be replaced by A intersect [-inf, a] is {}
    """
    This only works for inequalities we know cannot evaluate to {True, False}
    A >=! 5 -> A ss! [5, inf)
    5 >=! A -> A ss! (-inf, 5]

    A >=! [1, 10] -> A ss! [10, inf)
    [1, 10] >=! A -> A ss! (-inf, 1]
    """

    ge_exprs = {
        e
        for e in mutator.nodes_of_type(GreaterOrEqual, sort_by_depth=True)
        # Look for expressions with only one non-literal operand
        if e.constrained
        and len(list(op for op in e.operands if isinstance(op, ParameterOperatable)))
        == 1
    }

    for ge in ge_exprs:
        is_left = ge.operands[0] is next(iter(ge.operatable_operands))

        if is_left:
            param = ge.operands[0]
            lit = Quantity_Interval_Disjoint.from_value(ge.operands[1])
            boundary = lit.max_elem
            if math.isinf(boundary):
                if ge.constrained:
                    raise Contradiction(
                        "GreaterEqual inf not possible",
                        involved=[param],
                        mutator=mutator,
                    )
                mutator.utils.alias_is_literal_and_check_predicate_eval(ge, False)
                continue
            interval = Quantity_Interval_Disjoint(Quantity_Interval(min=boundary))
        else:
            param = ge.operands[1]
            lit = Quantity_Interval_Disjoint.from_value(ge.operands[0])
            boundary = lit.min_elem
            if math.isinf(boundary):
                if ge.constrained:
                    raise Contradiction(
                        "LessEqual -inf not possible",
                        involved=[param],
                        mutator=mutator,
                    )
                mutator.utils.alias_is_literal_and_check_predicate_eval(ge, False)
                continue
            interval = Quantity_Interval_Disjoint(Quantity_Interval(max=boundary))

        mutator.mutate_expression(
            ge,
            operands=[param, interval],
            expression_factory=IsSubset,
        )


@algorithm("Remove unconstrained", terminal=True)
def remove_unconstrained(mutator: Mutator):
    """
    Remove all expressions that are not involved in any constrained predicates
    or expressions with side effects
    Note: Not possible for Parameters, want to keep those around for REPR
    """
    objs = mutator.nodes_of_type(Expression)
    for obj in objs:
        if obj.constrained:
            continue
        if isinstance(obj, HasSideEffects):
            continue
        if any(
            e.constrained or isinstance(e, HasSideEffects)
            for e in mutator.utils.get_expressions_involved_in(obj)
        ):
            continue
        mutator.remove(obj)


@algorithm("Remove congruent expressions", terminal=False)
def remove_congruent_expressions(mutator: Mutator):
    """
    Remove expressions that are congruent to other expressions

    ```
    X1 := A + B, X2 := A + B -> [{X1, X2}, {A}, {B}]
    ```
    """
    # X1 = A + B, X2 = A + B -> X1 is X2
    # No (Invalid): X1 = A + [0, 10], X2 = A + [0, 10]
    # No (Automatic): X1 = A + C, X2 = A + B, C ~ B -> X1 ~ X2

    all_exprs = mutator.nodes_of_type(Expression, sort_by_depth=True)
    # optimization: can't be congruent if they have uncorrelated literals
    all_exprs = [e for e in all_exprs if not e.get_uncorrelatable_literals()]
    # TODO is this fully correct?
    # optimization: Is, IsSubset already handled
    all_exprs = [
        e
        for e in all_exprs
        if not (
            isinstance(e, (Is, IsSubset)) and e.constrained and e.get_operand_literals()
        )
    ]
    exprs_by_type = groupby(
        all_exprs,
        lambda e: (
            type(e),
            len(e.operands),
            None if not isinstance(e, ConstrainableExpression) else e.constrained,
        ),
    )
    full_eq = EquivalenceClasses[Expression](all_exprs)

    for exprs in exprs_by_type.values():
        if len(exprs) <= 1:
            continue
        # TODO use hash to speed up comparisons
        for e1, e2 in combinations(exprs, 2):
            # no need for recursive, since subexpr already merged if congruent
            if not full_eq.is_eq(e1, e2) and e1.is_congruent_to(e2, recursive=False):
                full_eq.add_eq(e1, e2)

    repres = {}
    for expr in all_exprs:
        eq_class = full_eq.classes[expr]
        if len(eq_class) <= 1:
            continue

        eq_id = id(eq_class)
        if eq_id not in repres:
            representative = mutator.mutate_expression(expr)
            repres[eq_id] = representative

            # propagate constrained & terminate
            if isinstance(representative, ConstrainableExpression):
                eq_class = cast(set[ConstrainableExpression], eq_class)
                representative.constrained = any(e.constrained for e in eq_class)
                if any(mutator.is_predicate_terminated(e) for e in eq_class):
                    mutator.predicate_terminate(representative)

        mutator._mutate(expr, repres[eq_id])


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
    param_ops = mutator.nodes_of_type(ParameterOperatable)
    full_eq = EquivalenceClasses[ParameterOperatable](param_ops)
    is_exprs = mutator.utils.get_all_aliases()
    for is_expr in is_exprs:
        ops = {
            # Literal expressions are basically literals
            o
            for o in is_expr.get_operand_operatables()
            if not mutator.utils.is_literal_expression(o)
        }
        # eq between non-literal operands
        full_eq.add_eq(*ops)
    p_eq_classes = full_eq.get(only_multi=True)

    # Make new param repre for alias classes
    for eq_class in p_eq_classes:
        eq_class_params = [p for p in eq_class if isinstance(p, Parameter)]
        eq_class_exprs = {p for p in eq_class if isinstance(p, Expression)}

        if not eq_class_params:
            continue

        if len(eq_class_params) == 1:
            # check if all in eq_class already aliased
            # Then no need to to create new representative
            _repr = eq_class_params[0]
            iss = _repr.get_operations(Is)
            iss_exprs = {
                o
                for e in iss
                for o in e.operatable_operands
                if isinstance(o, Expression)
            }
            if eq_class_exprs.issubset(iss_exprs):
                # check if all predicates are already propagated
                class_expressions = {
                    e
                    for operand in eq_class_exprs
                    for e in operand.get_operations()
                    # skip POps Is, because they create the alias classes
                    # or literal aliases (done by distribute algo)
                    if not (isinstance(e, Is) and e.constrained)
                    # skip literal subsets (done by distribute algo)
                    and not (
                        isinstance(e, IsSubset)
                        and e.get_operand_literals()
                        and e.constrained
                    )
                }
                if not class_expressions:
                    continue
            # else
            mutator.get_copy(_repr)
            continue

        # Merge param alias classes
        representative = mutator.utils.merge_parameters(eq_class_params)

        for p in eq_class_params:
            mutator._mutate(p, representative)

    for eq_class in p_eq_classes:
        eq_class_params = [p for p in eq_class if isinstance(p, Parameter)]
        eq_class_exprs = [p for p in eq_class if isinstance(p, Expression)]

        # single domain
        domain = Domain.get_shared_domain(*(op.domain for op in eq_class))

        if eq_class_params:
            # See len(alias_class_params) == 1 case above
            if not mutator.has_been_mutated(eq_class_params[0]):
                continue
            representative = mutator.get_mutated(eq_class_params[0])
        else:
            # If not params or lits in class, create a new param as representative
            # for expressions
            representative = mutator.register_created_parameter(
                Parameter(domain=domain), from_ops=list(eq_class)
            )

        for e in eq_class_exprs:
            mutator.soft_replace(e, representative)
            if mutator.utils.are_aliased(e, *eq_class_params):
                continue
            mutator.utils.alias_to(e, representative, from_ops=list(eq_class))


@algorithm("Merge intersecting subsets", terminal=False)
def merge_intersect_subsets(mutator: Mutator):
    """
    A subset L1
    A subset L2
    -> A subset (L1 & L2)

    x = A subset L1
    y = A subset L2
    Z = x and y -> Z = x & y
    -> A subset (L1 & L2)
    """

    # TODO use Intersection/Union expr
    # A ss B, A ss C -> A ss (B & C)
    # and then use literal folding
    # should also work for others:
    #   A < B, A < C -> A < (B | C)
    # Got to consider when to Intersect/Union is more useful than the associative

    # this merge is already done implicitly by try_extract_literal
    # but it's still needed to create the explicit subset op

    params = mutator.nodes_of_type(ParameterOperatable, sort_by_depth=True)

    for param in params:
        ss_lits = {
            k: vs
            for k, vs in mutator.utils.get_supersets(param).items()
            if mutator.utils.is_literal(k)
        }
        if len(ss_lits) <= 1:
            continue

        intersected = P_Set.intersect_all(*ss_lits.keys())

        # short-cut, would be detected by subset_to
        if intersected.is_empty():
            raise ContradictionByLiteral(
                "Intersection of literals is empty",
                involved=[param],
                literals=list(ss_lits.keys()),
                mutator=mutator,
            )

        old_ss = [old_ss for old_sss in ss_lits.values() for old_ss in old_sss]

        # already exists
        if intersected in ss_lits:
            target = ss_lits[intersected][0]
        else:
            target = mutator.utils.subset_to(param, intersected, from_ops=old_ss)
            assert isinstance(target, (IsSubset, Is))

        # Merge
        for old_ss in old_ss:
            mutator._mutate(old_ss, mutator.get_copy(target))


@algorithm("Empty set", terminal=False)
def empty_set(mutator: Mutator):
    """
    A is {} -> False
    A ss {} -> False
    """

    # A is {} -> False
    for e in mutator.nodes_of_type(Is):
        lits = cast(dict[int, SolverLiteral], e.get_operand_literals())
        if not lits:
            continue
        if any(lit.is_empty() for lit in lits.values()):
            mutator.utils.alias_is_literal_and_check_predicate_eval(e, False)

    # A ss {} -> False
    # Converted by literal_folding


@algorithm("Transitive subset", terminal=False)
def transitive_subset(mutator: Mutator):
    """
    ```
    A ss! B, B ss! C -> new A ss! C
    A ss! B, B is! X -> new A ss! X
    ```
    """
    # for all A ss! B | B not lit
    for ss_op in mutator.utils.get_all_subsets():
        A, B = ss_op.operands
        if not isinstance(B, ParameterOperatable):
            continue

        # all B ss! C | C not A
        for C, es in mutator.utils.get_supersets(B).items():
            if C is A:
                continue
            # create A ss! C/X
            mutator.utils.subset_to(A, C, from_ops=[ss_op, *es])

        # all B is! X, X lit
        # for non-lits done by eq classes
        X = mutator.utils.try_extract_literal(B)
        if X is not None:
            mutator.utils.subset_to(A, X, from_ops=[ss_op, B])


@algorithm("Predicate flat terminate", terminal=False)
def predicate_flat_terminate(mutator: Mutator):
    """
    ```
    P!(A, Lit) -> P!!(A, Lit)
    P!(Lit1, Lit2) -> P!!(Lit1, Lit2)
    ```

    Terminates all (dis)proven predicates that contain no expressions.
    """
    predicates = mutator.nodes_of_type(ConstrainableExpression)
    for p in predicates:
        if not p.constrained:
            continue

        if any(isinstance(po, Expression) for po in p.operatable_operands):
            continue

        # only (dis)proven
        if mutator.utils.try_extract_literal(p) is None:
            continue

        mutator.predicate_terminate(p)


@algorithm("Predicate is!! True", terminal=False)
def predicate_terminated_is_true(mutator: Mutator):
    """
    P!! is! True -> P!! is!! True
    """

    for p in mutator.nodes_of_type(Is):
        if not p.constrained:
            continue
        if mutator.is_predicate_terminated(p):
            continue
        if make_lit(True) not in p.operands:
            continue
        if not p.operatable_operands:
            continue
        op = next(iter(p.operatable_operands))
        if not op.constrained or not mutator.is_predicate_terminated(op):
            continue

        mutator.predicate_terminate(p)


@algorithm("Convert aliased singletons into literals", terminal=False)
def convert_operable_aliased_to_single_into_literal(mutator: Mutator):
    """
    A is ([5]), A + B -> ([5]) + B
    A is [True], A ^ B -> [True] ^ B
    """

    exprs = mutator.nodes_of_type(Expression, sort_by_depth=True)
    for e in exprs:
        if mutator.utils.is_pure_literal_expression(e):
            continue
        # handled in _todo
        if mutator.utils.is_alias_is_literal(e) or mutator.utils.is_subset_literal(e):
            continue
        # not handling here
        if (
            isinstance(e, (Is, IsSubset))
            and e.constrained
            and any(mutator.utils.is_constrained(op) for op in e.operatable_operands)
        ):
            continue

        ops = []
        found_literal = False
        for op in e.operands:
            lit = mutator.utils.is_replacable_by_literal(op)
            # preserve non-replaceable operands
            # A + B + C | A is ([5]) -> B, C
            if lit is None:
                ops.append(op)
                continue
            ops.append(lit)
            found_literal = True

        if not found_literal:
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
        param: ParameterOperatable,
        op_with_param: ParameterOperatable,
        op_without_param: ParameterOperatable,
        from_expr: Expression,
    ) -> tuple[ParameterOperatable.All, ParameterOperatable.All]:
        if not isinstance(op_with_param, Expression):
            return op_with_param, op_without_param

        def op_or_create_expr(
            operation: type[CanonicalExpression], *operands: ParameterOperatable.All
        ) -> ParameterOperatable.All:
            if len(operands) == 1:
                return operands[0]

            return mutator.create_expression(operation, *operands, from_ops=[from_expr])

        retained_ops = [
            op
            for op in op_with_param.operands
            if param in mutator.utils.find_unique_params(op)
        ]

        moved_ops = [
            op
            for op in op_with_param.operands
            if param not in mutator.utils.find_unique_params(op)
        ]

        if not moved_ops:
            return op_with_param, op_without_param

        match op_with_param, op_without_param:
            case (Add(), _):
                return (
                    op_or_create_expr(Add, *retained_ops),
                    op_or_create_expr(
                        Add,
                        op_without_param,
                        *[
                            op_or_create_expr(Multiply, op, make_lit(-1))
                            for op in moved_ops
                        ],
                    ),
                )
            case (Multiply(), _):
                return (
                    op_or_create_expr(Multiply, *retained_ops),
                    op_or_create_expr(
                        Multiply,
                        op_without_param,
                        op_or_create_expr(
                            Power, op_or_create_expr(Multiply, *moved_ops), make_lit(-1)
                        ),
                    ),
                )
            case (Power(), _):
                return (
                    op_with_param.operands[0],
                    op_or_create_expr(
                        Power, op_without_param, make_lit(-1)
                    ),  # TODO: fix exponent
                )
            case (_, _):
                return op_with_param, op_without_param

    def isolate_param(
        expr: Expression, param: ParameterOperatable
    ) -> (tuple[ParameterOperatable.All, ParameterOperatable.All]) | None:
        assert len(expr.operands) == 2
        lhs, rhs = expr.operands

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
                param, op_with_param, op_without_param, from_expr=expr
            )

            if (
                new_op_with_param == op_with_param
                and new_op_without_param == op_without_param
            ):
                break

            op_with_param, op_without_param = new_op_with_param, new_op_without_param

            if op_with_param == param:
                return op_with_param, op_without_param

            # TODO: check for no further progress

    exprs = mutator.nodes_of_type(Is, sort_by_depth=True)
    for expr in exprs:
        if mutator.utils.try_extract_literal(expr) is None:
            continue

        # TODO why? are we trying to do only arithmetic?
        # Then why not do isinstance(expr, Arithmetic)?
        if BoolSet(True) in expr.operands:
            continue

        unaliased_params = {
            p
            for p in mutator.utils.find_unique_params(expr)
            if mutator.utils.try_extract_literal(p) is None
        }

        # only handle single free var
        if len(unaliased_params) != 1:
            continue

        param = unaliased_params.pop()

        if param in expr.operands and not any(
            op is not param and mutator.utils.find_unique_params(op) == {param}
            for op in expr.operands
        ):
            # already isolated
            continue

        if (result := isolate_param(expr, param)) is None:
            continue

        mutator.mutate_expression(expr, operands=result)


@algorithm("Distribute literals across alias classes", terminal=False)
def distribute_literals_across_alias_classes(mutator: Mutator):
    """
    Distribute literals across alias classes

    E is A, A is Lit -> E is Lit
    E is A, A ss Lit -> E ss Lit

    """
    for p in mutator.nodes_of_type():
        lit, is_alias = mutator.utils.try_extract_literal_info(p)
        if lit is None:
            continue

        non_lit_aliases = {
            e: other_p
            for e in p.get_operations(Is, constrained_only=True)
            if not e.get_operand_literals()
            and (other_p := cast_assert(ParameterOperatable, e.get_other_operand(p)))
            is not p
        }
        for alias_expr, alias in non_lit_aliases.items():
            if is_alias:
                mutator.utils.alias_to(alias, lit, from_ops=[p, alias_expr])
            else:
                mutator.utils.subset_to(alias, lit, from_ops=[p, alias_expr])


# Terminal -----------------------------------------------------------------------------


@algorithm("Predicate unconstrained operands deduce", terminal=True)
def predicate_unconstrained_operands_deduce(mutator: Mutator):
    """
    A op! B | A or B unconstrained -> A op!! B
    """

    preds = mutator.nodes_of_type(ConstrainableExpression)
    for p in preds:
        if not p.constrained:
            continue
        if mutator.is_predicate_terminated(p):
            continue
        if mutator.utils.is_literal_expression(p):
            continue

        for op in p.operatable_operands:
            if mutator.utils.no_other_constraints(op, p, unfulfilled_only=True):
                mutator.utils.alias_is_literal_and_check_predicate_eval(p, True)
                break


# Estimation algorithms ----------------------------------------------------------------
@algorithm("Upper estimation", terminal=False)
def upper_estimation_of_expressions_with_subsets(mutator: Mutator):
    """
    If any operand in an expression has a subset literal,
    we can add a subset to the expression.

    ```
    A + B | B is [1,5] -> (A + B) , (A + B) subset (A + [1,5])
    A + B | B subset [1,5] -> (A + B) , (A + B) subset (A + [1,5])
    ```

    No need to check:
    ```
    A + B | A alias B ; never happens (after eq classes)
    A + B | B alias ([0]); never happens (after aliased_single_into_literal)
    ```
    """

    new_literal_mappings = mutator.get_literal_mappings(
        new_only=True, allow_subset=True
    )
    new_exprs = {
        k: v
        for k, v in new_literal_mappings.items()
        if not mutator.utils.is_correlatable_literal(v)
    }

    exprs = {e for alias in new_exprs.keys() for e in alias.get_operations()}
    exprs.update(mutator.non_copy_mutated)
    exprs = ParameterOperatable.sort_by_depth(exprs, ascending=True)

    for expr in exprs:
        assert isinstance(expr, CanonicalExpression)
        # In Is automatically by eq classes
        if isinstance(expr, Is):
            continue
        # Taken care of by singleton fold
        if any(
            mutator.utils.is_replacable_by_literal(op) is not None
            for op in expr.operands
        ):
            continue
        # optimization: don't take away from uncorrelated_alias_fold
        if (
            mutator.terminal
            # not (expr in new_subsets and expr not in new_aliases)
            and not any(mutator.utils.get_correlations(expr))
            and mutator.utils.map_extract_literals(expr)[1]
        ):
            continue
        # In subset useless to look at subset lits
        no_allow_subset_lit = isinstance(expr, IsSubset)

        operands, any_lit = mutator.utils.map_extract_literals(
            expr, allow_subset=not no_allow_subset_lit
        )
        if not any_lit:
            continue

        # TODO make this more efficient (include in extract)
        lit_alias_origins = {
            e
            for p in any_lit
            for e in p.get_operations(Is, constrained_only=True)
            if e.get_operand_literals()
        }

        # Make new expr with subset literals
        mutator.mutate_expression(
            expr,
            operands=operands,
            soft_mutate=IsSubset,
            from_ops=[expr, *lit_alias_origins],
        )


@algorithm("Uncorrelated alias fold", terminal=True)
def uncorrelated_alias_fold(mutator: Mutator):
    """
    If an operation contains only operands that are not correlated with each other,
    we can replace the operands with their corresponding literals.
    ```
    op(As), no correlations in As outside of op, len(A is Lit in As) > 0
    -> op(As) is! op(As replaced by corresponding lits)
    ```

    Terminal because relies on missing correlations.
    """

    new_literal_mappings = mutator.get_literal_mappings(new_only=True)

    # bool expr always map to singles
    new_literal_mappings_filtered = {
        k: v
        for k, v in new_literal_mappings.items()
        if not mutator.utils.is_correlatable_literal(v)
    }
    exprs = {
        e for alias in new_literal_mappings_filtered for e in alias.get_operations()
    }
    # Include mutated since last run
    exprs.update(mutator.non_copy_mutated)
    exprs = ParameterOperatable.sort_by_depth(exprs, ascending=True)

    for expr in exprs:
        assert isinstance(expr, CanonicalExpression)
        # Taken care of by singleton fold
        if any(
            mutator.utils.is_replacable_by_literal(op) is not None
            for op in expr.operands
        ):
            continue
        if isinstance(expr, Is) and expr.constrained:
            # TODO: definitely need to do something
            # just not the same what we do with the other types
            continue
        # TODO: we can weaken this to not replace correlated operands instead of
        #   skipping the whole expression
        # check if any correlations
        if any(mutator.utils.get_correlations(expr)):
            continue

        operands, any_lit = mutator.utils.map_extract_literals(expr)
        if not any_lit:
            continue

        # TODO make this more efficient (include in extract)
        lit_alias_origins = {
            e
            for p in any_lit
            for e in p.get_operations(Is, constrained_only=True)
            if e.get_operand_literals()
        }

        # no point in op! is op! (always true)
        if expr.constrained:
            mutator.create_expression(
                type(expr),
                *operands,
                constrain=True,
                allow_uncorrelated=True,
                from_ops=[expr, *lit_alias_origins],
            )
            continue

        mutator.mutate_expression(
            expr,
            operands=operands,
            soft_mutate=Is,
            from_ops=[expr, *lit_alias_origins],
        )
