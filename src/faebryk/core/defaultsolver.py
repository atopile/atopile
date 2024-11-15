# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections import defaultdict
from collections.abc import Iterable
from statistics import median
from typing import Any, cast

from more_itertools import partition

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.graphinterface import GraphInterfaceSelf
from faebryk.core.parameter import (
    Add,
    Arithmetic,
    ConstrainableExpression,
    Divide,
    Expression,
    Is,
    IsSubset,
    Multiply,
    Parameter,
    ParameterOperatable,
    Power,
    Predicate,
    Subtract,
    has_implicit_constraints_recursive,
)
from faebryk.core.solver import Solver
from faebryk.libs.sets import Range, Ranges
from faebryk.libs.units import HasUnit, Quantity, dimensionless
from faebryk.libs.util import EquivalenceClasses, unique_ref

logger = logging.getLogger(__name__)


def debug_print(repr_map: dict[ParameterOperatable, ParameterOperatable]):
    import sys

    if getattr(sys, "gettrace", lambda: None)():
        log = print
    else:
        log = logger.info
    for s, d in repr_map.items():
        if isinstance(d, Expression):
            if isinstance(s, Expression):
                log(f"{s}[{s.operands}] -> {d}[{d.operands} | G {d.get_graph()!r}]")
            else:
                log(f"{s} -> {d}[{d.operands} | G {d.get_graph()!r}]")
        else:
            log(f"{s} -> {d} | G {d.get_graph()!r}")
    graphs = unique_ref(p.get_graph() for p in repr_map.values())
    log(f"{len(graphs)} graphs")


def parameter_ops_alias_classes(
    G: Graph,
) -> dict[ParameterOperatable, set[ParameterOperatable]]:
    # TODO just get passed
    param_ops = {
        p
        for p in GraphFunctions(G).nodes_of_type(ParameterOperatable)
        if get_constrained_predicates_involved_in(p)
    }.difference(GraphFunctions(G).nodes_of_type(Predicate))
    full_eq = EquivalenceClasses[ParameterOperatable](param_ops)

    is_exprs = [e for e in GraphFunctions(G).nodes_of_type(Is) if e.constrained]

    for is_expr in is_exprs:
        full_eq.add_eq(*is_expr.operands)

    obvious_eq = defaultdict(list)
    for p in param_ops:
        obvious_eq[p.obviously_eq_hash()].append(p)
    logger.info(f"obvious eq: {obvious_eq}")

    for candidates in obvious_eq.values():
        if len(candidates) > 1:
            logger.debug(f"#obvious eq candidates: {len(candidates)}")
            for i, p in enumerate(candidates):
                for q in candidates[:i]:
                    if p.obviously_eq(q):
                        full_eq.add_eq(p, q)
                        break
    return full_eq.classes


def get_params_for_expr(expr: Expression) -> set[Parameter]:
    param_ops = {op for op in expr.operatable_operands if isinstance(op, Parameter)}
    expr_ops = {op for op in expr.operatable_operands if isinstance(op, Expression)}

    return param_ops | {op for e in expr_ops for op in get_params_for_expr(e)}


def get_constrained_predicates_involved_in(
    p: ParameterOperatable,
) -> set[Predicate]:
    # p.self -> p.operated_on -> e1.operates_on -> e1.self
    dependants = p.bfs_node(
        lambda path: isinstance(path[-1].node, ParameterOperatable)
        and (
            # self
            isinstance(path[-1], GraphInterfaceSelf)
            # operated on
            or path[-1].node.operated_on is path[-1]
            # operated on -> operates on
            or (
                len(path) >= 2
                and isinstance(path[-2].node, ParameterOperatable)
                and path[-2].node.operated_on is path[-2]
                and isinstance(path[-1].node, Expression)
                and path[-1].node.operates_on is path[-1]
            )
        )
    )
    res = {p for p in dependants if isinstance(p, Predicate) and p.constrained}
    return res


def parameter_dependency_classes(G: Graph) -> list[set[Parameter]]:
    # TODO just get passed
    params = [
        p
        for p in GraphFunctions(G).nodes_of_type(Parameter)
        if get_constrained_predicates_involved_in(p)
    ]

    related = EquivalenceClasses[Parameter](params)

    eq_exprs = [e for e in GraphFunctions(G).nodes_of_type(Predicate) if e.constrained]

    for eq_expr in eq_exprs:
        params = get_params_for_expr(eq_expr)
        related.add_eq(*params)

    return related.get()


# TODO make part of Expression class
def create_new_expr(
    old_expr: Expression, *operands: ParameterOperatable.All
) -> Expression:
    new_expr = type(old_expr)(*operands)
    for op in operands:
        if isinstance(op, ParameterOperatable):
            assert op.get_graph() == new_expr.get_graph()
    if isinstance(old_expr, ConstrainableExpression):
        cast(ConstrainableExpression, new_expr).constrained = old_expr.constrained
    return new_expr


def copy_param(p: Parameter) -> Parameter:
    return Parameter(
        units=p.units,
        within=p.within,
        domain=p.domain,
        soft_set=p.soft_set,
        guess=p.guess,
        tolerance_guess=p.tolerance_guess,
        likely_constrained=p.likely_constrained,
    )


def copy_operand_recursively(
    o: ParameterOperatable.All, repr_map: dict[ParameterOperatable, ParameterOperatable]
) -> ParameterOperatable.All:
    if o in repr_map:
        return repr_map[o]
    if isinstance(o, Expression):
        new_ops = []
        for op in o.operands:
            new_op = copy_operand_recursively(op, repr_map)
            if isinstance(op, ParameterOperatable):
                repr_map[op] = new_op
            new_ops.append(new_op)
        expr = create_new_expr(o, *new_ops)
        repr_map[o] = expr
        return expr
    elif isinstance(o, Parameter):
        param = copy_param(o)
        repr_map[o] = param
        return param
    else:
        return o


# units -> base units (dimensionless)
# within -> constrain is subset
# scalar to single
def normalize_graph(G: Graph) -> dict[ParameterOperatable, ParameterOperatable]:
    def set_to_base_units(s: Ranges | Range | None) -> Ranges | Range | None:
        if s is None:
            return None
        if isinstance(s, Ranges):
            return Ranges._from_ranges(s._ranges, dimensionless)
        return Range._from_range(s._range, dimensionless)

    def scalar_to_base_units(q: int | float | Quantity | None) -> Quantity | None:
        if q is None:
            return None
        if isinstance(q, Quantity):
            return q.to_base_units().magnitude * dimensionless
        return q * dimensionless

    param_ops = GraphFunctions(G).nodes_of_type(ParameterOperatable)

    repr_map: dict[ParameterOperatable, ParameterOperatable] = {}

    for po in cast(
        Iterable[ParameterOperatable],
        ParameterOperatable.sort_by_depth(param_ops, ascending=True),
    ):
        if isinstance(po, Parameter):
            new_param = Parameter(
                units=dimensionless,
                within=None,
                domain=po.domain,
                soft_set=set_to_base_units(po.soft_set),
                guess=scalar_to_base_units(po.guess),
                tolerance_guess=po.tolerance_guess,
                likely_constrained=po.likely_constrained,
            )
            repr_map[po] = new_param
            if po.within is not None:
                new_param.constrain_subset(set_to_base_units(po.within))
        elif isinstance(po, Expression):
            new_ops = []
            for op in po.operands:
                if isinstance(op, ParameterOperatable):
                    assert op in repr_map
                    new_ops.append(repr_map[op])
                elif isinstance(op, int | float | Quantity):
                    new_ops.append(scalar_to_base_units(op))
                else:
                    new_ops.append(set_to_base_units(op))
            repr_map[po] = create_new_expr(po, *new_ops)

    return repr_map


def resolve_alias_classes(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable], bool]:
    dirty = False
    params_ops = [
        p
        for p in GraphFunctions(G).nodes_of_type(ParameterOperatable)
        if get_constrained_predicates_involved_in(p)
    ]
    exprs = GraphFunctions(G).nodes_of_type(Expression)
    predicates = {e for e in exprs if isinstance(e, Predicate)}
    exprs.difference_update(predicates)
    exprs = {e for e in exprs if get_constrained_predicates_involved_in(e)}

    p_alias_classes = parameter_ops_alias_classes(G)
    dependency_classes = parameter_dependency_classes(G)

    infostr = (
        f"{len(params_ops)} parametersoperable"
        f"\n    {len(p_alias_classes)} alias classes"
        f"\n    {len(dependency_classes)} dependency classes"
        "\n"
    )
    logger.info(infostr)

    repr_map: dict[ParameterOperatable, ParameterOperatable] = {}

    # Make new param repre for alias classes
    for param_op in ParameterOperatable.sort_by_depth(params_ops, ascending=True):
        if param_op in repr_map or param_op not in p_alias_classes:
            continue

        alias_class = p_alias_classes[param_op]

        # TODO short-cut if len() == 1 ?
        param_alias_class = [p for p in alias_class if isinstance(p, Parameter)]
        expr_alias_class = [p for p in alias_class if isinstance(p, Expression)]

        # TODO non unit/numeric params, i.e. enums, bools
        # single unit
        unit_candidates = {HasUnit.get_units(p) for p in alias_class}
        if len(unit_candidates) > 1:
            raise ValueError("Incompatible units in alias class")
        if len(param_alias_class) > 0:
            dirty |= len(param_alias_class) > 1

            # single domain
            domain_candidates = {p.domain for p in param_alias_class}
            if len(domain_candidates) > 1:
                raise ValueError("Incompatible domains in alias class")

            # intersect ranges
            within_ranges = {
                p.within for p in param_alias_class if p.within is not None
            }
            within = None
            if within_ranges:
                within = Ranges.op_intersect_ranges(*within_ranges)

            # heuristic:
            # intersect soft sets
            soft_sets = {
                p.soft_set for p in param_alias_class if p.soft_set is not None
            }
            soft_set = None
            if soft_sets:
                soft_set = Ranges.op_intersect_ranges(*soft_sets)

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
            representative = Parameter(units=unit_candidates.pop())

        if len(expr_alias_class) > 0:
            for e in expr_alias_class:
                copy_expr = copy_operand_recursively(e, repr_map)
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
        if isinstance(expr, Is):
            continue

        assert all(
            o in repr_map or not isinstance(o, ParameterOperatable)
            for o in expr.operands
        )
        repr_map[expr] = copy_operand_recursively(expr, repr_map)

    return repr_map, dirty


def subset_of_literal(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable], bool]:
    dirty = False
    params = GraphFunctions(G).nodes_of_type(Parameter)
    removed = set()
    repr_map: dict[ParameterOperatable, ParameterOperatable] = {}

    for param in params:
        is_subsets = [
            e
            for e in param.get_operations()
            if isinstance(e, IsSubset)
            and len(e.get_operations()) == 0
            and not isinstance(e.get_other_operand(param), ParameterOperatable)
        ]
        if len(is_subsets) > 1:
            other_sets = [e.get_other_operand(param) for e in is_subsets]
            intersected = other_sets[0]
            for s in other_sets[1:]:
                intersected = intersected.op_intersect_ranges(Ranges(s))
            removed.update(is_subsets)
            new_param = copy_param(param)
            new_param.constrain_subset(intersected)
            repr_map[param] = new_param
            dirty = True
        else:
            repr_map[param] = copy_param(param)

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
        copy_operand_recursively(expr, repr_map)

    return repr_map, dirty


def is_replacable(
    repr_map: dict[ParameterOperatable, ParameterOperatable],
    e: Expression,
    parent_expr: Expression,
) -> bool:
    if e in repr_map:  # overly restrictive: equivalent replacement would be ok
        return False
    if e.get_operations() != {parent_expr}:
        return False
    return True


def compress_associative_add_mul(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable], bool]:
    dirty = False
    add_muls = cast(
        set[Add | Multiply], GraphFunctions(G).nodes_of_types((Add, Multiply))
    )
    # get out deepest expr in compressable tree
    parent_add_muls = {
        e for e in add_muls if type(e) not in {type(n) for n in e.get_operations()}
    }

    repr_map: dict[ParameterOperatable, ParameterOperatable] = {}
    removed = set()

    # (A + B) + C
    #    X -> Y
    # compress(Y)
    #    compress(X) -> [A, B]
    # -> [A, B, C]

    def flatten_operands_of_ops_with_same_type[T: Add | Multiply](
        e: T,
    ) -> tuple[list[T], bool]:
        dirty = False
        operands = e.operands
        noncomp, compressible = partition(
            lambda o: type(o) is type(e) and is_replacable(repr_map, o, e), operands
        )
        out = []
        for c in compressible:
            dirty = True
            removed.add(c)
            sub_out, sub_dirty = flatten_operands_of_ops_with_same_type(c)
            dirty |= sub_dirty
            out += sub_out
        if len(out) > 0:
            logger.info(f"FLATTENED {type(e).__name__} {e} -> {out}")
        return out + list(noncomp), dirty

    for expr in cast(
        Iterable[Add | Multiply],
        ParameterOperatable.sort_by_depth(parent_add_muls, ascending=True),
    ):
        operands, sub_dirty = flatten_operands_of_ops_with_same_type(expr)
        if sub_dirty:
            dirty = True
            copy_operands = [copy_operand_recursively(o, repr_map) for o in operands]

            new_expr = create_new_expr(
                expr,
                *copy_operands,
            )
            repr_map[expr] = new_expr

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
        copy_operand_recursively(o, repr_map)

    return repr_map, dirty


def compress_associative_sub(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable], bool]:
    logger.info("Compressing Subtracts")
    dirty = False
    subs = cast(set[Subtract], GraphFunctions(G).nodes_of_type(Subtract))
    # get out deepest expr in compressable tree
    parent_subs = {
        e for e in subs if type(e) not in {type(n) for n in e.get_operations()}
    }

    removed = set()
    repr_map: dict[ParameterOperatable, ParameterOperatable] = {}

    def flatten_sub(
        e: Subtract,
    ) -> tuple[
        ParameterOperatable.All,
        list[ParameterOperatable.All],
        list[ParameterOperatable.All],
        bool,
    ]:
        const_subtrahend = (
            [] if isinstance(e.operands[1], ParameterOperatable) else [e.operands[1]]
        )
        nonconst_subtrahend = [] if const_subtrahend else [e.operands[1]]
        if isinstance(e.operands[0], Subtract) and is_replacable(
            repr_map, e.operands[0], e
        ):
            removed.add(e.operands[0])
            minuend, const_subtrahends, nonconst_subtrahends, _ = flatten_sub(
                e.operands[0]
            )
            return (
                minuend,
                const_subtrahends + const_subtrahend,
                nonconst_subtrahends + nonconst_subtrahend,
                True,
            )
        else:
            return e.operands[0], const_subtrahend, nonconst_subtrahend, False

    for expr in cast(
        Iterable[Subtract],
        ParameterOperatable.sort_by_depth(parent_subs, ascending=True),
    ):
        minuend, const_subtrahends, nonconst_subtrahends, sub_dirty = flatten_sub(expr)
        if (
            isinstance(minuend, Add)
            and is_replacable(repr_map, minuend, expr)
            and len(const_subtrahends) > 0
        ):
            copy_minuend = Add(
                *(copy_operand_recursively(s, repr_map) for s in minuend.operands),
                *(-1 * c for c in const_subtrahends),
            )
            repr_map[expr] = copy_minuend
            const_subtrahends = []
            sub_dirty = True
        elif sub_dirty:
            copy_minuend = copy_operand_recursively(minuend, repr_map)
        if sub_dirty:
            dirty = True
            copy_subtrahends = [
                copy_operand_recursively(s, repr_map)
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
        copy_o = copy_operand_recursively(o, repr_map)
        logger.info(f"REMAINING {o} -> {copy_o}")
        repr_map[o] = copy_o

    return repr_map, dirty


def compress_arithmetic_expressions(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable], bool]:
    dirty = False
    arith_exprs = cast(set[Arithmetic], GraphFunctions(G).nodes_of_type(Arithmetic))

    repr_map: dict[ParameterOperatable, ParameterOperatable] = {}
    removed = set()

    for expr in cast(
        Iterable[Arithmetic],
        ParameterOperatable.sort_by_depth(arith_exprs, ascending=True),
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
                    n: copy_operand_recursively(n, repr_map) for n in multiplicity
                }
                nonconst_prod = [
                    Multiply(copied[n], m) if m > 1 else copied[n]
                    for n, m in multiplicity.items()
                ]
                new_operands = [
                    *nonconst_prod,
                    *const_sum,
                    *(
                        copy_operand_recursively(o, repr_map)
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
                        n: copy_operand_recursively(n, repr_map) for n in multiplicity
                    }
                    nonconst_power = [
                        Power(copied[n], m) if m > 1 else copied[n]
                        for n, m in multiplicity.items()
                    ]
                    new_operands = [
                        *nonconst_power,
                        *const_prod,
                        *(
                            copy_operand_recursively(o, repr_map)
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
                    copy_operand_recursively(expr.operands[0], repr_map),
                )
                repr_map[expr] = repr_map[expr.operands[0]]
                removed.add(expr)
            else:
                repr_map[expr] = copy_operand_recursively(expr, repr_map)
        elif isinstance(expr, Divide):
            if sum(1 for _ in const_ops) == 2:
                if not expr.operands[1].magnitude == 0:
                    dirty = True
                    repr_map[expr] = expr.operands[0] / expr.operands[1]
                    removed.add(expr)
                else:
                    # no valid solution but might not matter e.g. [phi(a,b,...)
                    # OR a/0 == b]
                    repr_map[expr] = copy_operand_recursively(expr, repr_map)
            elif expr.operands[1] is expr.operands[0]:  # TODO obv eq, replacable
                dirty = True
                repr_map[expr] = 1 * dimensionless
                removed.add(expr)
            elif expr.operands[1] == 1 * expr.operands[1].units:
                dirty = True
                repr_map[expr.operands[0]] = repr_map.get(
                    expr.operands[0],
                    copy_operand_recursively(expr.operands[0], repr_map),
                )
                repr_map[expr] = repr_map[expr.operands[0]]
                removed.add(expr)
            else:
                repr_map[expr] = copy_operand_recursively(expr, repr_map)
        else:
            repr_map[expr] = copy_operand_recursively(expr, repr_map)

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
        copy_operand_recursively(o, repr_map)

    return {
        k: v for k, v in repr_map.items() if isinstance(v, ParameterOperatable)
    }, dirty


def remove_obvious_tautologies(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable], bool]:
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
            len(get_constrained_predicates_involved_in(po).difference({pred_is})) == 0
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
            repr_map[p] = copy_operand_recursively(p, repr_map)
    return repr_map, dirty


class DefaultSolver(Solver):
    timeout: int = 1000

    def phase_one_no_guess_solving(self, g: Graph) -> None:
        logger.info(f"Phase 1 Solving: No guesses {'-' * 80}")

        # strategies
        # https://miro.com/app/board/uXjVLV3O2BQ=/
        # compress expressions inside alias classes
        #   x / y => x / x
        # associativity
        #   (x + a) + b => x + a + b [for +,*]
        # compress expressions that are using literals
        #   x + 1 + 5 => x + 6
        #   x + 0 => x
        #   x * 1 => x
        #   x * 0 => 0
        #   x / 1 => x
        # compress calculatable expressions
        #   x / x => 1
        #   x + x => 2*x
        #   x - x => 0
        #   x * x => x^2
        #   k*x + l*x => (k+l)*x
        #   sqrt(x^2) => abs(x)
        #   sqrt(x) * sqrt(x) => x

        # as long as progress iterate

        logger.info("Phase 0 Solving: normalize graph")
        repr_map = normalize_graph(g)
        debug_print(repr_map)
        graphs = unique_ref(p.get_graph() for p in repr_map.values())
        # TODO assert all new graphs

        dirty = True
        iter = 0

        while dirty and len(graphs) > 0:
            iter += 1
            logger.info(f"Iteration {iter}")
            logger.info("Phase 1 Solving: Alias classes")
            repr_map = {}
            for g in graphs:
                alias_repr_map, alias_dirty = resolve_alias_classes(g)
                repr_map.update(alias_repr_map)
            debug_print(repr_map)
            graphs = unique_ref(p.get_graph() for p in repr_map.values())
            # TODO assert all new graphs

            logger.info("Phase 2a Solving: Add/Mul associative expressions")
            repr_map = {}
            for g in graphs:
                assoc_add_mul_repr_map, assoc_add_mul_dirty = (
                    compress_associative_add_mul(g)
                )
                repr_map.update(assoc_add_mul_repr_map)
            debug_print(repr_map)
            graphs = unique_ref(p.get_graph() for p in repr_map.values())
            # TODO assert all new graphs

            logger.info("Phase 2a Solving: Add/Mul associative expressions")
            repr_map = {}
            for g in graphs:
                assoc_add_mul_repr_map, assoc_add_mul_dirty = (
                    compress_associative_add_mul(g)
                )
                repr_map.update(assoc_add_mul_repr_map)
            debug_print(repr_map)
            graphs = unique_ref(p.get_graph() for p in repr_map.values())
            # TODO assert all new graphs

            logger.info("Phase 2b Solving: Subtract associative expressions")
            repr_map = {}
            for g in graphs:
                assoc_sub_repr_map, assoc_sub_dirty = compress_associative_sub(g)
                repr_map.update(assoc_sub_repr_map)
            debug_print(repr_map)
            graphs = unique_ref(p.get_graph() for p in repr_map.values())
            # TODO assert all new graphs

            logger.info("Phase 3 Solving: Arithmetic expressions")
            repr_map = {}
            for g in graphs:
                arith_repr_map, arith_dirty = compress_arithmetic_expressions(g)
                repr_map.update(arith_repr_map)
            debug_print(repr_map)
            graphs = unique_ref(p.get_graph() for p in repr_map.values())
            # TODO assert all new graphs

            logger.info("Phase 4 Solving: Remove obvious tautologies")
            repr_map = {}
            for g in graphs:
                tautology_repr_map, tautology_dirty = remove_obvious_tautologies(g)
                repr_map.update(tautology_repr_map)
            debug_print(repr_map)
            graphs = unique_ref(p.get_graph() for p in repr_map.values())
            # TODO assert all new graphs

            logger.info("Phase 5 Solving: Subset of literals")
            repr_map = {}
            for g in graphs:
                subset_repr_map, subset_dirty = subset_of_literal(g)
                repr_map.update(subset_repr_map)
            debug_print(repr_map)
            graphs = unique_ref(p.get_graph() for p in repr_map.values())
            # TODO assert all new graphs

            dirty = (
                alias_dirty
                or assoc_add_mul_dirty
                or assoc_sub_dirty
                or arith_dirty
                or tautology_dirty
                or subset_dirty
            )

    def get_any_single(
        self,
        operatable: ParameterOperatable,
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Any:
        raise NotImplementedError()

    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Solver.SolveResultAny[ArgType]:
        raise NotImplementedError()

    def find_and_lock_solution(self, G: Graph) -> Solver.SolveResultAll:
        raise NotImplementedError()
