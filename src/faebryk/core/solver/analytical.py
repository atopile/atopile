# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from functools import partial
from itertools import combinations
from typing import cast

from faebryk.core.parameter import (
    Add,
    ConstrainableExpression,
    Domain,
    Expression,
    GreaterOrEqual,
    Is,
    IsSubset,
    Multiply,
    Parameter,
    ParameterOperatable,
    Power,
)
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    S_LOG,
    CanonicalOperation,
    ContradictionByLiteral,
    FullyAssociative,
    SolverLiteral,
    algorithm,
    alias_is_literal,
    alias_is_literal_and_check_predicate_eval,
    find_unique_params,
    flatten_associative,
    get_all_aliases,
    get_all_subsets,
    get_constrained_expressions_involved_in,
    get_correlations,
    get_supersets,
    is_correlatable_literal,
    is_literal,
    is_literal_expression,
    is_replacable,
    is_replacable_by_literal,
    make_lit,
    map_extract_literals,
    merge_parameters,
    no_other_constrains,
    subset_literal,
    subset_to,
    try_extract_all_literals,
    try_extract_literal,
    try_extract_literal_info,
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
    not_none,
)

logger = logging.getLogger(__name__)

if S_LOG:
    logger.setLevel(logging.DEBUG)


# TODO: mark destructive=False where applicable


@algorithm("Convert inequality with literal to subset")
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
            interval = Quantity_Interval_Disjoint(Quantity_Interval(min=lit.max_elem))
        else:
            param = ge.operands[1]
            lit = Quantity_Interval_Disjoint.from_value(ge.operands[0])
            interval = Quantity_Interval_Disjoint(Quantity_Interval(max=lit.min_elem))

        mutator.mutate_expression(
            ge,
            operands=[param, interval],
            expression_factory=IsSubset,
        )


@algorithm("Remove unconstrained")
def remove_unconstrained(mutator: Mutator):
    """
    Remove all expressions that are not involved in any constrained predicates
    Note: Not possible for Parameters, want to keep those around for REPR
    """
    objs = mutator.nodes_of_type(Expression)
    for obj in objs:
        if get_constrained_expressions_involved_in(obj):
            continue
        mutator.remove(obj)


@algorithm("Remove congruent expressions")
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
    exprs_by_type = groupby(all_exprs, type)
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

            # propagate constrained & marked true
            if isinstance(representative, ConstrainableExpression):
                eq_class = cast(set[ConstrainableExpression], eq_class)
                representative.constrained = any(e.constrained for e in eq_class)
                if any(mutator.is_predicate_true(e) for e in eq_class):
                    mutator.mark_predicate_true(representative)

        mutator._mutate(expr, repres[eq_id])


@algorithm("Alias classes")
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
    is_exprs = get_all_aliases(mutator)
    for is_expr in is_exprs:
        full_eq.add_eq(*is_expr.operatable_operands)
    p_eq_classes = full_eq.get()

    # Make new param repre for alias classes
    for eq_class in p_eq_classes:
        if len(eq_class) <= 1:
            continue

        alias_class_p_ops = [
            p
            for p in eq_class
            if isinstance(p, ParameterOperatable)
            # Literal expressions are basically literals
            and not is_literal_expression(p)
        ]
        alias_class_params = [p for p in alias_class_p_ops if isinstance(p, Parameter)]
        alias_class_exprs = {p for p in alias_class_p_ops if isinstance(p, Expression)}

        if len(alias_class_p_ops) <= 1:
            continue
        if not alias_class_params:
            continue

        if len(alias_class_params) == 1:
            # check if all in eq_class already aliased
            # Then no need to to create new representative
            _repr = alias_class_params[0]
            iss = _repr.get_operations(Is)
            iss_exprs = {
                o
                for e in iss
                for o in e.operatable_operands
                if isinstance(o, Expression)
            }
            if alias_class_exprs.issubset(iss_exprs):
                # check if all predicates are already propagated
                class_expressions = {
                    e
                    for operand in alias_class_exprs
                    for e in operand.get_operations()
                    # skip POps Is, because they create the alias classes
                    # or literal aliases (done by distribute algo)
                    if not isinstance(e, Is)
                    # skip literal subsets (done by distribute algo)
                    and not (isinstance(e, IsSubset) and e.get_literal_operands())
                }
                if not class_expressions:
                    continue

        # Merge param alias classes
        representative = merge_parameters(alias_class_params)

        for p in alias_class_params:
            mutator._mutate(p, representative)

    for eq_class in p_eq_classes:
        if len(eq_class) <= 1:
            continue
        alias_class_p_ops = [
            p
            for p in eq_class
            if isinstance(p, ParameterOperatable)
            # Literal expressions are basically literals
            and not is_literal_expression(p)
        ]
        alias_class_params = [p for p in alias_class_p_ops if isinstance(p, Parameter)]
        alias_class_exprs = [p for p in alias_class_p_ops if isinstance(p, Expression)]

        if len(alias_class_p_ops) <= 1:
            continue

        # TODO non unit/numeric params, i.e. enums, bools

        # single domain
        # TODO check domain for literals
        domain = Domain.get_shared_domain(*(p.domain for p in alias_class_p_ops))

        if alias_class_params:
            # See len(alias_class_params) == 1 case above
            if not mutator.has_been_mutated(alias_class_params[0]):
                continue
            representative = mutator.get_mutated(alias_class_params[0])
        else:
            # If not params or lits in class, create a new param as representative
            # for expressions
            representative = mutator.register_created_parameter(
                Parameter(domain=domain), from_ops=alias_class_p_ops
            )

        # Repr old expr with new param, but keep old expr around
        # This will implicitly swap out the expr in other exprs with the repr
        for e in alias_class_exprs:
            copy_expr = mutator.mutate_expression(e)
            expr = mutator.create_expression(
                Is, copy_expr, representative, from_ops=alias_class_p_ops
            )
            expr.constrain()  # p_eq_classes is derived from constrained exprs only
            # DANGER!
            mutator._override_repr(e, representative)

    # TODO remove, done by tautologies I think
    # remove eq_class Is (for non-literal alias classes)
    # removed = {
    #     e
    #     for e in mutator.nodes_of_type(Is)
    #     if all(mutator.has_been_mutated(operand) for operand in e.operands)
    #     and not e.get_operations()
    # }
    # mutator.remove(*removed)


@algorithm("Distribute literals across alias classes", destructive=False)
def distribute_literals_across_alias_classes(mutator: Mutator):
    """
    Distribute literals across alias classes

    E is A, A is Lit -> E is Lit
    E is A, A ss Lit -> E ss Lit

    """
    for p in mutator.nodes_of_type():
        lit, is_alias = try_extract_literal_info(p)
        if lit is None:
            continue

        non_lit_aliases = {
            cast_assert(ParameterOperatable, e.get_other_operand(p))
            for e in p.get_operations(Is, constrained_only=True)
            if not e.get_literal_operands()
        }
        for alias in non_lit_aliases:
            if is_alias:
                alias_is_literal(alias, lit, mutator, from_ops=[p])
            else:
                subset_literal(alias, lit, mutator, from_ops=[p])


@algorithm("Merge intersecting subsets")
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
        ss_lits = {v: e for v, e in get_supersets(param).items() if is_literal(v)}
        if len(ss_lits) <= 1:
            continue

        intersected = P_Set.intersect_all(*ss_lits.keys())

        # already exists
        if intersected in ss_lits:
            continue

        # short-cut, would be detected by subset_to
        if intersected.is_empty():
            raise ContradictionByLiteral(
                "Intersection of literals is empty",
                involved=[param],
                literals=list(ss_lits.keys()),
            )

        subset_to(param, intersected, mutator, from_ops=list(ss_lits.values()))


@algorithm("Associative expressions Full")
def compress_associative(mutator: Mutator):
    """
    Makes
    ```
    (A + B) + (C + (D + E))
       Y    Z    X    W
    -> +(A,B,C,D,E)
       Z'

    for +, *, and, or, &, |, ^
    """
    ops = cast(
        list[FullyAssociative],
        mutator.nodes_of_types(FullyAssociative, sort_by_depth=True),
    )
    # get out deepest expr in compressable tree
    root_ops = [e for e in ops if type(e) not in {type(n) for n in e.get_operations()}]

    for expr in root_ops:
        res = flatten_associative(
            expr, partial(is_replacable, mutator.transformations.mutated)
        )
        if not res.destroyed_operations:
            continue

        mutator.remove(*res.destroyed_operations)

        mutator.mutate_expression(
            expr,
            operands=res.extracted_operands,
        )


@algorithm("Empty set")
def empty_set(mutator: Mutator):
    """
    A is {} -> False
    A ss {} -> False
    """

    # A is {} -> False
    for e in mutator.nodes_of_type(Is):
        lits = cast(dict[int, SolverLiteral], e.get_literal_operands())
        if not lits:
            continue
        if any(lit.is_empty() for lit in lits.values()):
            alias_is_literal_and_check_predicate_eval(e, False, mutator)

    # A ss {} -> False
    # Converted by literal_folding


@algorithm("Upper estimation")
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

    new_aliases = mutator.get_literal_aliased(new_only=True)
    new_subsets = mutator.get_literal_subsets(new_only=True)

    new_exprs = {
        k: v
        for k, v in (new_aliases | new_subsets).items()
        if not is_correlatable_literal(v)
    }

    exprs = {e for alias in new_exprs.keys() for e in alias.get_operations()}
    for expr in exprs:
        assert isinstance(expr, CanonicalOperation)
        # In Is automatically by eq classes
        if isinstance(expr, Is):
            continue
        # In subset useless to look at subset lits
        no_allow_subset_lit = isinstance(expr, IsSubset)

        operands = []
        for op in expr.operands:
            if not isinstance(op, ParameterOperatable):
                operands.append(op)
                continue

            subset_lits = try_extract_literal(op, allow_subset=not no_allow_subset_lit)
            if subset_lits is None:
                operands.append(op)
                continue
            operands.append(subset_lits)

        # Make new expr with subset literals
        mutator.mutate_expression(expr, operands=operands, soft_mutate=IsSubset)


@algorithm("Transitive subset")
def transitive_subset(mutator: Mutator):
    """
    ```
    A ss! B, B ss! C -> new A ss! C
    A ss! B, B is! X -> new A ss! X
    ```
    """
    # for all A ss! B | B not lit
    for ss_op in get_all_subsets(mutator):
        A, B = ss_op.operands
        if not isinstance(B, ParameterOperatable):
            continue

        # all B ss! C | C not A
        for C, e in get_supersets(B).items():
            if C is A:
                continue
            # create A ss! C/X
            subset_to(A, C, mutator, from_ops=[ss_op, e])

        # all B is! X, X lit
        # for non-lits done by eq classes
        X = try_extract_literal(B)
        if X is not None:
            subset_to(A, X, mutator, from_ops=[ss_op])


@algorithm("Remove empty graphs", destructive=True)
def remove_empty_graphs(mutator: Mutator):
    """
    If there is only one predicate, it can be replaced by True
    If there are no predicates, the graph can be removed
    """

    # FIXME: rewrite with multi graph support
    return

    predicates = [
        p
        for p in mutator.nodes_of_type(ConstrainableExpression)
        if p.constrained
        # TODO consider marking predicates as irrelevant or something
        # Ignore Is!!(P!!, True)
        and not (
            isinstance(p, Is)
            and p._solver_evaluates_to_true
            and (
                # Is!!(P!!, True)
                (
                    BoolSet(True) in p.get_literal_operands().values()
                    and all(
                        isinstance(inner, ConstrainableExpression)
                        and inner.constrained
                        and inner._solver_evaluates_to_true
                        for inner in p.get_operatable_operands()
                    )
                )
                # Is!!(A, A)
                or p.operands[0] is p.operands[1]
            )
        )
    ]

    if len(predicates) > 1:
        return

    for p in predicates:
        alias_is_literal_and_check_predicate_eval(p, True, mutator)

    # Never remove predicates
    if predicates:
        return

    # If there are no predicates, the graph can be removed
    mutator.remove_graph()


@algorithm("Predicate literal deduce")
def predicate_literal_deduce(mutator: Mutator):
    """
    ```
    P!(A, Lit) -> P!!(A, Lit)
    P!(Lit1, Lit2) -> P!!(Lit1, Lit2)
    ```

    Proof:
    ```
    >=, >, is, ss, or, not
    P1!(A, Lit1) True
    P2!(A, Lit2)
    P3!(A, B)
    P3!!(A, B)
    ```
    """
    # FIXME: I dont think this is actually true
    return
    predicates = mutator.nodes_of_type(ConstrainableExpression)
    for p in predicates:
        if not p.constrained:
            continue
        lits = not_none(try_extract_all_literals(p, accept_partial=True))
        if len(p.operands) - len(lits) <= 1:
            mutator.mark_predicate_true(p)


@algorithm("Predicate unconstrained operands deduce", destructive=True)
def predicate_unconstrained_operands_deduce(mutator: Mutator):
    """
    A op! B | A or B unconstrained -> A op!! B
    """
    # FIXME rethink this
    return

    preds = mutator.nodes_of_type(ConstrainableExpression)
    for p in preds:
        if not p.constrained:
            continue
        if mutator.is_predicate_true(p):
            continue

        if any(ParameterOperatable.is_literal(o) for o in p.operands):
            continue

        if no_other_constrains(p.operands[0], p, unfulfilled_only=True):
            alias_is_literal_and_check_predicate_eval(p, True, mutator)
            return
        if no_other_constrains(p.operands[1], p, unfulfilled_only=True):
            alias_is_literal_and_check_predicate_eval(p, True, mutator)
            return


@algorithm("Convert aliased singletons into literals")
def convert_operable_aliased_to_single_into_literal(mutator: Mutator):
    """
    A is ([5]), A + B -> ([5]) + B
    A is [True], A ^ B -> [True] ^ B
    """

    exprs = mutator.nodes_of_type(Expression, sort_by_depth=True)
    for e in exprs:
        if is_literal_expression(e):
            continue

        ops = []
        found_literal = False
        for op in e.operands:
            lit = is_replacable_by_literal(op)
            # preserve non-replaceable operands
            # A + B + C | A is ([5]) -> B, C
            if lit is None:
                ops.append(op)
                continue
            # Don't make from A is! X -> X is! X
            if isinstance(e, Is) and e.constrained and lit in e.operands:
                continue
            ops.append(lit)
            found_literal = True

        if not found_literal:
            continue

        # don't mutate predicates
        # if isinstance(e, ConstrainableExpression) and e.constrained:
        #    # FIXME
        #    # mutator.create_expression(type(e), *ops).constrain()
        #    continue

        mutator.mutate_expression(e, operands=ops)


@algorithm("Isolate lone parameters")
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
            operation: type[CanonicalOperation], *operands: ParameterOperatable.All
        ) -> ParameterOperatable.All:
            if len(operands) == 1:
                return operands[0]

            return mutator.create_expression(operation, *operands, from_ops=[from_expr])

        retained_ops = [
            op for op in op_with_param.operands if param in find_unique_params(op)
        ]

        moved_ops = [
            op for op in op_with_param.operands if param not in find_unique_params(op)
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

        param_in_lhs = param in find_unique_params(lhs)
        param_in_rhs = param in find_unique_params(rhs)

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
        if try_extract_literal(expr) is None:
            continue

        # TODO why? are we trying to do only arithmetic?
        # Then why not do isinstance(expr, Arithmetic)?
        if BoolSet(True) in expr.operands:
            continue

        unaliased_params = {
            p for p in find_unique_params(expr) if try_extract_literal(p) is None
        }

        # only handle single free var
        if len(unaliased_params) != 1:
            continue

        param = unaliased_params.pop()

        if param in expr.operands and not any(
            op is not param and find_unique_params(op) == {param}
            for op in expr.operands
        ):
            # already isolated
            continue

        if (result := isolate_param(expr, param)) is None:
            continue

        mutator.mutate_expression(expr, operands=result)


@algorithm("Uncorrelated alias fold", destructive=True)
def uncorrelated_alias_fold(mutator: Mutator):
    """
    If an operation contains only operands that are not correlated with each other,
    we can replace the operands with their corresponding literals.
    ```
    op(As), no correlations in As outside of op, len(A is Lit in As) > 0
    -> op(As) is! op(As replaced by corresponding lits)
    ```

    Destructive because relies on missing correlations.
    """

    new_aliases = mutator.get_literal_aliased(new_only=True)

    # bool expr always map to singles
    new_exprs = {k: v for k, v in new_aliases.items() if not is_correlatable_literal(v)}

    for alias in new_exprs.keys():
        exprs = alias.get_operations()
        for expr in exprs:
            assert isinstance(expr, CanonicalOperation)
            # TODO: we can weaken this to not replace correlated operands instead of
            #   skipping the whole expression
            # check if any correlations
            if any(get_correlations(expr)):
                continue

            expr_resolved_operands = map_extract_literals(expr)

            if isinstance(expr, Is) and expr.constrained:
                # TODO: definitely need to do something
                # just not the same what we do with the other types
                continue

            mutator.mutate_expression(
                expr, operands=expr_resolved_operands, soft_mutate=Is
            )


@algorithm("Remove tautologies")
def remove_tautologies(mutator: Mutator):
    """
    A is A -> True
    A ss A -> True
    A >= A, A not lit -> True
    """

    # Also done in literal_folding, but kinda nice to have it here
    # called if_operands_same_make_true

    predicates = mutator.nodes_of_types(
        (Is, IsSubset, GreaterOrEqual), sort_by_depth=True
    )

    for pred in predicates:
        assert isinstance(pred, ConstrainableExpression)
        if len(set(pred.operands)) > 1:
            continue
        if isinstance(pred, GreaterOrEqual) and is_literal(pred.operands[0]):
            continue

        alias_is_literal_and_check_predicate_eval(pred, True, mutator)
