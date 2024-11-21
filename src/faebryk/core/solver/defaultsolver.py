# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections.abc import Iterable
from typing import Any

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.parameter import (
    Expression,
    GreaterOrEqual,
    Is,
    IsSubset,
    LessOrEqual,
    Numbers,
    Parameter,
    ParameterOperatable,
    Predicate,
)
from faebryk.core.solver.analytical import (
    compress_associative,
    convert_inequality_to_subset,
    convert_to_canonical_operations,
    fold_literals,
    merge_intersect_subsets,
    remove_obvious_tautologies,
    remove_unconstrained,
    resolve_alias_classes,
)
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import (
    Mutator,
    Mutators,
    NumericLiteralR,
    debug_print,
    get_graphs,
    literal_to_base_units,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    Quantity_Singleton,
)
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.units import HasUnit, dimensionless
from faebryk.libs.util import times_out

logger = logging.getLogger(__name__)


def constrain_within_and_domain(mutator: Mutator):
    for param in GraphFunctions(mutator.G).nodes_of_type(Parameter):
        new_param = mutator.mutate_parameter(param)
        if new_param.within is not None:
            new_param.constrain_subset(new_param.within)
        if isinstance(new_param.domain, Numbers) and not new_param.domain.negative:
            new_param.constrain_ge(0.0 * new_param.units)


def strip_units(mutator: Mutator):
    """
    units -> base units (dimensionless)
    within -> constrain is subset
    scalar to single
    """

    param_ops = GraphFunctions(mutator.G).nodes_of_type(ParameterOperatable)

    for po in ParameterOperatable.sort_by_depth(param_ops, ascending=True):
        # Parameter
        if isinstance(po, Parameter):
            mutator.mutate_parameter(
                po,
                units=dimensionless,
                soft_set=literal_to_base_units(po.soft_set),
                guess=literal_to_base_units(po.guess),
            )

        # Expression
        elif isinstance(po, Expression):

            def mutate(
                i: int, operand: ParameterOperatable.All
            ) -> ParameterOperatable.All:
                if isinstance(operand, NumericLiteralR):
                    return literal_to_base_units(operand)

                # FIXME: I don't think this is correct
                assert isinstance(operand, ParameterOperatable)
                return operand

            mutator.mutate_expression_with_op_map(po, mutate)


# FIXME doesnt work
def re_attach_units(G: Graph, total_repr_map: Mutator.REPR_MAP) -> Mutator.REPR_MAP:
    mutator = Mutator(G)

    v_sorted_by_depth = sorted(
        total_repr_map.items(),
        key=lambda x: x[1].depth() if isinstance(x[1], Expression) else 0,
    )

    repr_map = total_repr_map
    lit_map = {}

    for k, v in v_sorted_by_depth:
        logger.info(f"{k} {v}")
        if isinstance(v, NumericLiteralR):
            lit_map[k] = v * HasUnit.get_units(k)
            repr_map[k] = lit_map[k]
            logger.info(f"{k} {v} {lit_map[k]}")
        elif isinstance(v, Parameter):
            mutator.mutate_parameter(v, units=HasUnit.get_units(k))
        # elif isinstance(v, Expression):
        #    mutator.mutate_expression_with_op_map(v, lambda _, op: lit_map.get(op, op))

    mutator.copy_unmutated()

    return Mutators.concat_repr_maps(repr_map, mutator.repr_map)


class DefaultSolver(Solver):
    # TODO actually use this...
    timeout: int = 1000

    def has_no_solution(
        self, total_repr_map: dict[ParameterOperatable, ParameterOperatable.All]
    ) -> bool:
        # any parameter is/subset literal is empyt (implcit constraint that we forgot)
        # any constrained expression got mapped to False
        # any constrained expression literal is False
        raise NotImplementedError()

    @times_out(5)
    def phase_one_no_guess_solving(self, g: Graph) -> Mutator.REPR_MAP:
        logger.info("Phase 1 Solving: No guesses".ljust(80, "="))

        # TODO move into comment here
        # strategies
        # https://www.notion.so/
        # Phase1-136836dcad9480cbb037defe359934ee?pvs=4#136836dcad94807d93bccb14598e1ef0

        pre_algorithms = [
            ("Constrain within and domain", constrain_within_and_domain),
            # ("Strip units", strip_units),
        ]
        iterative_algorithms = [
            ("Remove unconstrained", remove_unconstrained),
            ("Alias classes", resolve_alias_classes),
            ("Remove obvious tautologies", remove_obvious_tautologies),
            ("Inequality to set", convert_inequality_to_subset),
            ("Canonical expression form", convert_to_canonical_operations),
            ("Associative expressions Full", compress_associative),
            ("Arithmetic expressions", fold_literals),
            ("Subset of literals", merge_intersect_subsets),
        ]

        post_algorithms = [
            # ("Re-attach units", re_attach_units),
        ]

        algo_dirty = True
        iterno = 0
        algos_repr_maps: dict[tuple[int, str], Mutator.REPR_MAP] = {}
        graphs = [g]

        while algo_dirty and len(graphs) > 0:
            logger.info(f"Iteration {iterno} ".ljust(80, "-"))

            if iterno == 0:
                algos = pre_algorithms
            else:
                algos = iterative_algorithms

            algos_dirty = {}
            for phase_name, (algo_name, algo) in enumerate(algos):
                mutators = Mutators(*graphs)
                mutators.run(algo)
                algo_repr_map, algo_graphs, algo_dirty = mutators.close()
                algos_dirty[(iterno, algo_name)] = algo_dirty
                if not algo_dirty:
                    continue
                graphs = algo_graphs
                algos_repr_maps[(iterno, algo_name)] = algo_repr_map
                logger.info(
                    f"Iteration {iterno} Phase 1.{phase_name}: {algo_name} G:{len(graphs)}"
                )
                debug_print(algo_repr_map)
                # TODO assert all new graphs

            algo_dirty = any(algos_dirty.values())
            iterno += 1

        total_repr_map = Mutators.concat_repr_maps(
            *algos_repr_maps.values(),
        )
        logger.info(f"Iteration {-1}[{iterno}] ".ljust(80, "-"))
        for phase_name, (algo_name, algo) in enumerate(post_algorithms):
            repr_map = {}
            for g in graphs:
                repr_map = algo(g, total_repr_map)
                repr_map.update(repr_map)
            graphs = get_graphs(repr_map.values())
            algos_repr_maps[(iterno, algo_name)] = repr_map
            total_repr_map = repr_map
            logger.info(
                f"Iteration {iterno} Phase 1.{phase_name}: {algo_name} G:{len(graphs)}"
            )

        # FIXME: unnormalize parameters, converting back form base units
        return total_repr_map

    def get_any_single(
        self,
        operatable: ParameterOperatable,
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Any:
        raise NotImplementedError()

    def find_and_lock_solution(self, G: Graph) -> Solver.SolveResultAll:
        return Solver.SolveResultAll(
            timed_out=False,
            has_solution=True,
        )
        # raise NotImplementedError()

    # TODO implement
    def inspect_known_min(
        self, value: ParameterOperatable.NumberLike
    ) -> ParameterOperatable.Number:
        raise NotImplementedError()

    def inspect_known_max(
        self, value: ParameterOperatable.NumberLike
    ) -> ParameterOperatable.Number:
        raise NotImplementedError()

    def inspect_known_values(
        self, value: ParameterOperatable.BooleanLike
    ) -> P_Set[bool]:
        raise NotImplementedError()

    def inspect_get_known_supersets(
        self, value: ParameterOperatable.Sets
    ) -> Iterable[P_Set]:
        raise NotImplementedError()

    # IMPORTANT ------------------------------------------------------------------------

    # Could be exponentially many
    def inspect_known_supersets_are_few(self, value: ParameterOperatable.Sets) -> bool:
        return True

    def inspect_get_known_superranges(
        self, value: Parameter
    ) -> Quantity_Interval_Disjoint:
        if not isinstance(value.domain, Numbers):
            raise ValueError(f"Ranges only defined for numbers not {value.domain}")

        # run phase 1 solver
        # TODO caching
        repr_map = self.phase_one_no_guess_solving(value.get_graph())
        if value not in repr_map:
            logger.warning(f"Parameter {value} not in repr_map")
            return Quantity_Interval_Disjoint(Quantity_Interval(units=value.units))

        value = repr_map[value]

        if not isinstance(value, ParameterOperatable):
            literal = value
            if Parameter.is_number_literal(literal):
                return Quantity_Interval_Disjoint(Quantity_Singleton(literal))
            if isinstance(literal, P_Set):
                if isinstance(literal, Quantity_Interval):
                    return Quantity_Interval_Disjoint(literal)
                if isinstance(literal, Quantity_Interval_Disjoint):
                    return literal
            raise ValueError(f"incompatible literal {literal}")

        # check predicates (is, subset)
        literal = value.try_get_literal(Is)
        if literal is None:
            literal = value.try_get_literal(IsSubset)

        if literal is not None:
            if Parameter.is_number_literal(literal):
                return Quantity_Interval_Disjoint(Quantity_Singleton(literal))
            if isinstance(literal, P_Set):
                if isinstance(literal, Quantity_Interval):
                    return Quantity_Interval_Disjoint(literal)
                if isinstance(literal, Quantity_Interval_Disjoint):
                    return literal
            raise ValueError(f"incompatible literal {literal}")

        # check predicates (greater, less)
        lower = None
        literal = value.try_get_literal(GreaterOrEqual)
        if literal is not None:
            if Parameter.is_number_literal(literal):
                lower = literal
            elif isinstance(literal, P_Set):
                if isinstance(literal, (Quantity_Interval, Quantity_Interval_Disjoint)):
                    lower = literal.max_elem()
        else:
            lower = float("-inf") * HasUnit.get_units(value)

        upper = None
        literal = value.try_get_literal(LessOrEqual)
        if literal is not None:
            if Parameter.is_number_literal(literal):
                upper = literal
            elif isinstance(literal, P_Set):
                if isinstance(literal, (Quantity_Interval, Quantity_Interval_Disjoint)):
                    upper = literal.min_elem()
        else:
            upper = float("inf") * HasUnit.get_units(value)

        return Quantity_Interval_Disjoint(Quantity_Interval(lower, upper))

    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Solver.SolveResultAny[ArgType]:
        if not predicates:
            return Solver.SolveResultAny(
                timed_out=False,
                true_predicates=[],
                false_predicates=[],
                unknown_predicates=[],
            )

        # FIXME: implement
        # raise NotImplementedError()
        return Solver.SolveResultAny(
            timed_out=False,
            true_predicates=[],
            false_predicates=[],
            unknown_predicates=predicates,
        )
