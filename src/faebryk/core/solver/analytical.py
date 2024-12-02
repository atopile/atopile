# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from functools import partial
from itertools import combinations
from typing import cast

from faebryk.core.graph import GraphFunctions
from faebryk.core.parameter import (
    ConstrainableExpression,
    Domain,
    Expression,
    GreaterOrEqual,
    Is,
    IsSubset,
    Parameter,
    ParameterOperatable,
)
from faebryk.core.solver.literal_folding import fold
from faebryk.core.solver.utils import (
    NON_ASSOCIATIVE_SIMPLIFY,
    S_LOG,
    CanonicalOperation,
    FullyAssociative,
    Mutator,
    alias_is_literal,
    alias_is_literal_and_check_predicate_eval,
    flatten_associative,
    get_constrained_expressions_involved_in,
    is_replacable,
    is_replacable_by_literal,
    merge_parameters,
    try_extract_all_literals,
    try_extract_literal,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import (
    EquivalenceClasses,
    cast_assert,
    groupby,
    not_none,
    partition,
)

logger = logging.getLogger(__name__)

if S_LOG:
    logger.setLevel(logging.DEBUG)


def convert_inequality_with_literal_to_subset(mutator: Mutator):
    """
    A >= 5 -> A in [5, inf)
    5 >= A -> A in (-inf, 5]

    A >= [1, 10] -> A in [10, inf)
    [1, 10] >= A -> A in (-inf, 1]
    """

    ge_exprs = {
        e
        for e in GraphFunctions(mutator.G).nodes_of_type(GreaterOrEqual)
        # Look for expressions with only one non-literal operand
        if len(list(op for op in e.operands if isinstance(op, ParameterOperatable)))
        == 1
    }

    for ge in ParameterOperatable.sort_by_depth(ge_exprs, ascending=True):
        is_left = ge.operands[0] is next(iter(ge.operatable_operands))

        if is_left:
            param = ge.operands[0]
            lit = Quantity_Interval_Disjoint.from_value(ge.operands[1])
            interval = Quantity_Interval_Disjoint(Quantity_Interval(min=lit.max_elem()))
        else:
            param = ge.operands[1]
            lit = Quantity_Interval_Disjoint.from_value(ge.operands[0])
            interval = Quantity_Interval_Disjoint(Quantity_Interval(max=lit.min_elem()))

        mutator.mutate_expression(
            ge,
            operands=[param, interval],
            expression_factory=IsSubset,
        )

    return mutator


def remove_unconstrained(mutator: Mutator):
    """
    Remove all parameteroperables that are not involved in any constrained predicates
    """
    objs = GraphFunctions(mutator.G).nodes_of_type(ParameterOperatable)
    for obj in objs:
        if get_constrained_expressions_involved_in(obj):
            continue
        mutator.remove(obj)


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

    all_exprs = GraphFunctions(mutator.G).nodes_of_type(Expression)
    exprs_by_type = groupby(all_exprs, type)
    full_eq = EquivalenceClasses[Expression](all_exprs)

    for exprs in exprs_by_type.values():
        if len(exprs) <= 1:
            continue
        # TODO use hash to speed up comparisons
        for e1, e2 in combinations(exprs, 2):
            if not full_eq.is_eq(e1, e2) and e1.is_congruent_to(e2):
                full_eq.add_eq(e1, e2)

    repres = {}
    for expr in ParameterOperatable.sort_by_depth(all_exprs, ascending=True):
        eq_class = full_eq.classes[expr]
        if len(eq_class) <= 1:
            continue

        eq_id = id(eq_class)
        if eq_id not in repres:
            logger.debug(f"Remove congruent: {eq_class}")
            representative = mutator.mutate_expression(expr)
            repres[eq_id] = representative

            # propagate constrained & marked true
            if isinstance(representative, ConstrainableExpression):
                eq_class = cast(set[ConstrainableExpression], eq_class)
                representative.constrained = any(e.constrained for e in eq_class)
                if any(mutator.is_predicate_true(e) for e in eq_class):
                    mutator.mark_predicate_true(representative)

        mutator._mutate(expr, repres[eq_id])


def resolve_alias_classes(mutator: Mutator):
    """
    Resolve alias classes
    Ignores literals
    ```
    A alias B
    B alias C
    C alias D + E
    D + E < 5
    -> A,B,C => R, R alias D + E, R < 5

    Careful: Aliases to literals will not be resolved due to loss
    of correlation information
    ```
    """

    # A is B, B is C, D is E, F, G is (A+B)
    # -> [{A, B, C}, {D, E}, {F}, {G, (A+B)}]
    param_ops = GraphFunctions(mutator.G).nodes_of_type(ParameterOperatable)
    full_eq = EquivalenceClasses[ParameterOperatable](param_ops)
    is_exprs = [e for e in GraphFunctions(mutator.G).nodes_of_type(Is) if e.constrained]
    for is_expr in is_exprs:
        full_eq.add_eq(*is_expr.operatable_operands)
    p_eq_classes = full_eq.get()

    # Make new param repre for alias classes
    for eq_class in p_eq_classes:
        if len(eq_class) <= 1:
            continue

        alias_class_p_ops = [p for p in eq_class if isinstance(p, ParameterOperatable)]
        alias_class_params = [p for p in alias_class_p_ops if isinstance(p, Parameter)]
        alias_class_exprs = {p for p in alias_class_p_ops if isinstance(p, Expression)}

        if len(alias_class_p_ops) <= 1:
            continue
        if not alias_class_params:
            continue

        if len(alias_class_params) == 1:
            # check if all in eq_class already aliased
            # Then no need to to create new representative
            iss = alias_class_params[0].get_operations(Is)
            iss_exprs = {
                o
                for e in iss
                for o in e.operatable_operands
                if isinstance(o, Expression)
            }
            if alias_class_exprs.issubset(iss_exprs):
                continue

        # Merge param alias classes
        representative = merge_parameters(alias_class_params)

        for p in alias_class_params:
            mutator._mutate(p, representative)

    for eq_class in p_eq_classes:
        if len(eq_class) <= 1:
            continue
        alias_class_p_ops = [p for p in eq_class if isinstance(p, ParameterOperatable)]
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
            representative = Parameter(domain=domain)

        for e in alias_class_exprs:
            copy_expr = mutator.mutate_expression(e)
            copy_expr.alias_is(representative)
            # DANGER!
            mutator._override_repr(e, representative)

    # remove eq_class Is (for non-literal alias classes)
    removed = {
        e
        for e in GraphFunctions(mutator.G).nodes_of_type(Is)
        if all(mutator.has_been_mutated(operand) for operand in e.operands)
        and not e.get_operations()
    }
    mutator.remove(*removed)


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

    params = GraphFunctions(mutator.G).nodes_of_type(ParameterOperatable)

    for param in ParameterOperatable.sort_by_depth(params, ascending=True):
        # TODO we can also propagate is subset from other param: x sub y sub range
        constrained_subset_ops_with_literal = [
            e
            for e in param.get_operations(types=IsSubset)
            if e.constrained
            and e.operands[0] is param
            and ParameterOperatable.try_extract_literal(e.operands[1]) is not None
        ]
        if len(constrained_subset_ops_with_literal) <= 1:
            continue

        literal_subsets = [
            not_none(ParameterOperatable.try_extract_literal(e.operands[1]))
            for e in constrained_subset_ops_with_literal
        ]
        # intersect
        intersected = P_Set.intersect_all(*literal_subsets)

        # If not narrower than all operands, skip
        if not all(
            intersected != e.operands[1] for e in constrained_subset_ops_with_literal
        ):
            continue

        # What we are doing here is mark this predicate as satisfied
        # because another predicate exists that will always imply this one
        for e in constrained_subset_ops_with_literal:
            # TODO remove e if possible
            alias_is_literal(e, True)

        cast_assert(ParameterOperatable, mutator.get_copy(param)).constrain_subset(
            intersected
        )


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
        set[FullyAssociative],
        GraphFunctions(mutator.G).nodes_of_types(FullyAssociative),
    )
    # get out deepest expr in compressable tree
    root_ops = {e for e in ops if type(e) not in {type(n) for n in e.get_operations()}}

    for expr in ParameterOperatable.sort_by_depth(root_ops, ascending=True):
        res = flatten_associative(expr, partial(is_replacable, mutator.repr_map))
        if not res.destroyed_operations:
            continue

        mutator.remove(*res.destroyed_operations)

        mutator.mutate_expression(
            expr,
            operands=res.extracted_operands,
        )


def fold_literals(mutator: Mutator):
    """
    Tries to do operations on literals or fold expressions.
    - If possible to do literal operation, aliases expr with result.
    - If fold results in new expr, replaces old expr with new one.
    - If fold results in neutralization, returns operand if not literal else alias.

    Examples:
    ```
    Or(True, B) -> alias: True
    Add(A, B, 5, 10) -> replace: Add(A, B, 15)
    Add(10, 15) -> alias: 25
    Not(Not(A)) -> neutralize=replace: A
    ```
    """

    exprs = GraphFunctions(mutator.G).nodes_of_type(Expression)

    for expr in ParameterOperatable.sort_by_depth(exprs, ascending=True):
        if mutator.has_been_mutated(expr) or mutator.is_removed(expr):
            continue

        # TODO
        # A is! 5, A is! Add(10, 2)
        # A ...
        # Add(10, 2) -> A -> 5
        # don't run on aliased exprs
        # if (
        #    not (
        #        not isinstance(expr, ConstrainableExpression)
        #        or expr._solver_evaluates_to_true
        #    )
        #    and ParameterOperatable.try_get_literal(expr) is not None
        # ):
        #    continue

        operands = expr.operands
        # TODO consider extracting instead
        p_operands, literal_operands = partition(
            lambda o: ParameterOperatable.is_literal(o), operands
        )
        p_operands = cast(list[ParameterOperatable], p_operands)
        non_replacable_nonliteral_operands, replacable_nonliteral_operands = partition(
            lambda o: not mutator.has_been_mutated(o), p_operands
        )
        multiplicity = Counter(replacable_nonliteral_operands)

        # TODO, obviously_eq offers additional possibilites,
        # must be replacable, no implicit constr
        fold(
            cast(CanonicalOperation, expr),
            literal_operands=list(literal_operands),
            replacable_nonliteral_operands=multiplicity,
            non_replacable_nonliteral_operands=list(non_replacable_nonliteral_operands),
            mutator=mutator,
        )


def upper_estimation_of_expressions_with_subsets(mutator: Mutator):
    """
    If any operand in an expression has a subset literal, we can add a subset to the expr

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

    exprs = GraphFunctions(mutator.G).nodes_of_type(Expression)
    for expr in exprs:
        # if isinstance(expr, Predicate):
        #    continue

        operands = []
        for op in expr.operands:
            if not isinstance(op, ParameterOperatable):
                operands.append(op)
                continue
            subset_lits = try_extract_literal(op, allow_subset=True)
            if subset_lits is None:
                operands.append(op)
                continue
            operands.append(subset_lits)

        # Make new expr with subset literals
        new_expr = type(expr)(*[mutator.get_copy(operand) for operand in operands])
        # Constrain subset on copy of old expr
        ss = cast_assert(Expression, mutator.get_copy(expr)).constrain_subset(new_expr)
        mutator.mark_predicate_true(ss)


def remove_empty_graphs(mutator: Mutator):
    """
    If there is only one predicate, it can be replaced by True
    If there are no predicates, the graph can be removed
    """

    predicates = [
        p
        for p in GraphFunctions(mutator.G).nodes_of_type(ConstrainableExpression)
        if p.constrained
    ]

    if len(predicates) > 1:
        return

    for p in predicates:
        alias_is_literal_and_check_predicate_eval(p, True, mutator)

    # Never remove predicates
    if predicates and not NON_ASSOCIATIVE_SIMPLIFY:
        return

    mutator.remove(*GraphFunctions(mutator.G).nodes_of_type(ParameterOperatable))


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
    predicates = GraphFunctions(mutator.G).nodes_of_type(ConstrainableExpression)
    for p in predicates:
        if not p.constrained:
            continue
        lits = not_none(try_extract_all_literals(p, accept_partial=True))
        if len(p.operands) - len(lits) <= 1:
            # mutator.mark_predicate_true(p)
            # purely for printing mutating needed
            if not mutator.is_predicate_true(p):
                mutator.mark_predicate_true(
                    cast_assert(ConstrainableExpression, mutator.mutate_expression(p))
                )


def convert_operable_aliased_to_single_into_literal(mutator: Mutator):
    """
    A is ([5]), A + B -> ([5]) + B
    """

    exprs = GraphFunctions(mutator.G).nodes_of_type(Expression)
    for e in ParameterOperatable.sort_by_depth(exprs, ascending=True):
        # TODO I don't fully understand why this is here
        # but is very needed
        if isinstance(e, Is) and e.constrained:
            continue

        if not any(is_replacable_by_literal(op) is not None for op in e.operands):
            continue

        mutator.mutate_expression_with_op_map(
            e,
            operand_mutator=lambda _, op: (
                lit if (lit := is_replacable_by_literal(op)) is not None else op
            ),
        )
