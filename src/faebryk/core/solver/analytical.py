# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


# FIXME: remove this
# ignore ruff errors in this file:
# ruff: noqa: F821, F841

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from functools import partial
from statistics import median
from typing import Callable, TypeGuard, cast

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.parameter import (
    Add,
    And,
    Divide,
    Domain,
    Expression,
    GreaterOrEqual,
    Is,
    IsSubset,
    LessOrEqual,
    Multiply,
    Or,
    Parameter,
    ParameterOperatable,
    Power,
    Predicate,
    Subtract,
    has_implicit_constraints_recursive,
)
from faebryk.core.solver.utils import (
    Associative,
    FullyAssociative,
    Mutator,
    get_constrained_expressions_involved_in,
    is_replacable,
    parameter_dependency_classes,
    parameter_ops_alias_classes,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.units import HasUnit, dimensionless
from faebryk.libs.util import partition

logger = logging.getLogger(__name__)


def inequality_to_set_op(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable.All], bool]:
    param_ops = cast(
        set[LessOrEqual | GreaterOrEqual],
        GraphFunctions(G).nodes_of_types((LessOrEqual, GreaterOrEqual)),
    )

    dirty = False
    repr_map: dict[ParameterOperatable, ParameterOperatable.All] = {}

    for po in cast(
        Iterable[LessOrEqual | GreaterOrEqual],
        ParameterOperatable.sort_by_depth(param_ops, ascending=True),
    ):

        def get_literal(
            po: ParameterOperatable.All, default: float
        ) -> tuple[ParameterOperatable.Literal, bool]:
            if not isinstance(po, ParameterOperatable):
                return po, True
            return default * HasUnit.get_units_or_dimensionless(po), False

        if len(po.operatable_operands) == 1:
            if isinstance(po, LessOrEqual):
                left, l_literal = get_literal(po.operands[0], float("-inf"))
                right, r_literal = get_literal(po.operands[1], float("inf"))
            elif isinstance(po, GreaterOrEqual):
                left, l_literal = get_literal(po.operands[1], float("-inf"))
                right, r_literal = get_literal(po.operands[0], float("inf"))
            copy_po = cast(
                ParameterOperatable,
                Mutator.copy_operand_recursively(
                    po.operatable_operands.pop(), repr_map
                ),
            )
            subset = copy_po.operation_is_subset(Quantity_Interval(left, right))
            if po.constrained:
                subset.constrain()
            dirty = True
            repr_map[po] = subset

    for p in GraphFunctions(G).nodes_of_type(ParameterOperatable):
        if p not in repr_map:
            Mutator.copy_operand_recursively(p, repr_map)

    return repr_map, dirty


def resolve_alias_classes(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable.All], bool]:
    dirty = False
    params_ops = [
        p
        for p in GraphFunctions(G).nodes_of_type(ParameterOperatable)
        if get_constrained_expressions_involved_in(p)
    ]
    exprs = GraphFunctions(G).nodes_of_type(Expression)
    predicates = {e for e in exprs if isinstance(e, Predicate)}
    exprs.difference_update(predicates)
    exprs = {e for e in exprs if get_constrained_expressions_involved_in(e)}

    p_alias_classes = parameter_ops_alias_classes(G)
    dependency_classes = parameter_dependency_classes(G)

    infostr = (
        f"{len(params_ops)} parametersoperable"
        f"\n    {len(p_alias_classes)} alias classes"
        f"\n    {len(dependency_classes)} dependency classes"
        "\n"
    )
    logger.info(infostr)

    repr_map: dict[ParameterOperatable, ParameterOperatable.All] = {}

    # Make new param repre for alias classes
    for param_op in ParameterOperatable.sort_by_depth(params_ops, ascending=True):
        if param_op in repr_map or param_op not in p_alias_classes:
            continue

        alias_class = p_alias_classes[param_op]

        # TODO short-cut if len() == 1 ?
        param_alias_class = [p for p in alias_class if isinstance(p, Parameter)]
        expr_alias_class = [p for p in alias_class if isinstance(p, Expression)]

        # TODO non unit/numeric params, i.e. enums, bools
        # is dimensionless sufficient?
        # single unit
        unit_candidates = {HasUnit.get_units_or_dimensionless(p) for p in alias_class}
        if len(unit_candidates) > 1:
            raise ValueError("Incompatible units in alias class")
        # single domain
        domain = Domain.get_shared_domain(
            *(
                # TODO get domain for constants
                p.domain
                for p in alias_class
                if isinstance(p, ParameterOperatable)
            )
        )

        representative = None

        if len(param_alias_class) > 0:
            dirty |= len(param_alias_class) > 1

            # intersect ranges
            within_intervals = {
                p.within for p in param_alias_class if p.within is not None
            }
            within = None
            if within_intervals:
                within = Quantity_Interval_Disjoint.op_intersect_intervals(
                    *within_intervals
                )

            # heuristic:
            # intersect soft sets
            soft_sets = {
                p.soft_set for p in param_alias_class if p.soft_set is not None
            }
            soft_set = None
            if soft_sets:
                soft_set = Quantity_Interval_Disjoint.op_intersect_intervals(*soft_sets)

            # heuristic:
            # get median
            guesses = {p.guess for p in param_alias_class if p.guess is not None}
            guess = None
            if guesses:
                guess = median(guesses)  # type: ignore

            # heuristic:
            # max tolerance guess
            tolerance_guesses = {
                p.tolerance_guess
                for p in param_alias_class
                if p.tolerance_guess is not None
            }
            tolerance_guess = None
            if tolerance_guesses:
                tolerance_guess = max(tolerance_guesses)

            likely_constrained = any(p.likely_constrained for p in param_alias_class)

            representative = Parameter(
                domain=domain,
                units=unit_candidates.pop(),
                within=within,
                soft_set=soft_set,
                guess=guess,
                tolerance_guess=tolerance_guess,
                likely_constrained=likely_constrained,
            )
            repr_map.update({p: representative for p in param_alias_class})
        elif len(expr_alias_class) > 1:
            dirty = True
            representative = Parameter(domain=domain, units=unit_candidates.pop())

        if representative is not None:
            for e in expr_alias_class:
                copy_expr = Mutator.copy_operand_recursively(e, repr_map)
                repr_map[e] = (
                    representative  # copy_expr TODO make sure this makes sense
                )
                Is(copy_expr, representative).constrain()

    # replace parameters in expressions and predicates
    for expr in cast(
        Iterable[Expression],
        ParameterOperatable.sort_by_depth(exprs | predicates, ascending=True),
    ):
        # filter alias class Is
        if isinstance(expr, Is) and all(o in repr_map for o in expr.operands):
            continue

        assert all(
            o in repr_map or not isinstance(o, ParameterOperatable)
            for o in expr.operands
        )
        repr_map[expr] = Mutator.copy_operand_recursively(expr, repr_map)

    return repr_map, dirty


def subset_of_literal(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable.All], bool]:
    dirty = False
    params = GraphFunctions(G).nodes_of_type(Parameter)
    removed = set()
    repr_map: dict[ParameterOperatable, ParameterOperatable.All] = {}

    mutator = Mutator(repr_map)

    for param in params:
        # TODO we can also propagate is subset from other param: x sub y sub range
        is_subsets = [
            e
            for e in param.get_operations()
            if isinstance(e, IsSubset)
            # FIXME should just be constrained ones, then considere which ones
            # can be removed
            and len(e.get_operations()) == 0
            and not isinstance(e.get_other_operand(param), ParameterOperatable)
        ]
        if len(is_subsets) > 1:
            other_sets = [e.get_other_operand(param) for e in is_subsets]
            intersected = Quantity_Interval_Disjoint(other_sets[0])
            for s in other_sets[1:]:
                intersected = intersected & Quantity_Interval_Disjoint(s)
            removed.update(is_subsets)
            new_param = mutator.mutate_parameter(param)
            new_param.constrain_subset(intersected)
            dirty = True
        else:
            mutator.mutate_parameter(param)

    exprs = (
        ParameterOperatable.sort_by_depth(  # TODO, do we need the sort here? same above
            (
                p
                for p in GraphFunctions(G).nodes_of_type(Expression)
                if p not in repr_map and p not in removed
            ),
            ascending=True,
        )
    )
    for expr in exprs:
        Mutator.copy_operand_recursively(expr, repr_map)

    return repr_map, dirty


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


def compress_fully_associative(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable.All], bool]:
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
        removed.update(res.destroyed_operations)
        dirty = True
        copy_operands = [
            mutator._copy_operand_recursively(o) for o in res.extracted_operands
        ]

        mutator.mutate_expression(
            expr,
            *copy_operands,
        )

    # copy other param ops
    other_param_op = ParameterOperatable.sort_by_depth(
        (
            p
            for p in GraphFunctions(G).nodes_of_type(ParameterOperatable)
            if not mutator.has_been_mutated(p) and p not in removed
        ),
        ascending=True,
    )
    for o in other_param_op:
        mutator._copy_operand_recursively(o)

    return mutator.repr_map, dirty


def compress_associative_sub(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable.All], bool]:
    logger.info("Compressing Subtracts")
    dirty = False
    subs = cast(set[Subtract], GraphFunctions(G).nodes_of_type(Subtract))
    # get out deepest expr in compressable tree
    parent_subs = {
        e for e in subs if type(e) not in {type(n) for n in e.get_operations()}
    }

    removed = set()
    repr_map: dict[ParameterOperatable, ParameterOperatable.All] = {}

    for expr in cast(
        Iterable[Subtract],
        ParameterOperatable.sort_by_depth(parent_subs, ascending=True),
    ):
        res = flatten_associative(expr, partial(is_replacable, repr_map))

        if (
            isinstance(minuend, Add)
            and is_replacable(repr_map, minuend, expr)
            and len(const_subtrahends) > 0
        ):
            copy_minuend = Add(
                *(
                    Mutator.copy_operand_recursively(s, repr_map)
                    for s in minuend.operands
                ),
                *(-1 * c for c in const_subtrahends),
            )
            repr_map[expr] = copy_minuend
            const_subtrahends = []
            sub_dirty = True
        elif sub_dirty:
            copy_minuend = Mutator.copy_operand_recursively(minuend, repr_map)
        if sub_dirty:
            dirty = True
            copy_subtrahends = [
                Mutator.copy_operand_recursively(s, repr_map)
                for s in nonconst_subtrahends + const_subtrahends
            ]
            if len(copy_subtrahends) > 0:
                new_expr = Subtract(
                    copy_minuend,
                    Add(*copy_subtrahends),
                )
            else:
                new_expr = copy_minuend
                removed.add(expr)
            repr_map[expr] = new_expr
            logger.info(f"REPRMAP {expr} -> {new_expr}")

    # copy other param ops
    other_param_op = ParameterOperatable.sort_by_depth(
        (
            p
            for p in GraphFunctions(G).nodes_of_type(ParameterOperatable)
            if p not in repr_map and p not in removed
        ),
        ascending=True,
    )
    for o in other_param_op:
        copy_o = Mutator.copy_operand_recursively(o, repr_map)
        logger.info(f"REMAINING {o} -> {copy_o}")
        repr_map[o] = copy_o

    return repr_map, dirty


def compress_expressions(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable.All], bool]:
    dirty = False
    exprs = cast(set[Expression], GraphFunctions(G).nodes_of_type(Expression))

    repr_map: dict[ParameterOperatable, ParameterOperatable.All] = {}
    removed = set()

    for expr in cast(
        Iterable[Expression],
        ParameterOperatable.sort_by_depth(exprs, ascending=True),
    ):
        if expr in repr_map or expr in removed:
            continue

        operands = expr.operands
        const_ops, nonconst_ops = partition(
            lambda o: isinstance(o, ParameterOperatable), operands
        )
        non_replacable_nonconst_ops, replacable_nonconst_ops = partition(
            lambda o: o not in repr_map, nonconst_ops
        )
        # TODO, obviously_eq offers additional possibilites,
        # must be replacable, no implicit constr
        multiplicity = {}
        for n in replacable_nonconst_ops:
            if n in multiplicity:
                multiplicity[n] += 1
            else:
                multiplicity[n] = 1

        if isinstance(expr, Add):
            try:
                const_sum = [next(const_ops)]
                for c in const_ops:
                    dirty = True
                    const_sum[0] += c
                # TODO make work with all the types
                if const_sum[0] == 0 * expr.units:
                    dirty = True
                    const_sum = []
            except StopIteration:
                const_sum = []
            if any(m > 1 for m in multiplicity.values()):
                dirty = True
            if dirty:
                copied = {
                    n: Mutator.copy_operand_recursively(n, repr_map)
                    for n in multiplicity
                }
                nonconst_prod = [
                    Multiply(copied[n], m * dimensionless) if m > 1 else copied[n]
                    for n, m in multiplicity.items()
                ]
                new_operands = [
                    *nonconst_prod,
                    *const_sum,
                    *(
                        Mutator.copy_operand_recursively(o, repr_map)
                        for o in non_replacable_nonconst_ops
                    ),
                ]
                if len(new_operands) > 1:
                    new_expr = Add(*new_operands)
                elif len(new_operands) == 1:
                    new_expr = new_operands[0]
                    removed.add(expr)
                else:
                    raise ValueError("No operands, should not happen")
                repr_map[expr] = new_expr

        elif isinstance(expr, Or):
            const_op_list = list(const_ops)
            if any(not isinstance(o, bool) for o in const_op_list):
                raise ValueError("Or with non-boolean operands")
            if any(o for o in const_op_list):
                dirty = True
                repr_map[expr] = True
                removed.add(expr)
            elif len(const_op_list) > 0 or any(m > 1 for m in multiplicity.values()):
                new_operands = [
                    *(
                        Mutator.copy_operand_recursively(o, repr_map)
                        for o in multiplicity
                    ),
                    *(
                        Mutator.copy_operand_recursively(o, repr_map)
                        for o in non_replacable_nonconst_ops
                    ),
                ]
                if len(new_operands) > 1:
                    new_expr = Or(*new_operands)
                elif len(new_operands) == 1:
                    new_expr = new_operands[0]
                    removed.add(expr)
                else:
                    new_expr = False
                repr_map[expr] = new_expr

        elif isinstance(expr, And):
            const_op_list = list(const_ops)
            if any(not isinstance(o, bool) for o in const_op_list):
                raise ValueError("Or with non-boolean operands")
            if any(not o for o in const_op_list):
                dirty = True
                repr_map[expr] = False
                removed.add(expr)
            elif len(const_op_list) > 0 or any(m > 1 for m in multiplicity.values()):
                new_operands = [
                    *(
                        Mutator.copy_operand_recursively(o, repr_map)
                        for o in multiplicity
                    ),
                    *(
                        Mutator.copy_operand_recursively(o, repr_map)
                        for o in non_replacable_nonconst_ops
                    ),
                ]
                if len(new_operands) > 1:
                    new_expr = And(*new_operands)
                elif len(new_operands) == 1:
                    new_expr = new_operands[0]
                    removed.add(expr)
                else:
                    new_expr = True
                repr_map[expr] = new_expr

        elif isinstance(expr, Multiply):
            try:
                const_prod = [next(const_ops)]
                for c in const_ops:
                    dirty = True
                    const_prod[0] *= c
                if (
                    const_prod[0] == 1 * dimensionless
                ):  # TODO make work with all the types
                    dirty = True
                    const_prod = []
            except StopIteration:
                const_prod = []
            if (
                len(const_prod) == 1 and const_prod[0].magnitude == 0
            ):  # TODO make work with all the types
                dirty = True
                repr_map[expr] = 0 * expr.units
            else:
                if any(m > 1 for m in multiplicity.values()):
                    dirty = True
                if dirty:
                    copied = {
                        n: Mutator.copy_operand_recursively(n, repr_map)
                        for n in multiplicity
                    }
                    nonconst_power = [
                        Power(copied[n], m * dimensionless) if m > 1 else copied[n]
                        for n, m in multiplicity.items()
                    ]
                    new_operands = [
                        *nonconst_power,
                        *const_prod,
                        *(
                            Mutator.copy_operand_recursively(o, repr_map)
                            for o in non_replacable_nonconst_ops
                        ),
                    ]
                    if len(new_operands) > 1:
                        new_expr = Multiply(*new_operands)
                    elif len(new_operands) == 1:
                        new_expr = new_operands[0]
                        removed.add(expr)
                    else:
                        raise ValueError("No operands, should not happen")
                    repr_map[expr] = new_expr
        elif isinstance(expr, Subtract):
            if sum(1 for _ in const_ops) == 2:
                dirty = True
                repr_map[expr] = expr.operands[0] - expr.operands[1]
                removed.add(expr)
            elif expr.operands[0] is expr.operands[1]:  # TODO obv eq, replacable
                dirty = True
                repr_map[expr] = 0 * expr.units
                removed.add(expr)
            elif expr.operands[1] == 0 * expr.operands[1].units:
                dirty = True
                repr_map[expr.operands[0]] = repr_map.get(
                    expr.operands[0],
                    Mutator.copy_operand_recursively(expr.operands[0], repr_map),
                )
                repr_map[expr] = repr_map[expr.operands[0]]
                removed.add(expr)
            else:
                repr_map[expr] = Mutator.copy_operand_recursively(expr, repr_map)
        elif isinstance(expr, Divide):
            if sum(1 for _ in const_ops) == 2:
                if not expr.operands[1].magnitude == 0:
                    dirty = True
                    repr_map[expr] = expr.operands[0] / expr.operands[1]
                    removed.add(expr)
                else:
                    # no valid solution but might not matter e.g. [phi(a,b,...)
                    # OR a/0 == b]
                    repr_map[expr] = Mutator.copy_operand_recursively(expr, repr_map)
            elif expr.operands[1] is expr.operands[0]:  # TODO obv eq, replacable
                dirty = True
                repr_map[expr] = 1 * dimensionless
                removed.add(expr)
            elif expr.operands[1] == 1 * expr.operands[1].units:
                dirty = True
                repr_map[expr.operands[0]] = repr_map.get(
                    expr.operands[0],
                    Mutator.copy_operand_recursively(expr.operands[0], repr_map),
                )
                repr_map[expr] = repr_map[expr.operands[0]]
                removed.add(expr)
            else:
                repr_map[expr] = Mutator.copy_operand_recursively(expr, repr_map)
        else:
            repr_map[expr] = Mutator.copy_operand_recursively(expr, repr_map)

    other_param_op = (
        ParameterOperatable.sort_by_depth(  # TODO, do we need the sort here? same above
            (
                p
                for p in GraphFunctions(G).nodes_of_type(ParameterOperatable)
                if p not in repr_map and p not in removed
            ),
            ascending=True,
        )
    )
    for o in other_param_op:
        Mutator.copy_operand_recursively(o, repr_map)

    return {
        k: v for k, v in repr_map.items() if isinstance(v, ParameterOperatable)
    }, dirty


def remove_obvious_tautologies(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable.All], bool]:
    repr_map = {}
    removed = set()
    dirty = False

    def remove_is(pred_is: Is):
        if len(pred_is.get_operations()) == 0:
            removed.add(pred_is)
        else:
            repr_map[pred_is] = True
        nonlocal dirty
        dirty = True

    def known_unconstrained(po: ParameterOperatable) -> bool:
        no_other_constraints = (
            len(get_constrained_expressions_involved_in(po).difference({pred_is})) == 0
        )
        return no_other_constraints and not po.has_implicit_constraints_recursive()

    for pred_is in ParameterOperatable.sort_by_depth(
        GraphFunctions(G).nodes_of_type(Is), ascending=True
    ):
        pred_is = cast(Is, pred_is)
        left = pred_is.operands[0]
        right = pred_is.operands[1]
        left_const = not isinstance(left, ParameterOperatable)
        right_const = not isinstance(right, ParameterOperatable)
        if (
            left is right
            or (left_const and right_const and left == right)  # TODO obv eq
            and not has_implicit_constraints_recursive(left)
            and not has_implicit_constraints_recursive(right)
        ):
            remove_is(pred_is)
        elif (
            isinstance(left, Parameter)
            and known_unconstrained(left)
            or isinstance(right, Parameter)
            and known_unconstrained(right)
        ):
            remove_is(pred_is)
    for p in GraphFunctions(G).nodes_of_type(ParameterOperatable):
        if p not in removed and p not in repr_map:
            repr_map[p] = Mutator.copy_operand_recursively(p, repr_map)
    return repr_map, dirty
