# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from functools import partial
from typing import cast

from faebryk.core.graph import GraphFunctions
from faebryk.core.parameter import (
    Add,
    Divide,
    Domain,
    Expression,
    GreaterOrEqual,
    GreaterThan,
    Is,
    IsSubset,
    IsSuperset,
    LessOrEqual,
    LessThan,
    Multiply,
    Parameter,
    ParameterOperatable,
    Power,
    Predicate,
    Subtract,
    has_implicit_constraints_recursive,
)
from faebryk.core.solver.literal_folding import fold
from faebryk.core.solver.utils import (
    FullyAssociative,
    Mutator,
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
from faebryk.libs.units import quantity
from faebryk.libs.util import not_none, partition

logger = logging.getLogger(__name__)


def convert_inequality_to_subset(mutator: Mutator):
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
            interval = Quantity_Interval(min=lit.max_elem())
        else:
            param = ge.operands[1]
            lit = Quantity_Interval_Disjoint.from_value(ge.operands[0])
            interval = Quantity_Interval(max=lit.min_elem())

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
        alias_class_exprs = [p for p in alias_class_p_ops if isinstance(p, Expression)]

        if len(alias_class_p_ops) <= 1:
            continue

        # TODO non unit/numeric params, i.e. enums, bools

        # single domain
        # TODO check domain for literals
        domain = Domain.get_shared_domain(*(p.domain for p in alias_class_p_ops))

        if alias_class_params:
            # Merge param alias classes
            representative = merge_parameters(alias_class_params)
        else:
            # If not params or lits in class, create a new param as representative
            # for expressions
            representative = Parameter(domain=domain)

        for p in alias_class_params:
            mutator._mutate(p, representative)

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

    params = GraphFunctions(mutator.G).nodes_of_type(Parameter)

    for param in params:
        # TODO we can also propagate is subset from other param: x sub y sub range
        constrained_subset_ops_with_literal = [
            e
            for e in param.get_operations(types=IsSubset)
            if e.constrained
            and ParameterOperatable.try_extract_literal(e.get_other_operand(param))
            is not None
        ]
        if len(constrained_subset_ops_with_literal) <= 1:
            continue

        literal_subsets = [
            not_none(
                ParameterOperatable.try_extract_literal(e.get_other_operand(param))
            )
            for e in constrained_subset_ops_with_literal
        ]
        # intersect
        intersected = Quantity_Interval_Disjoint.intersect_all(*literal_subsets)

        # If not narrower than all operands, skip
        if not all(intersected != lit for lit in literal_subsets):
            continue

        # What we are doing here is mark this predicate as satisfied
        # because another predicate exists that will always imply this one
        for e in constrained_subset_ops_with_literal:
            mutator.mutate_expression(e).alias_is(True)

        mutator.mutate_parameter(param).constrain_subset(intersected)


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


def convert_to_canonical_operations(mutator: Mutator):
    """
    Transforms Sub-Add to Add-Add
    ```
    A - B -> A + (-B)
    A / B -> A * B^-1
    A <= B -> B >= A
    A < B -> B > A
    A superset B -> B subset A

    #TODO: floor/ceil -> round(x -/+ 0.5)
    #TODO: cos(x) -> sin(x + pi/2)
    #TODO: sqrt -> ^-(2^-1)
    #TODO: Logic (xor, and, implies) -> Or & Not
    ```
    """

    MirroredExpressions = [
        (
            Add,
            Subtract,
            lambda operands: [operands[0]]
            + [Multiply(o, quantity(-1)) for o in operands[1:]],
        ),
        (
            Multiply,
            Divide,
            lambda operands: [operands[0]]
            + [Power(o, quantity(-1)) for o in operands[1:]],
        ),
        (
            GreaterOrEqual,
            LessOrEqual,
            lambda operands: list(reversed(operands)),
        ),
        (
            GreaterThan,
            LessThan,
            lambda operands: list(reversed(operands)),
        ),
        (
            IsSubset,
            IsSuperset,
            lambda operands: list(reversed(operands)),
        ),
    ]

    for Target, Convertible, Converter in MirroredExpressions:
        convertible = {e for e in GraphFunctions(mutator.G).nodes_of_type(Convertible)}

        for expr in ParameterOperatable.sort_by_depth(convertible, ascending=True):
            mutator.mutate_expression(
                expr, Converter(expr.operands), expression_factory=Target
            )


def fold_literals(mutator: Mutator):
    exprs = GraphFunctions(mutator.G).nodes_of_type(Expression)

    for expr in ParameterOperatable.sort_by_depth(exprs, ascending=True):
        if mutator.has_been_mutated(expr) or mutator.is_removed(expr):
            continue

        operands = expr.operands
        p_operands, literal_operands = partition(
            lambda o: ParameterOperatable.is_literal(o), operands
        )
        non_replacable_nonconst_ops, replacable_nonconst_ops = partition(
            lambda o: not mutator.has_been_mutated(o), p_operands
        )
        multiplicity = Counter(replacable_nonconst_ops)

        # TODO, obviously_eq offers additional possibilites,
        # must be replacable, no implicit constr
        fold(
            expr,
            literal_operands,
            multiplicity,
            non_replacable_nonconst_ops,
            mutator.repr_map,
            mutator.removed,
        )


def remove_obvious_tautologies(mutator: Mutator):
    """
    Remove tautologies like:
     - A == A
     - A == B | A or B unconstrained
     - Lit1 == Lit2 | Lit1 and Lit2 are equal literals
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
