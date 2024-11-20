# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from dataclasses import dataclass
from functools import partial
from typing import Callable, TypeGuard, cast

from faebryk.core.graph import Graph, GraphFunctions
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
    Associative,
    FullyAssociative,
    Mutator,
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
from faebryk.libs.util import partition

logger = logging.getLogger(__name__)


def convert_inequality_to_subset(
    G: Graph,
) -> tuple[Mutator.REPR_MAP, bool]:
    """
    A >= 5 -> A in [5, inf)
    5 >= A -> A in (-inf, 5]
    """

    ge_exprs = {
        e
        for e in GraphFunctions(G).nodes_of_type(GreaterOrEqual)
        # Look for expressions with only one non-literal operand
        if len(e.operatable_operands) == 1
    }

    mutator = Mutator()

    for ge in ParameterOperatable.sort_by_depth(ge_exprs, ascending=True):
        is_left = ge.operands[0] is next(iter(ge.operatable_operands))

        if is_left:
            param = ge.operands[0]
            interval = Quantity_Interval(min=ge.operands[1])
        else:
            param = ge.operands[1]
            interval = Quantity_Interval(max=ge.operands[0])

        mutator.mutate_expression(
            ge,
            operands=[param, interval],
            expression_factory=IsSubset,
        )

    if not mutator.repr_map:
        return Mutator.no_mutations(G), False

    mutator.copy_unmutated(G)

    return mutator.repr_map, True


def remove_unconstrained(
    G: Graph,
) -> tuple[Mutator.REPR_MAP, bool]:
    """
    Remove all parameteroperables that are not involved in any constrained predicates
    """
    mutator = Mutator()

    objs = GraphFunctions(G).nodes_of_type(ParameterOperatable)
    remove = [o for o in objs if not get_constrained_expressions_involved_in(o)]

    if not remove:
        assert not mutator.repr_map
        return Mutator.no_mutations(G), False

    mutator.copy_unmutated(G, exclude_filter=lambda p: p in remove)
    return mutator.repr_map, True


def resolve_alias_classes(
    G: Graph,
) -> tuple[Mutator.REPR_MAP, bool]:
    """
    Resolve alias classes
    Ignores literals
    ```
    A alias B
    B alias C
    C alias D + E
    D + E < 5
    -> A,B,C => R, R alias D + E, R < 5
    ```
    """

    dirty = False
    exprs = GraphFunctions(G).nodes_of_type(Expression)
    predicates = {e for e in exprs if isinstance(e, Predicate)}
    exprs.difference_update(predicates)

    p_eq_classes = parameter_ops_eq_classes(G)

    mutator = Mutator()

    # Make new param repre for alias classes
    for eq_class in p_eq_classes.values():
        if len(eq_class) <= 1:
            continue

        alias_class_p_ops = [p for p in eq_class if isinstance(p, ParameterOperatable)]
        alias_class_params = [p for p in alias_class_p_ops if isinstance(p, Parameter)]
        alias_class_exprs = [p for p in alias_class_p_ops if isinstance(p, Expression)]

        if len(alias_class_p_ops) <= 1:
            continue
        dirty = True

        # TODO non unit/numeric params, i.e. enums, bools

        # single domain
        # TODO check domain for literals
        domain = Domain.get_shared_domain(*(p.domain for p in alias_class_p_ops))

        # Merge param alias classes
        if len(alias_class_params) > 0:
            representative = merge_parameters(alias_class_params)

            for p in alias_class_params:
                mutator._mutate(p, representative)
        # If not params in class, create a new param as representative for expressions
        else:
            representative = Parameter(domain=domain)

        for e in alias_class_exprs:
            copy_expr = mutator.mutate_expression(e)
            # TODO make sure this makes sense
            mutator.repr_map[e] = representative
            copy_expr.alias_is(representative)

    if not dirty:
        assert not mutator.repr_map
        return Mutator.no_mutations(G), dirty

    # remove eq_class Is
    removed = {
        e
        for e in GraphFunctions(G).nodes_of_type(Is)
        if all(mutator.has_been_mutated(operand) for operand in e.operands)
    }
    mutator.copy_unmutated(G, exclude_filter=lambda p: p in removed)

    return mutator.repr_map, dirty


def merge_intersect_subsets(
    G: Graph,
) -> tuple[Mutator.REPR_MAP, bool]:
    """
    A subset L1
    A subset L2
    -> A subset (L1 & L2)

    x = A subset L1
    y = A subset L2
    Z = x and y -> Z = x & y
    -> A subset (L1 & L2)
    """

    params = GraphFunctions(G).nodes_of_type(Parameter)
    mutator = Mutator()

    for param in params:
        # TODO we can also propagate is subset from other param: x sub y sub range
        constrained_subset_ops_with_literal = [
            e
            for e in param.get_operations(types=IsSubset)
            if e.constrained and Parameter.is_literal(e.get_other_operand(param))
        ]
        if len(constrained_subset_ops_with_literal) <= 1:
            continue

        literal_subsets = [
            e.get_other_operand(param) for e in constrained_subset_ops_with_literal
        ]
        # intersect
        intersected = Quantity_Interval_Disjoint.from_value(literal_subsets[0])
        for s in literal_subsets[1:]:
            intersected &= Quantity_Interval_Disjoint.from_value(s)

        # TODO this should be somewhere else
        # What we are doing here is mark this predicate as satisfied
        # because another predicate exists that will always imply this one
        for e in constrained_subset_ops_with_literal:
            mutator._mutate(e, True)

        mutator.mutate_parameter(param).constrain_subset(intersected)

    dirty = len(mutator.repr_map) > 0
    if not dirty:
        assert not mutator.repr_map
        return Mutator.no_mutations(G), False

    mutator.copy_unmutated(G)

    return mutator.repr_map, dirty


def flatten_associative[T: Associative](
    to_flatten: T,  # type: ignore
    check_destructable: Callable[[Expression, Expression], bool],
):
    """
    Recursively extract operands from nested expressions of the same type.

    ```
    (A + B) + C + (D + E)
       Y    Z   X    W
    flatten(Z) -> flatten(Y) + [C] + flatten(X)
      flatten(Y) -> [A, B]
      flatten(X) -> flatten(W) + [D, E]
      flatten(W) -> [C]
    -> [A, B, C, D, E] = extracted operands
    -> {Z, X, W, Y} = destroyed operations
    ```

    Note: `W` flattens only for right associative operations

    Args:
    - check_destructable(expr, parent_expr): function to check if an expression is
        allowed to be flattened (=destructed)
    """

    @dataclass
    class Result[T2]:
        extracted_operands: list[ParameterOperatable.All]
        """
        Extracted operands
        """
        destroyed_operations: set[T2]
        """
        ParameterOperables that got flattened and thus are not used anymore
        """

    out = Result[T](
        extracted_operands=[],
        destroyed_operations=set(),
    )

    def can_be_flattened(o: ParameterOperatable.All) -> TypeGuard[T]:
        if not isinstance(to_flatten, Associative):
            return False
        if not isinstance(to_flatten, FullyAssociative):
            if to_flatten.operands[0] is not o:
                return False
        return type(o) is type(to_flatten) and check_destructable(o, to_flatten)

    non_compressible_operands, nested_compressible_operations = partition(
        can_be_flattened,
        to_flatten.operands,
    )
    out.extracted_operands.extend(non_compressible_operands)

    nested_extracted_operands = []
    for nested_to_flatten in nested_compressible_operations:
        out.destroyed_operations.add(nested_to_flatten)

        res = flatten_associative(nested_to_flatten, check_destructable)
        nested_extracted_operands += res.extracted_operands
        out.destroyed_operations.update(res.destroyed_operations)

    if len(nested_extracted_operands) > 0 and logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"FLATTENED {type(to_flatten).__name__} {to_flatten} -> {nested_extracted_operands}"
        )

    out.extracted_operands.extend(nested_extracted_operands)

    return out


def compress_associative(
    G: Graph,
) -> tuple[Mutator.REPR_MAP, bool]:
    """
    Makes
    ```
    (A + B) + (C + (D + E))
       Y    Z    X    W
    -> +(A,B,C,D,E)
       Z'

    for +, *, and, or, &, |, ^
    """

    dirty = False
    ops = cast(
        set[FullyAssociative],
        GraphFunctions(G).nodes_of_types(FullyAssociative),
    )
    # get out deepest expr in compressable tree
    root_ops = {e for e in ops if type(e) not in {type(n) for n in e.get_operations()}}

    mutator = Mutator()
    removed = set()

    for expr in ParameterOperatable.sort_by_depth(root_ops, ascending=True):
        res = flatten_associative(expr, partial(is_replacable, mutator.repr_map))
        if not res.destroyed_operations:
            continue

        removed |= res.destroyed_operations
        dirty = True

        mutator.mutate_expression(
            expr,
            operands=res.extracted_operands,
        )

    if not dirty:
        assert not mutator.repr_map
        return Mutator.no_mutations(G), False

    # copy other param ops
    mutator.copy_unmutated(G, exclude_filter=lambda p: p in removed)

    return mutator.repr_map, dirty


def convert_to_canonical_operations(
    G: Graph,
) -> tuple[Mutator.REPR_MAP, bool]:
    """
    Transforms Sub-Add to Add-Add
    ```
    A - B -> A + (-B)
    A / B -> A * B^-1
    A <= B -> B >= A
    A < B -> B > A
    A superset B -> B subset A
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

    mutator = Mutator()

    for Target, Convertible, Converter in MirroredExpressions:
        convertible = {e for e in GraphFunctions(G).nodes_of_type(Convertible)}

        for expr in ParameterOperatable.sort_by_depth(convertible, ascending=True):
            mutator.mutate_expression(
                expr, Converter(expr.operands), expression_factory=Target
            )

    dirty = len(mutator.repr_map) > 0
    if not dirty:
        return Mutator.no_mutations(G), False

    mutator.copy_unmutated(G)

    return mutator.repr_map, dirty


def fold_literals(
    G: Graph,
) -> tuple[Mutator.REPR_MAP, bool]:
    dirty = False
    exprs = GraphFunctions(G).nodes_of_type(Expression)

    mutator = Mutator()
    removed = set()

    for expr in ParameterOperatable.sort_by_depth(exprs, ascending=True):
        if mutator.has_been_mutated(expr) or expr in removed:
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
        dirty |= fold(
            expr,
            literal_operands,
            multiplicity,
            non_replacable_nonconst_ops,
            mutator.repr_map,
            removed,
        )

    if not dirty:
        return Mutator.no_mutations(G), False

    mutator.copy_unmutated(G, exclude_filter=lambda p: p in removed)

    return mutator.repr_map, dirty


def remove_obvious_tautologies(
    G: Graph,
) -> tuple[Mutator.REPR_MAP, bool]:
    """
    Remove tautologies like:
     - A == A
     - A == B | A or B unconstrained
     - Lit1 == Lit2 | Lit1 and Lit2 are equal literals
    """

    mutator = Mutator()

    removed = set()

    def remove_is(pred_is: Is):
        if len(pred_is.get_operations()) == 0:
            removed.add(pred_is)
        else:
            mutator._mutate(pred_is, True)

    def known_unconstrained(po: ParameterOperatable) -> bool:
        no_other_constraints = (
            len(get_constrained_expressions_involved_in(po).difference({pred_is})) == 0
        )
        return no_other_constraints and not po.has_implicit_constraints_recursive()

    is_predicates = GraphFunctions(G).nodes_of_type(Is)

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
        elif (
            isinstance(left, Parameter)
            and known_unconstrained(left)
            or isinstance(right, Parameter)
            and known_unconstrained(right)
        ):
            # A == B | A or B unconstrained
            remove_is(pred_is)

            # TODO remove hack
            # This is here so superranges can see this literal
            if left_is_literal:
                mutator._mutate(right, left)
            elif right_is_literal:
                mutator._mutate(left, right)

    dirty = len(removed) > 0 or len(mutator.repr_map) > 0
    if not dirty:
        return Mutator.no_mutations(G), False

    mutator.copy_unmutated(G, exclude_filter=lambda p: p in removed)

    return mutator.repr_map, dirty
