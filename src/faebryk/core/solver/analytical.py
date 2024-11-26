# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from functools import partial
from typing import cast

from faebryk.core.graph import GraphFunctions
from faebryk.core.parameter import (
    Domain,
    Expression,
    GreaterOrEqual,
    Is,
    IsSubset,
    Parameter,
    ParameterOperatable,
    Predicate,
    has_implicit_constraints_recursive,
)
from faebryk.core.solver.literal_folding import fold
from faebryk.core.solver.utils import (
    CanonicalOperation,
    FullyAssociative,
    Mutator,
    alias_is_literal,
    flatten_associative,
    get_constrained_expressions_involved_in,
    is_replacable,
    merge_parameters,
    parameter_ops_eq_classes,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.util import cast_assert, not_none, partition

logger = logging.getLogger(__name__)


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
    exprs = GraphFunctions(mutator.G).nodes_of_type(Expression)
    predicates = {e for e in exprs if isinstance(e, Predicate)}
    exprs.difference_update(predicates)

    p_eq_classes = parameter_ops_eq_classes(mutator.G)

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
        intersected = Quantity_Interval_Disjoint.intersect_all(*literal_subsets)

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

        # don't run on aliased exprs
        if ParameterOperatable.try_get_literal(expr) is not None:
            continue

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


# TODO move into fold_alias
def remove_obvious_tautologies(mutator: Mutator):
    """
    Remove tautologies like:
     - A is A
     - A is B | A or B unconstrained
     - Lit1 is Lit2 | Lit1 and Lit2 are equal literals
    """

    def remove_is(pred_is: Is):
        if len(pred_is.get_operations()) == 0:
            mutator.remove(pred_is)
        else:
            pred_is.alias_is(True)

    def known_unconstrained(po: ParameterOperatable) -> bool:
        no_other_constraints = (
            len(get_constrained_expressions_involved_in(po).difference({pred_is})) == 0
        )
        return no_other_constraints and not po.has_implicit_constraints_recursive()

    is_predicates = GraphFunctions(mutator.G).nodes_of_type(Is)

    for pred_is in ParameterOperatable.sort_by_depth(is_predicates, ascending=True):
        left, right = pred_is.operands
        left_is_literal = not isinstance(left, ParameterOperatable)
        right_is_literal = not isinstance(right, ParameterOperatable)

        if (
            left is right
            or (left_is_literal and right_is_literal and left == right)  # TODO obv eq
            and not has_implicit_constraints_recursive(left)
            and not has_implicit_constraints_recursive(right)
        ):
            # A == A
            # L1 == L2
            remove_is(pred_is)
        elif not (left_is_literal or right_is_literal) and (
            (isinstance(left, Parameter) and known_unconstrained(left))
            or (isinstance(right, Parameter) and known_unconstrained(right))
        ):
            # A == B | A or B unconstrained
            remove_is(pred_is)


def upper_estimation_of_expressions_with_subsets(mutator: Mutator):
    """
    If any operand in an expression has a subset literal, we can add a subset to the expr

    A + B | A alias B ; never happens (after eq classes)
    A + B | B alias [1,5] -> (A + B) , (A + B) subset (A + [1,5])
    A + B | B subset [1,5] -> (A + B) , (A + B) subset (A + [1,5])
    A / B | B alias [1,5] -> (A / B) , (A / B) subset (A / [1,5])
    B / A | B alias [1,5] -> (B / A) , (B / A) subset ([1,5] / A)
    A / B | B alias 0 -> (A / B), (A / B) subset (A / 0)
    A / B | B alias [-1,1] -> (A / B), (A / B) subset (A / [-1,1])
    """

    exprs = GraphFunctions(mutator.G).nodes_of_type(Expression)
    for expr in exprs:
        if isinstance(expr, Predicate):
            continue

        operands = []
        for op in expr.operands:
            if not isinstance(op, ParameterOperatable):
                operands.append(op)
                continue
            subset_lits = op.try_get_literal_subset()
            if subset_lits is None:
                operands.append(op)
                continue
            operands.append(subset_lits)

        # Make new expr with subset literals
        new_expr = type(expr)(*[mutator.get_copy(operand) for operand in operands])
        logger.info(f"Adding upper estimate {expr} subset {new_expr}")
        # Constrain subset on copy of old expr
        cast_assert(Expression, mutator.get_copy(expr)).constrain_subset(new_expr)
