# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import defaultdict
from typing import Callable, Iterable, cast

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.graphinterface import GraphInterfaceSelf
from faebryk.core.parameter import (
    Add,
    And,
    ConstrainableExpression,
    Difference,
    Divide,
    Domain,
    Expression,
    Intersection,
    Is,
    Multiply,
    Numbers,
    Or,
    Parameter,
    ParameterOperatable,
    Predicate,
    Subtract,
    SymmetricDifference,
    Union,
    Xor,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    QuantityLike,
)
from faebryk.libs.units import Quantity, Unit, dimensionless
from faebryk.libs.util import EquivalenceClasses, unique_ref

logger = logging.getLogger(__name__)

Commutative = (
    Add | Multiply | And | Or | Xor | Union | Intersection | SymmetricDifference
)
FullyAssociative = Add | Multiply | And | Or | Xor | Union | Intersection
LeftAssociative = Subtract | Divide | Difference
Associative = FullyAssociative | LeftAssociative


def parameter_ops_alias_classes(
    G: Graph,
) -> dict[ParameterOperatable, set[ParameterOperatable]]:
    # TODO just get passed
    param_ops = {
        p
        for p in GraphFunctions(G).nodes_of_type(ParameterOperatable)
        if get_constrained_expressions_involved_in(p)
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


def is_replacable(
    repr_map: dict[ParameterOperatable, ParameterOperatable.All],
    to_replace: Expression,
    parent_expr: Expression,
) -> bool:
    """
    Check if an expression can be replaced.
    Only possible if not in use somewhere else or already mapped to new expr
    """
    if to_replace in repr_map:  # overly restrictive: equivalent replacement would be ok
        return False
    if to_replace.get_operations() != {parent_expr}:
        return False
    return True


def parameter_dependency_classes(G: Graph) -> list[set[Parameter]]:
    # TODO just get passed
    params = [
        p
        for p in GraphFunctions(G).nodes_of_type(Parameter)
        if get_constrained_expressions_involved_in(p)
    ]

    related = EquivalenceClasses[Parameter](params)

    eq_exprs = [e for e in GraphFunctions(G).nodes_of_type(Predicate) if e.constrained]

    for eq_expr in eq_exprs:
        params = get_params_for_expr(eq_expr)
        related.add_eq(*params)

    return related.get()


def debug_print(repr_map: dict[ParameterOperatable, ParameterOperatable]):
    import sys

    if getattr(sys, "gettrace", lambda: None)():
        log = print
    else:
        log = logger.debug
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


def get_params_for_expr(expr: Expression) -> set[Parameter]:
    param_ops = {op for op in expr.operatable_operands if isinstance(op, Parameter)}
    expr_ops = {op for op in expr.operatable_operands if isinstance(op, Expression)}

    return param_ops | {op for e in expr_ops for op in get_params_for_expr(e)}


def get_constrained_expressions_involved_in(
    p: ParameterOperatable,
) -> set[ConstrainableExpression]:
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
    res = {
        p
        for p in dependants
        if isinstance(p, ConstrainableExpression) and p.constrained
    }
    return res


# TODO move to Mutator
def get_graphs(values: Iterable) -> list[Graph]:
    return unique_ref(
        p.get_graph() for p in values if isinstance(p, ParameterOperatable)
    )


NumericLiteral = QuantityLike | Quantity_Interval_Disjoint | Quantity_Interval


def literal_to_base_units[T: NumericLiteral | None](q: T) -> T:
    if q is None:
        return None  # type: ignore
    if isinstance(q, bool):
        return q
    if isinstance(q, Quantity):
        return q.to_base_units().magnitude * dimensionless
    if isinstance(q, int | float):
        return q * dimensionless
    if isinstance(q, Quantity_Interval_Disjoint):
        return Quantity_Interval_Disjoint._from_intervals(q._intervals, dimensionless)
    if isinstance(q, Quantity_Interval):
        return Quantity_Interval._from_interval(q._interval, dimensionless)
    raise ValueError(f"unknown literal type {type(q)}")


# TODO use Mutator everywhere instead of repr_maps
class Mutator:
    def __init__(
        self, repr_map: dict[ParameterOperatable, ParameterOperatable.All] | None = None
    ) -> None:
        self.repr_map = repr_map or {}

    def mutate_parameter(
        self,
        param: Parameter,
        units: Unit | Quantity | None = None,
        within: Quantity_Interval_Disjoint | Quantity_Interval | None = None,
        domain: Domain | None = None,
        soft_set: Quantity_Interval_Disjoint | Quantity_Interval | None = None,
        guess: Quantity | int | float | None = None,
        tolerance_guess: float | None = None,
        likely_constrained: bool | None = None,
    ) -> Parameter:
        new_param = Parameter(
            units=units if units is not None else param.units,
            within=within if within is not None else param.within,
            domain=domain if domain is not None else param.domain,
            soft_set=soft_set if soft_set is not None else param.soft_set,
            guess=guess if guess is not None else param.guess,
            tolerance_guess=tolerance_guess
            if tolerance_guess is not None
            else param.tolerance_guess,
            likely_constrained=likely_constrained
            if likely_constrained is not None
            else param.likely_constrained,
        )

        self.repr_map[param] = new_param

        # TODO remove (make part of param)
        if new_param.within is not None:
            new_param.constrain_subset(new_param.within)
        if isinstance(new_param.domain, Numbers) and not new_param.domain.negative:
            new_param.constrain_ge(0 * new_param.units)

        return new_param

    def has_been_mutated(self, po: ParameterOperatable) -> bool:
        return po in self.repr_map

    def get_mutated(self, po: ParameterOperatable) -> ParameterOperatable.All:
        return self.repr_map[po]

    # TODO make part of Expression class
    def mutate_expression(
        self, expr: Expression, *operands: ParameterOperatable.All
    ) -> Expression:
        new_expr = type(expr)(*operands)
        for op in operands:
            if isinstance(op, ParameterOperatable):
                assert op.get_graph() == new_expr.get_graph()
        if isinstance(expr, ConstrainableExpression):
            cast(ConstrainableExpression, new_expr).constrained = expr.constrained

        self.repr_map[expr] = new_expr
        return new_expr

    def mutate_expression_with_operand_mapper(
        self,
        expr: Expression,
        operand_mutator: Callable[[ParameterOperatable], ParameterOperatable.All]
        | None = None,
    ) -> Expression:
        if operand_mutator is None:
            operand_mutator = lambda op: op  # noqa: E731

        def apply_mutator(op: ParameterOperatable.All) -> ParameterOperatable.All:
            out = operand_mutator(op)

            if isinstance(op, ParameterOperatable):
                if out is op:
                    if self.has_been_mutated(op):
                        return self.get_mutated(op)
                    else:
                        return self._copy_operand_recursively(op)

                self.repr_map[op] = out

            return out

        operands = [apply_mutator(op) for op in expr.operands]
        return self.mutate_expression(expr, *operands)

    def _copy_operand_recursively(
        self,
        o: ParameterOperatable.All,
    ) -> ParameterOperatable.All:
        if self.has_been_mutated(o):
            return self.get_mutated(o)

        if isinstance(o, Expression):
            new_ops = []
            for op in o.operands:
                new_op = self._copy_operand_recursively(op)
                if isinstance(op, ParameterOperatable):
                    self.repr_map[op] = new_op
                new_ops.append(new_op)
            expr = self.mutate_expression(o, *new_ops)
            return expr
        elif isinstance(o, Parameter):
            param = self.mutate_parameter(o)
            return param
        else:
            return o

    # TODO remove
    @staticmethod
    def copy_operand_recursively(
        o: ParameterOperatable.All,
        repr_map: dict[ParameterOperatable, ParameterOperatable.All],
    ) -> ParameterOperatable.All:
        return Mutator(repr_map)._copy_operand_recursively(o)

    # TODO move to Mutator
    @staticmethod
    def concat_repr_maps(
        *repr_maps: dict[ParameterOperatable, ParameterOperatable.All],
    ) -> dict[ParameterOperatable, ParameterOperatable.All]:
        assert len(repr_maps) > 0
        res = {}
        keys = repr_maps[0].keys()
        for k in keys:
            v = k
            for m in repr_maps:
                if v in m:
                    v = m[v]
                else:
                    if isinstance(v, ParameterOperatable):
                        raise ValueError("this should not happen ... I think")
                    break
            else:
                res[k] = v
        return res
