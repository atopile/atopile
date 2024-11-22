# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections.abc import Iterable
from typing import Any, Callable

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.parameter import (
    Expression,
    Is,
    IsSubset,
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
    upper_estimation_of_expressions_with_subsets,
)
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import (
    Contradiction,
    Mutator,
    Mutators,
    NumericLiteralR,
    literal_to_base_units,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval_Disjoint,
    QuantitySetLikeR,
)
from faebryk.libs.sets.sets import P_Set, PlainSet
from faebryk.libs.units import dimensionless
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

                # # FIXME: I don't think this is correct
                # assert isinstance(operand, ParameterOperatable)
                return operand

            mutator.mutate_expression_with_op_map(po, mutate)


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
    def phase_one_no_guess_solving(self, g: Graph):
        logger.info("Phase 1 Solving: No guesses".ljust(80, "="))

        # TODO move into comment here
        # strategies
        # https://www.notion.so/
        # Phase1-136836dcad9480cbb037defe359934ee?pvs=4#136836dcad94807d93bccb14598e1ef0

        pre_algorithms = [
            ("Constrain within and domain", constrain_within_and_domain),
            ("Strip units", strip_units),
        ]
        iterative_algorithms = [
            ("Remove unconstrained", remove_unconstrained),
            ("Alias classes", resolve_alias_classes),
            ("Remove obvious tautologies", remove_obvious_tautologies),
            ("Inequality to set", convert_inequality_to_subset),
            ("Canonical expression form", convert_to_canonical_operations),
            ("Associative expressions Full", compress_associative),
            ("Fold literals", fold_literals),
            ("Merge intersecting subsets", merge_intersect_subsets),
        ]
        subset_dirty_algorithms = [
            ("Upper estimation", upper_estimation_of_expressions_with_subsets),
        ]

        def run_algo(graphs: list[Graph], phase_name: str, algo_name: str, algo: Callable[[Mutator], None]):
            mutators = Mutators(*graphs)
            mutators.run(algo)
            algo_repr_map, algo_graphs, algo_dirty = mutators.close()
            if algo_dirty:
                logger.info(
                    f"Iteration {iterno} Phase 1.{phase_name}: {algo_name} G:{len(graphs)}"
                )
                for mutator in mutators:
                    mutator.debug_print()
            # TODO assert all new graphs
            return algo_repr_map, algo_graphs, algo_dirty
        any_dirty = True
        iterno = 0
        total_repr_map: dict[tuple[int, str], Mutator.REPR_MAP] = {}
        param_ops_subset_literals: dict[ParameterOperatable, ParameterOperatable.Literal] = {
            po: po.try_get_literal_subset() for po in GraphFunctions(g).nodes_of_type(ParameterOperatable)
        }
        graphs = [g]

        while any_dirty and len(graphs) > 0:
            v_count = sum(g.node_count for g in graphs)
            logger.info(
                f"Iteration {iterno} |graphs|: {len(graphs)}, |V|: {v_count}".ljust(
                    80, "-"
                )
            )

            if iterno == 0:
                algos = pre_algorithms
            else:
                algos = iterative_algorithms

            iteration_repr_maps: dict[tuple[int, str], Mutator.REPR_MAP] = {}
            iteration_dirty = {}
            for phase_name, (algo_name, algo) in enumerate(algos):
                algo_repr_map, algo_graphs, algo_dirty = run_algo(graphs, phase_name, algo_name, algo)
                if not algo_dirty:
                    continue
                iteration_dirty[(iterno, algo_name)] = algo_dirty
                graphs = algo_graphs
                iteration_repr_maps[(iterno, algo_name)] = algo_repr_map

            any_dirty = any(iteration_dirty.values())

            total_repr_map = Mutators.concat_repr_maps(*([total_repr_map] if total_repr_map else []), *iteration_repr_maps.values())

            subset_dirty = False
            total_repr_map_obj = Mutators.create_concat_repr_map(total_repr_map)
            param_ops_subset_literals = {po: lit for po, lit in param_ops_subset_literals.items() if po in total_repr_map_obj}
            for po in param_ops_subset_literals:
                new_subset_literal = total_repr_map_obj.try_get_literal(po, IsSubset)
                if new_subset_literal != param_ops_subset_literals[po]:
                    logger.info(f"Subset dirty {param_ops_subset_literals[po]} != {new_subset_literal}")
                    param_ops_subset_literals[po] = new_subset_literal
                    subset_dirty = True

            iteration_repr_maps: dict[tuple[int, str], Mutator.REPR_MAP] = {}
            if subset_dirty or iterno == 1:
                logger.info("Subset dirty, running subset dirty algorithms")
                for phase_name, (algo_name, algo) in enumerate(subset_dirty_algorithms, start=phase_name):
                    algo_repr_map, algo_graphs, algo_dirty = run_algo(graphs, phase_name, algo_name, algo)
                    if not algo_dirty:
                        continue
                    graphs = algo_graphs
                    iteration_repr_maps[(iterno, algo_name)] = algo_repr_map

            total_repr_map = Mutators.concat_repr_maps(*([total_repr_map] if total_repr_map else []), *iteration_repr_maps.values())
            iterno += 1

        return Mutators.create_concat_repr_map(total_repr_map)

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
        self, param: Parameter
    ) -> Quantity_Interval_Disjoint:
        if not isinstance(param.domain, Numbers):
            raise ValueError(f"Ranges only defined for numbers not {param.domain}")

        # run phase 1 solver
        # TODO caching
        repr_map = self.phase_one_no_guess_solving(param.get_graph())
        if param not in repr_map.repr_map:
            logger.warning(f"Parameter {param} not in repr_map")
            return Quantity_Interval_Disjoint.unbounded(param.units)

        # check predicates (is, subset), (ge, le covered too)
        literal = repr_map.try_get_literal(param, Is)
        if literal is None:
            literal = repr_map.try_get_literal(param, IsSubset)

        if literal is None:
            return Quantity_Interval_Disjoint.unbounded(param.units)

        if not isinstance(literal, QuantitySetLikeR):
            raise ValueError(f"incompatible literal {literal}")

        return Quantity_Interval_Disjoint.from_value(literal)

    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Solver.SolveResultAny[ArgType]:
        if not predicates:
            raise ValueError("No predicates given")

        result = Solver.SolveResultAny(
            timed_out=False,
            true_predicates=[],
            false_predicates=[],
            unknown_predicates=[],
        )

        it = iter(predicates)

        for p in it:
            pred, _ = p
            assert not pred.constrained
            pred.constrained = True
            try:
                repr_map = self.phase_one_no_guess_solving(pred.get_graph())
                lit = repr_map.try_get_literal(pred)
                if lit is True or lit == PlainSet(True):
                    result.true_predicates.append(p)
                    break
                elif lit is False or lit == PlainSet(False):
                    result.false_predicates.append(p)
                elif lit is None:
                    result.unknown_predicates.append(p)
                else:
                    assert False
            except Contradiction:
                result.false_predicates.append(p)
            except TimeoutError:
                result.unknown_predicates.append(p)
            finally:
                pred.constrained = False

        result.unknown_predicates.extend(it)

        if lock and result.true_predicates:
            assert len(result.true_predicates) == 1
            result.true_predicates[0].constrain()

        return result
