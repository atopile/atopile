# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from statistics import median
from typing import Any

from faebryk.core.graphinterface import Graph, GraphInterfaceSelf
from faebryk.core.parameter import (
    Expression,
    Is,
    Parameter,
    ParameterOperatable,
    Predicate,
)
from faebryk.core.solver import Solver
from faebryk.libs.sets import Ranges
from faebryk.libs.util import EquivalenceClasses

logger = logging.getLogger(__name__)


def parameter_alias_classes(G: Graph) -> list[set[Parameter]]:
    full_eq = EquivalenceClasses[Parameter](G.nodes_of_type(Parameter))

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
    return [p for p in dependants if isinstance(p, Predicate) and p.constrained]


def parameter_dependency_classes(G: Graph) -> list[set[Parameter]]:
    related = EquivalenceClasses[Parameter](G.nodes_of_type(Parameter))

    eq_exprs = [e for e in G.nodes_of_type(Predicate) if e.constrained]

    for eq_expr in eq_exprs:
        params = get_params_for_expr(eq_expr)
        related.add_eq(*params)

    return related.get()


def resolve_alias_classes(G: Graph) -> dict[ParameterOperatable, ParameterOperatable]:
    params = [
        p
        for p in G.nodes_of_type(Parameter)
        if get_constrained_predicates_involved_in(p)
    ]
    exprs = G.nodes_of_type(Expression)
    predicates = {e for e in exprs if isinstance(e, Predicate)}
    exprs.difference_update(predicates)

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

    part_of_class_params = {p for c in p_alias_classes for p in c}
    not_part_of_class_params = set(params).difference(part_of_class_params)

    # Make new param repre for alias classes
    for alias_class in p_alias_classes:
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

    # copy non alias params (that are in use)
    for p in not_part_of_class_params:
        repr_map[p] = Parameter(
            units=p.units,
            within=p.within,
            domain=p.domain,
            soft_set=p.soft_set,
            guess=p.guess,
            tolerance_guess=p.tolerance_guess,
            likely_constrained=p.likely_constrained,
        )

    # replace parameters in expressions and predicates
    for expr in exprs | predicates:

        def try_replace(o: ParameterOperatable.All):
            if not isinstance(o, ParameterOperatable):
                return o
            if o in repr_map:
                return repr_map[o]
            # TODO
            raise Exception()

        # filter alias class Is
        if isinstance(expr, Is):
            if all(isinstance(o, Parameter) for o in expr.operands):
                continue

        operands = [try_replace(o) for o in expr.operands]
        new_expr = type(expr)(*operands)
        logger.info(f"{expr}[{expr.operands}] ->\n     {new_expr}[{new_expr.operands}]")
        repr_map[expr] = new_expr

    return repr_map


class DefaultSolver(Solver):
    timeout: int = 1000

    def phase_one_no_guess_solving(self, G: Graph) -> None:
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

        # as long as progress iterate

        repr_map = resolve_alias_classes(G)

        graphs = {p.get_graph() for p in repr_map.values()}

        logger.info(f"{len(graphs)} new graphs")
        for s, d in repr_map.items():
            logger.info(f"{s} -> {d}")

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
