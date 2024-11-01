# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from collections.abc import Iterable
import logging
from statistics import median
from typing import Any, cast

from more_itertools import partition

from faebryk.core.graphinterface import Graph, GraphInterfaceSelf
from faebryk.core.parameter import (
    Add,
    Arithmetic,
    Constrainable,
    Expression,
    Is,
    Multiply,
    Parameter,
    ParameterOperatable,
    Power,
    Predicate,
    Subtract,
)
from faebryk.core.solver import Solver
from faebryk.libs.sets import Ranges
from faebryk.libs.util import EquivalenceClasses

logger = logging.getLogger(__name__)


def parameter_alias_classes(G: Graph) -> list[set[Parameter]]:
    # TODO just get passed
    params = [
        p
        for p in G.nodes_of_type(Parameter)
        if get_constrained_predicates_involved_in(p)
    ]
    full_eq = EquivalenceClasses[Parameter](params)

    is_exprs = [e for e in G.nodes_of_type(Is) if e.constrained]

    for is_expr in is_exprs:
        params_ops = [op for op in is_expr.operands if isinstance(op, Parameter)]
        full_eq.add_eq(*params_ops)

    return full_eq.get()


def get_params_for_expr(expr: Expression) -> set[Parameter]:
    param_ops = {op for op in expr.operatable_operands if isinstance(op, Parameter)}
    expr_ops = {op for op in expr.operatable_operands if isinstance(op, Expression)}

    return param_ops | {op for e in expr_ops for op in get_params_for_expr(e)}


def get_constrained_predicates_involved_in(
    p: Parameter | Expression,
) -> list[Predicate]:
    # p.self -> p.operated_on -> e1.operates_on -> e1.self
    dependants = p.bfs_node(
        lambda path, _: isinstance(path[-1].node, ParameterOperatable)
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
    res = [p for p in dependants if isinstance(p, Predicate) and p.constrained]
    return res


def parameter_dependency_classes(G: Graph) -> list[set[Parameter]]:
    # TODO just get passed
    params = [
        p
        for p in G.nodes_of_type(Parameter)
        if get_constrained_predicates_involved_in(p)
    ]

    related = EquivalenceClasses[Parameter](params)

    eq_exprs = [e for e in G.nodes_of_type(Predicate) if e.constrained]

    for eq_expr in eq_exprs:
        params = get_params_for_expr(eq_expr)
        related.add_eq(*params)

    return related.get()


# TODO make part of Expression class
def create_new_expr(
    old_expr: Expression, *operands: ParameterOperatable.All
) -> Expression:
    new_expr = type(old_expr)(*operands)
    if isinstance(old_expr, Constrainable):
        cast(Constrainable, new_expr).constrained = old_expr.constrained
    return new_expr


def resolve_alias_classes(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable], bool]:
    dirty = False
    params = [
        p
        for p in G.nodes_of_type(Parameter)
        if get_constrained_predicates_involved_in(p)
    ]
    exprs = G.nodes_of_type(Expression)
    predicates = {e for e in exprs if isinstance(e, Predicate)}
    exprs.difference_update(predicates)
    exprs = {e for e in exprs if get_constrained_predicates_involved_in(e)}

    p_alias_classes = parameter_alias_classes(G)
    dependency_classes = parameter_dependency_classes(G)

    infostr = (
        f"{len(params)} parameters"
        f"\n    {len(p_alias_classes)} alias classes"
        f"\n    {len(dependency_classes)} dependency classes"
        "\n"
    )
    logger.info("Phase 1 Solving: Alias classes")
    logger.info(infostr)

    repr_map: dict[ParameterOperatable, ParameterOperatable] = {}

    # Make new param repre for alias classes
    for alias_class in p_alias_classes:
        # TODO short-cut if len() == 1
        if len(alias_class) > 1:
            dirty = True

        # single unit
        unit_candidates = {p.units for p in alias_class}
        if len(unit_candidates) > 1:
            raise ValueError("Incompatible units in alias class")

        # single domain
        domain_candidates = {p.domain for p in alias_class}
        if len(domain_candidates) > 1:
            raise ValueError("Incompatible domains in alias class")

        # intersect ranges
        within_ranges = {p.within for p in alias_class if p.within is not None}
        within = None
        if within_ranges:
            within = Ranges.op_intersect_ranges(*within_ranges)

        # heuristic:
        # intersect soft sets
        soft_sets = {p.soft_set for p in alias_class if p.soft_set is not None}
        soft_set = None
        if soft_sets:
            soft_set = Ranges.op_intersect_ranges(*soft_sets)

        # heuristic:
        # get median
        guesses = {p.guess for p in alias_class if p.guess is not None}
        guess = None
        if guesses:
            guess = median(guesses)  # type: ignore

        # heuristic:
        # max tolerance guess
        tolerance_guesses = {
            p.tolerance_guess for p in alias_class if p.tolerance_guess is not None
        }
        tolerance_guess = None
        if tolerance_guesses:
            tolerance_guess = max(tolerance_guesses)

        likely_constrained = any(p.likely_constrained for p in alias_class)

        representative = Parameter(
            units=unit_candidates.pop(),
            within=within,
            soft_set=soft_set,
            guess=guess,
            tolerance_guess=tolerance_guess,
            likely_constrained=likely_constrained,
        )
        repr_map.update({p: representative for p in alias_class})

    # replace parameters in expressions and predicates
    for expr in cast(
        Iterable[Expression],
        ParameterOperatable.sort_by_depth(exprs | predicates, ascending=True),
    ):

        def try_replace(o: ParameterOperatable.All):
            if not isinstance(o, ParameterOperatable):
                return o
            if o in repr_map:
                return repr_map[o]
            raise Exception()

        # filter alias class Is
        if isinstance(expr, Is):
            if all(isinstance(o, Parameter) for o in expr.operands):
                continue

        operands = [try_replace(o) for o in expr.operands]
        new_expr = create_new_expr(expr, *operands)
        logger.info(f"{expr}[{expr.operands}] ->\n     {new_expr}[{new_expr.operands}]")
        repr_map[expr] = new_expr

    return repr_map, dirty


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


def copy_pop(
    o: ParameterOperatable.All, repr_map: dict[ParameterOperatable, ParameterOperatable]
) -> ParameterOperatable.All:
    if o in repr_map:
        return repr_map[o]
    if isinstance(o, Expression):
        return create_new_expr(
            o,
            *(
                repr_map[op] if op in repr_map else copy_pop(op, repr_map)
                for op in o.operands
            ),
        )
    elif isinstance(o, Parameter):
        return copy_param(o)
    else:
        return o


def compress_associative_expressions(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable], bool]:
    dirty = False
    add_muls = cast(set[Add | Multiply], G.nodes_of_types((Add, Multiply)))
    # get out deepest expr in compressable tree
    parent_add_muls = {
        e for e in add_muls if type(e) not in {type(n) for n in e.get_operations()}
    }

    repr_map: dict[ParameterOperatable, ParameterOperatable] = {}

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
        noncomp, compressable = partition(lambda o: type(o) is type(e), operands)
        out = []
        for c in compressable:
            dirty = True
            if c in repr_map:
                out.append(repr_map[c])
            else:
                sub_out, sub_dirty = flatten_operands_of_ops_with_same_type(c)
                dirty |= sub_dirty
                out += sub_out
        return out + list(noncomp), dirty

    for expr in cast(
        Iterable[Add | Multiply],
        ParameterOperatable.sort_by_depth(parent_add_muls, ascending=True),
    ):
        operands, sub_dirty = flatten_operands_of_ops_with_same_type(expr)
        dirty |= sub_dirty
        # copy
        for o in operands:
            if isinstance(o, ParameterOperatable):
                repr_map[o] = copy_pop(o, repr_map)

        # make new compressed expr with (copied) operands
        new_expr = create_new_expr(
            expr,
            *(
                repr_map[o] if o in repr_map else copy_pop(o, repr_map)
                for o in operands
            ),
        )
        repr_map[expr] = new_expr

    # copy other param ops
    other_param_op = ParameterOperatable.sort_by_depth(
        (
            p
            for p in G.nodes_of_type(ParameterOperatable)
            if p not in repr_map and p not in add_muls
        ),
        ascending=True,
    )
    remaining_param_op = {p: copy_pop(p, repr_map) for p in other_param_op}
    repr_map.update(remaining_param_op)

    return repr_map, dirty


def compress_arithmetic_expressions(
    G: Graph,
) -> tuple[dict[ParameterOperatable, ParameterOperatable], bool]:
    dirty = False
    arith_exprs = cast(set[Arithmetic], G.nodes_of_type(Arithmetic))

    repr_map: dict[ParameterOperatable, ParameterOperatable] = {}

    for expr in cast(
        Iterable[Arithmetic],
        ParameterOperatable.sort_by_depth(arith_exprs, ascending=True),
    ):
        operands = expr.operands
        const_ops, nonconst_ops = partition(
            lambda o: isinstance(o, ParameterOperatable), operands
        )
        multiplicity = {}
        has_multiplicity = False
        for n in nonconst_ops:
            if n in multiplicity:
                has_multiplicity = True
                multiplicity[n] += 1
            else:
                multiplicity[n] = 1

        if isinstance(expr, Add):
            try:
                const_sum = [next(const_ops)]
                for c in const_ops:
                    dirty = True
                    const_sum[0] += c
                if const_sum[0] == 0 * expr.units:  # TODO make work with all the types
                    dirty = True
                    const_sum = []
            except StopIteration:
                const_sum = []
            nonconst_prod = {
                n: Multiply(n, m) if m > 1 else copy_pop(n, repr_map)
                for n, m in multiplicity.items()
            }
            new_operands = (*nonconst_prod.values(), *const_sum)
            if len(new_operands) > 1:
                new_expr = Add(*new_operands)
            elif len(new_operands) == 1:
                new_expr = new_operands[0]
            else:
                raise ValueError("No operands, should not happen")
            repr_map.update(nonconst_prod)
            repr_map[expr] = new_expr

        elif isinstance(expr, Multiply):
            try:
                const_prod = [next(const_ops)]
                for c in const_ops:
                    dirty = True
                    const_prod[0] *= c
                if const_prod[0] == 1 * expr.units:  # TODO make work with all the types
                    dirty = True
                    const_prod = []
            except StopIteration:
                const_prod = []
            if (
                len(const_prod) == 1 and const_prod[0] == 0 * expr.units
            ):  # TODO make work with all the types
                dirty = True
                repr_map[expr] = 0 * expr.units
            else:
                nonconst_prod = {
                    n: Power(n, m) if m > 1 else copy_pop(n, repr_map)
                    for n, m in multiplicity.items()
                }
                if has_multiplicity:
                    dirty = True
                new_operands = (*nonconst_prod.values(), *const_prod)
                if len(new_operands) > 1:
                    new_expr = Multiply(*new_operands)
                elif len(new_operands) == 1:
                    new_expr = new_operands[0]
                else:
                    raise ValueError("No operands, should not happen")
                repr_map.update(nonconst_prod)
                repr_map[expr] = new_expr
        elif isinstance(expr, Subtract):
            if expr.operands[0] is expr.operands[1]:
                dirty = True
                repr_map[expr] = 0 * expr.units
            elif len(const_ops) == 2:
                dirty = True
                repr_map[expr] = expr.operands[0] - expr.operands[1]
            else:
                repr_map[expr] = copy_pop(expr, repr_map)
        else:
            repr_map[expr] = copy_pop(expr, repr_map)

    other_param_op = ParameterOperatable.sort_by_depth(
        (
            p
            for p in G.nodes_of_type(ParameterOperatable)
            if p not in repr_map and p not in arith_exprs
        ),
        ascending=True,
    )
    remaining_param_op = {p: copy_pop(p, repr_map) for p in other_param_op}
    repr_map.update(remaining_param_op)

    return {
        k: v for k, v in repr_map.items() if isinstance(v, ParameterOperatable)
    }, dirty


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

        graphs = {g}
        dirty = True
        iter = 0

        while dirty:
            iter += 1
            logger.info(f"Iteration {iter}")
            repr_map = {}
            for g in graphs:
                alias_repr_map, alias_dirty = resolve_alias_classes(g)
                repr_map.update(alias_repr_map)
            graphs = {p.get_graph() for p in repr_map.values()}
            for g in graphs:
                logger.info(f"G: {g}")
            logger.info(f"{len(graphs)} new graphs")
            # TODO assert all new graphs

            logger.info("Phase 2 Solving: Associative expressions")
            repr_map = {}
            for g in graphs:
                assoc_repr_map, assoc_dirty = compress_associative_expressions(g)
                repr_map.update(assoc_repr_map)
            for s, d in repr_map.items():
                if isinstance(s, Expression):
                    logger.info(f"{s}[{s.operands}] -> {d}[{d.operands}]")
                else:
                    logger.info(f"{s} -> {d}")
            graphs = {p.get_graph() for p in repr_map.values()}
            logger.info(f"{len(graphs)} new graphs")
            # TODO assert all new graphs

            logger.info("Phase 3 Solving: Arithmetic expressions")
            repr_map = {}
            for g in graphs:
                arith_repr_map, arith_dirty = compress_arithmetic_expressions(g)
                repr_map.update(arith_repr_map)
            for s, d in repr_map.items():
                if isinstance(s, Expression):
                    logger.info(f"{s}[{s.operands}] -> {d}[{d.operands}] | G: {id(g)}")
                else:
                    logger.info(f"{s} -> {d} | G: {id(g)}")
            graphs = {p.get_graph() for p in repr_map.values()}
            logger.info(f"{len(graphs)} new graphs")
            # TODO assert all new graphs

            dirty = alias_dirty or assoc_dirty or arith_dirty

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
