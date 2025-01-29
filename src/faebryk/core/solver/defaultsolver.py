# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from dataclasses import dataclass
from itertools import count
from types import SimpleNamespace
from typing import Any, override

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.parameter import (
    ConstrainableExpression,
    Expression,
    Parameter,
    ParameterOperatable,
    Predicate,
)
from faebryk.core.solver import analytical, canonical
from faebryk.core.solver.mutator import REPR_MAP, Mutator
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.core.solver.utils import (
    MAX_ITERATIONS_HEURISTIC,
    PRINT_START,
    S_LOG,
    TIMEOUT,
    Contradiction,
    SolverAlgorithm,
    debug_name_mappings,
    get_graphs,
)
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import groupby, times_out

logger = logging.getLogger(__name__)

if S_LOG:
    logger.setLevel(logging.DEBUG)


class DefaultSolver(Solver):
    """
    General documentation

    Naming:
    - Predicate: A constrainable expression that is constrained
    [Careful: not the same as the class Predicate]

    Associativity of simplification:
    - Goal: Simplify(B, Simplify(A)) == Simplify(A ^ B)
    Note: Not 100% sure if that's possible and whether we are there yet

    Debugging:
    - Run with FBRK_SLOG=y to turn on debug
    - Run with FRBK_SVERBOSE_TABLE=y for full expression names
    """

    algorithms = SimpleNamespace(
        # TODO: get order from topo sort
        # and types from decorator
        pre=[
            canonical.convert_to_canonical_operations,
            canonical.convert_to_canonical_literals,
            canonical.constrain_within_domain,
        ],
        iterative=[
            analytical.remove_unconstrained,
            analytical.convert_operable_aliased_to_single_into_literal,
            analytical.resolve_alias_classes,
            analytical.distribute_literals_across_alias_classes,
            analytical.remove_congruent_expressions,
            analytical.convert_inequality_with_literal_to_subset,
            analytical.compress_associative,
            analytical.fold_literals,
            analytical.merge_intersect_subsets,
            analytical.predicate_literal_deduce,
            analytical.predicate_unconstrained_operands_deduce,
            analytical.empty_set,
            analytical.transitive_subset,
            analytical.isolate_lone_params,
            analytical.remove_empty_graphs,
            analytical.upper_estimation_of_expressions_with_subsets,
            analytical.uncorrelated_alias_fold,
        ],
    )

    @dataclass
    class IterationData:
        graphs: list[Graph]
        total_repr_map: Mutator.ReprMap
        output_operables: dict[SolverAlgorithm, set[ParameterOperatable]]

        def __rich_repr__(self):
            yield "graphs", self.graphs
            yield "total_repr_map", self.total_repr_map

        def _print(self):
            from rich import print as rprint

            rprint(self)

    @dataclass
    class IterationState:
        dirty: bool

    def __init__(self) -> None:
        super().__init__()

        self.superset_cache: dict[Parameter, tuple[int, P_Set]] = {}

    def has_no_solution(
        self, total_repr_map: dict[ParameterOperatable, ParameterOperatable.All]
    ) -> bool:
        # any parameter is/subset literal is empty (implcit constraint that we forgot)
        # any constrained expression got mapped to False
        # any constrained expression literal is False
        raise NotImplementedError()

    @classmethod
    def _run_iteration(
        cls,
        iterno: int,
        data: IterationData,
        algos: list[SolverAlgorithm],
        print_context: ParameterOperatable.ReprContext,
        phase_offset: int = 0,
    ) -> tuple[IterationData, IterationState, ParameterOperatable.ReprContext]:
        iteration_state = DefaultSolver.IterationState(dirty=False)
        iteration_repr_maps: list[REPR_MAP] = []

        for phase_name, algo in enumerate(algos):
            phase_name = str(phase_name + phase_offset)

            if PRINT_START:
                logger.debug(
                    f"START Iteration {iterno} Phase 2.{phase_name}: {algo.name}"
                    f" G:{len(data.graphs)}"
                )

            mutator = Mutator(
                *data.graphs,
                algo=algo,
                print_context=print_context,
                last_run_operables=data.output_operables.get(algo),
            )
            mutator.run()
            algo_result = mutator.close()

            if algo_result.dirty and logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"DONE  Iteration {iterno} Phase 1.{phase_name}: {algo.name} "
                    f"G:{len(data.graphs)}"
                )
                print_context = mutator.debug_print() or print_context

            # TODO assert all new graphs

            iteration_state.dirty |= algo_result.dirty
            # TODO: optimize so only dirty
            if not algo.single:
                data.output_operables[algo] = mutator.get_output_operables()

            if algo_result.dirty:
                data.graphs = algo_result.graphs
                iteration_repr_maps.append(algo_result.repr_map)
                # TODO implement nicer
                # map output_operables through new repr_map
                for s, d in algo_result.repr_map.items():
                    for v_ops in data.output_operables.values():
                        if s in v_ops:
                            v_ops.remove(s)
                            v_ops.add(d)

        data.total_repr_map = Mutator.create_concat_repr_map(
            data.total_repr_map.repr_map, *iteration_repr_maps
        )

        return data, iteration_state, print_context

    @times_out(TIMEOUT)
    def simplify_symbolically(
        self,
        g: Graph,
        print_context: ParameterOperatable.ReprContext | None = None,
        destructive: bool = True,
    ) -> tuple[Mutator.ReprMap, ParameterOperatable.ReprContext]:
        """
        Args:
        - destructive: if False, no destructive algorithms are allowed
        """
        if not destructive:
            raise NotImplementedError()

        now = time.time()
        if LOG_PICK_SOLVE:
            logger.info("Phase 1 Solving: Analytical Solving ".ljust(80, "="))

        print_context_ = print_context or ParameterOperatable.ReprContext()
        if S_LOG:
            debug_name_mappings(print_context_, g)
            Mutator.print_all(g, context=print_context_, type_filter=Expression)

        iter_data = DefaultSolver.IterationData(
            graphs=[g],
            total_repr_map=Mutator.ReprMap(
                {po: po for po in GraphFunctions(g).nodes_of_type(ParameterOperatable)}
            ),
            output_operables={},
        )
        for iterno in count():
            first_iter = iterno == 0

            if iterno > MAX_ITERATIONS_HEURISTIC:
                raise Exception(
                    "Solver Bug: Too many iterations, likely stuck in a loop"
                )
            v_count = sum(
                len(GraphFunctions(g).nodes_of_type(ParameterOperatable))
                for g in iter_data.graphs
            )
            logger.debug(
                (
                    f"Iteration {iterno} "
                    f"|graphs|: {len(iter_data.graphs)}, |V|: {v_count}"
                ).ljust(80, "-")
            )

            try:
                iter_data, iteration_state, print_context_ = (
                    DefaultSolver._run_iteration(
                        iterno=iterno,
                        data=iter_data,
                        algos=self.algorithms.pre
                        if first_iter
                        else self.algorithms.iterative,
                        print_context=print_context_,
                    )
                )
            finally:
                if S_LOG:
                    Mutator.print_all(*iter_data.graphs, context=print_context_)

            if not iteration_state.dirty:
                break

            if not len(iter_data.graphs):
                break

        if LOG_PICK_SOLVE:
            logger.info(
                f"Phase 1 Solving: Analytical Solving done in {iterno} iterations"
                f" and {time.time() - now:.3f} seconds".ljust(80, "=")
            )

        return iter_data.total_repr_map, print_context_

    @override
    def get_any_single(
        self,
        operatable: Parameter,
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Any:
        # TODO
        if suppose_constraint is not None:
            raise NotImplementedError()

        # TODO
        if minimize is not None:
            raise NotImplementedError()

        lit = self.inspect_get_known_supersets(operatable)
        out = lit.any()
        if lock:
            operatable.alias_is(out)
        return out

    @override
    def find_and_lock_solution(self, G: Graph) -> Solver.SolveResultAll:
        return Solver.SolveResultAll(
            timed_out=False,
            has_solution=True,
        )
        # raise NotImplementedError()

    # IMPORTANT ------------------------------------------------------------------------

    # TODO: Could be exponentially many
    @override
    def inspect_get_known_supersets(
        self, param: Parameter, force_update: bool = False
    ) -> P_Set:
        all_params = GraphFunctions(param.get_graph()).nodes_of_type(
            ParameterOperatable
        )
        g_hash = hash(tuple(sorted(all_params, key=id)))
        cached = self.superset_cache.get(param, (None, None))[0]
        if cached == g_hash or (cached is not None and not force_update):
            return self.superset_cache[param][1]

        out, repr_map = self._inspect_get_known_supersets(param)
        self.superset_cache[param] = g_hash, out

        if repr_map:
            for p in all_params:
                if not isinstance(p, Parameter):
                    continue
                lit = repr_map.try_get_literal(p, allow_subset=True)
                if lit is None:
                    lit = p.domain_set()
                self.superset_cache[p] = g_hash, P_Set.from_value(lit)

        return out

    def _inspect_get_known_supersets(
        self, param: Parameter
    ) -> tuple[P_Set, Mutator.ReprMap | None]:
        lit = param.try_get_literal()
        if lit is not None:
            return P_Set.from_value(lit), None

        # run phase 1 solver
        # TODO caching
        repr_map, print_context = self.simplify_symbolically(param.get_graph())
        if param not in repr_map.repr_map:
            if LOG_PICK_SOLVE:
                logger.warning(f"Parameter {param} not in repr_map")
            return param.domain_set(), repr_map

        # check predicates (is, subset), (ge, le covered too)
        literal = repr_map.try_get_literal(param, allow_subset=True)

        if literal is None:
            return param.domain_set(), repr_map

        return P_Set.from_value(literal), repr_map

    @override
    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Solver.SolveResultAny[ArgType]:
        # TODO
        if suppose_constraint is not None:
            raise NotImplementedError()

        # TODO
        if minimize is not None:
            raise NotImplementedError()

        if not predicates:
            raise ValueError("No predicates given")

        result = Solver.SolveResultAny(
            timed_out=False,
            true_predicates=[],
            false_predicates=[],
            unknown_predicates=[],
        )

        print_context = ParameterOperatable.ReprContext()

        it = iter(predicates)

        for p in it:
            pred, _ = p
            assert not pred.constrained
            pred.constrained = True
            try:
                repr_map, print_context_new = self.simplify_symbolically(
                    pred.get_graph(), print_context=print_context
                )
                # FIXME: is this correct?
                # definitely breaks a lot
                new_Gs = get_graphs(repr_map.repr_map.values())
                repr_pred = repr_map.repr_map.get(pred)

                # FIXME: workaround for above
                if repr_pred is not None:
                    new_Gs = [repr_pred.get_graph()]

                new_preds = [
                    n
                    for new_G in new_Gs
                    for n in GraphFunctions(new_G).nodes_of_type(
                        ConstrainableExpression
                    )
                ]
                not_deducted = [
                    p
                    for p in new_preds
                    if p.constrained and not p._solver_evaluates_to_true
                ]

                if not_deducted:
                    logger.warning(
                        f"PREDICATE not deducible: {pred.compact_repr(print_context)}"
                        + (
                            f" -> {repr_pred.compact_repr(print_context_new)}"
                            if repr_pred is not None
                            else ""
                        )
                    )
                    logger.warning(
                        f"NOT DEDUCED: \n    {'\n    '.join([
                            p.compact_repr(print_context_new) for p in not_deducted])}"
                    )

                    if LOG_PICK_SOLVE:
                        debug_name_mappings(
                            print_context, pred.get_graph(), print_out=logger.warning
                        )
                        not_deduced_grouped = groupby(
                            not_deducted, key=lambda p: p.get_graph()
                        )
                        for g, _ in not_deduced_grouped.items():
                            Mutator.print_all(
                                g,
                                context=print_context_new,
                                print_out=logger.warning,
                            )

                    result.unknown_predicates.append(p)
                    continue

                result.true_predicates.append(p)
                # This is allowed, but we might want to add an option to prohibit
                # short-circuiting
                break

            except Contradiction as e:
                if LOG_PICK_SOLVE:
                    logger.warning(f"CONTRADICTION: {pred.compact_repr(print_context)}")
                    logger.warning(f"CAUSE: {e}")
                result.false_predicates.append(p)
            except TimeoutError:
                result.unknown_predicates.append(p)
            finally:
                pred.constrained = False

        result.unknown_predicates.extend(it)

        if lock and result.true_predicates:
            if len(result.true_predicates) > 1:
                # TODO, move this decision to caller (see short-circuiting)
                logger.warning("Multiple true predicates, locking first")
            result.true_predicates[0][0].constrain()

        return result
