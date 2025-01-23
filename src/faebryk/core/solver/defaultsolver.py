# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from dataclasses import dataclass
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
from faebryk.core.solver.mutator import REPR_MAP, AlgoResult, Mutators
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.core.solver.utils import (
    MAX_ITERATIONS,
    PRINT_START,
    S_LOG,
    Contradiction,
    SolverAlgorithm,
    SolverLiteral,
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

    # TODO actually use this...
    timeout: int = 1000

    algorithms = SimpleNamespace(
        pre=[
            canonical.constrain_within_domain,
            canonical.convert_to_canonical_literals,
            canonical.convert_to_canonical_operations,
        ],
        iterative=[
            analytical.remove_unconstrained,
            analytical.convert_operable_aliased_to_single_into_literal,
            analytical.remove_congruent_expressions,
            analytical.resolve_alias_classes,
            analytical.convert_inequality_with_literal_to_subset,
            analytical.compress_associative,
            analytical.fold_literals,
            analytical.merge_intersect_subsets,
            analytical.predicate_literal_deduce,
            analytical.predicate_unconstrained_operands_deduce,
            analytical.empty_set,
            analytical.transitive_subset,
            analytical.isolate_lone_params,
            analytical.uncorrelated_alias_fold,
            analytical.remove_empty_graphs,
        ],
        subset_dirty=[analytical.upper_estimation_of_expressions_with_subsets],
    )

    @dataclass
    class IterationData:
        graphs: list[Graph]
        total_repr_map: Mutators.ReprMap
        param_ops_subset_literals: dict[ParameterOperatable, SolverLiteral | None]

        def __rich_repr__(self):
            yield "graphs", self.graphs
            yield "total_repr_map", self.total_repr_map
            yield "param_ops_subset_literals", self.param_ops_subset_literals

        def _print(self):
            from rich import print as rprint

            rprint(self)

    @dataclass
    class IterationState:
        dirty: bool
        subset_dirty: bool

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
    def _run_algo(
        cls,
        iterno: int,
        graphs: list[Graph],
        phase_name: str,
        algo: SolverAlgorithm,
        print_context: ParameterOperatable.ReprContext,
    ) -> tuple[AlgoResult, ParameterOperatable.ReprContext]:
        if PRINT_START:
            logger.debug(
                f"START Iteration {iterno} Phase 1.{phase_name}: {algo.name}"
                f" G:{len(graphs)}"
            )
        mutators = Mutators(*graphs, print_context=print_context)
        mutators.run(algo)
        algo_result = mutators.close()
        # TODO remove
        if algo_result.dirty:
            logger.debug(
                f"DONE  Iteration {iterno} Phase 1.{phase_name}: {algo.name} "
                f"G:{len(graphs)}"
            )
            print_context = mutators.debug_print() or print_context
        # TODO assert all new graphs

        return algo_result, print_context

    @classmethod
    def _run_algos(
        cls,
        iterno: int,
        data: IterationData,
        algos: list[SolverAlgorithm],
        print_context: ParameterOperatable.ReprContext,
        phase_offset: int = 0,
    ) -> tuple[IterationData, IterationState, ParameterOperatable.ReprContext]:
        iteration_state = DefaultSolver.IterationState(dirty=False, subset_dirty=False)
        iteration_repr_maps: list[REPR_MAP] = []
        tracked_param_ops = {
            data.total_repr_map.repr_map[po]
            for po in data.param_ops_subset_literals.keys()
            if po in data.total_repr_map.repr_map
        }

        for phase_name, algo in enumerate(algos):
            phase_name = str(phase_name + phase_offset)

            if PRINT_START:
                logger.debug(
                    f"START Iteration {iterno} Phase 2.{phase_name}: {algo.name}"
                    f" G:{len(data.graphs)}"
                )

            mutators = Mutators(
                *data.graphs,
                tracked_param_ops=tracked_param_ops,
                print_context=print_context,
            )
            mutators.run(algo)
            algo_result = mutators.close()

            # TODO remove
            if algo_result.dirty:
                logger.debug(
                    f"DONE  Iteration {iterno} Phase 1.{phase_name}: {algo.name} "
                    f"G:{len(data.graphs)}"
                )
                print_context = mutators.debug_print() or print_context

            # TODO assert all new graphs

            iteration_state.dirty |= algo_result.dirty
            iteration_state.subset_dirty |= algo_result.subset_dirty

            if algo_result.dirty:
                data.graphs = algo_result.graphs
                iteration_repr_maps.append(algo_result.repr_map)

        data.total_repr_map = Mutators.create_concat_repr_map(
            data.total_repr_map.repr_map, *iteration_repr_maps
        )

        return data, iteration_state, print_context

    @classmethod
    def _run_initial_iteration(
        cls, data: IterationData, print_context: ParameterOperatable.ReprContext
    ) -> tuple[IterationData, ParameterOperatable.ReprContext]:
        data, _, print_context = DefaultSolver._run_algos(
            iterno=0,
            data=data,
            algos=cls.algorithms.pre,
            print_context=print_context,
        )

        # include new params generated by canonicalization
        new_params = {
            po: po
            for G in data.graphs
            for po in GraphFunctions(G).nodes_of_type(ParameterOperatable)
            if po not in data.total_repr_map.repr_map.values()
        }

        data.total_repr_map = Mutators.create_concat_repr_map(
            data.total_repr_map.repr_map | new_params
        )

        # Build initial subset literals
        data.param_ops_subset_literals = {
            po: data.total_repr_map.try_get_literal(po, allow_subset=True)
            for po in data.total_repr_map.repr_map
        }

        if S_LOG:
            Mutators.print_all(*data.graphs, context=print_context)

        return data, print_context

    @classmethod
    def _run_iteration(
        cls,
        iterno: int,
        data: IterationData,
        print_context: ParameterOperatable.ReprContext,
    ) -> tuple[IterationData, IterationState, ParameterOperatable.ReprContext]:
        data, iteration_state, print_context = DefaultSolver._run_algos(
            iterno=iterno,
            data=data,
            algos=cls.algorithms.iterative,
            print_context=print_context,
        )

        if iteration_state.dirty:
            # check which subset literals have changed for our old paramops
            subset_dirty = False
            for po in data.param_ops_subset_literals:
                if po not in data.total_repr_map.repr_map:
                    continue

                new_subset_literal = data.total_repr_map.try_get_literal(
                    po, allow_subset=True
                )

                if new_subset_literal != data.param_ops_subset_literals[po]:
                    logger.debug(
                        f"Subset dirty {data.param_ops_subset_literals[po]} != "
                        f"{new_subset_literal}"
                    )
                    data.param_ops_subset_literals[po] = new_subset_literal
                    subset_dirty = True

            # TODO: remove (and remaining unused subset_dirty logic)
            if iteration_state.subset_dirty != subset_dirty:
                print("SUBSET DIRTY MISMATCH")

            if iteration_state.subset_dirty or iterno <= 1:
                logger.debug(
                    "Subset dirty, running subset dirty algorithms"
                    if subset_dirty
                    else "Iteration 1, running subset dirty algorithms"
                )

                data, _, print_context = DefaultSolver._run_algos(
                    iterno=iterno,
                    data=data,
                    algos=cls.algorithms.subset_dirty,
                    print_context=print_context,
                    phase_offset=len(cls.algorithms.iterative),
                )

        if S_LOG:
            Mutators.print_all(*data.graphs, context=print_context)

        return data, iteration_state, print_context

    @times_out(120)
    def phase_1_simplify_analytically(
        self, g: Graph, print_context: ParameterOperatable.ReprContext | None = None
    ):
        now = time.time()
        if LOG_PICK_SOLVE:
            logger.info("Phase 1 Solving: Analytical Solving ".ljust(80, "="))

        # TODO move into comment here
        # strategies
        # https://www.notion.so/Phase1-136836dcad9480cbb037defe359934ee?pvs=4#136836dcad94807d93bccb14598e1ef0

        print_context_ = print_context or ParameterOperatable.ReprContext()
        if S_LOG:
            debug_name_mappings(print_context_, g)
            Mutators.print_all(g, context=print_context_, type_filter=Expression)

        iter_data, print_context_ = DefaultSolver._run_initial_iteration(
            data=DefaultSolver.IterationData(
                graphs=[g],
                total_repr_map=Mutators.ReprMap({}),
                param_ops_subset_literals={},
            ),
            print_context=print_context_,
        )

        iterno = 0
        any_dirty = True
        while any_dirty and len(iter_data.graphs) > 0:
            iterno += 1
            # TODO remove
            if iterno > MAX_ITERATIONS:
                raise Exception("Too many iterations")
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

            iter_data, iteration_state, print_context_ = DefaultSolver._run_iteration(
                iterno, iter_data, print_context_
            )

            any_dirty = iteration_state.dirty

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
    ) -> tuple[P_Set, Mutators.ReprMap | None]:
        lit = param.try_get_literal()
        if lit is not None:
            return P_Set.from_value(lit), None

        # run phase 1 solver
        # TODO caching
        repr_map, print_context = self.phase_1_simplify_analytically(param.get_graph())
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
                repr_map, print_context_new = self.phase_1_simplify_analytically(
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
                            Mutators.print_all(
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
