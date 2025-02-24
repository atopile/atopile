# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from dataclasses import dataclass
from itertools import count
from types import SimpleNamespace
from typing import Any, override

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.node import Node
from faebryk.core.parameter import (
    ConstrainableExpression,
    Expression,
    Parameter,
    ParameterOperatable,
    Predicate,
)
from faebryk.core.solver.mutator import REPR_MAP, Mutator
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.core.solver.symbolic import (
    canonical,
    expression_groups,
    expression_wise,
    pure_literal,
    structural,
)
from faebryk.core.solver.utils import (
    ALLOW_PARTIAL_STATE,
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
from faebryk.libs.test.times import Times
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
            canonical.convert_to_canonical_literals,
            canonical.convert_to_canonical_operations,
            canonical.constrain_within_domain,
            canonical.alias_predicates_to_true,
        ],
        iterative=[
            structural.check_literal_contradiction,
            structural.remove_unconstrained,
            structural.convert_operable_aliased_to_single_into_literal,
            structural.resolve_alias_classes,
            structural.distribute_literals_across_alias_classes,
            structural.remove_congruent_expressions,
            structural.convert_inequality_with_literal_to_subset,
            expression_groups.associative_flatten,
            expression_groups.reflexive_predicates,
            expression_groups.idempotent_deduplicate,
            expression_groups.idempotent_unpack,
            expression_groups.involutory_fold,
            expression_groups.unary_identity_unpack,
            pure_literal.fold_pure_literal_expressions,
            *expression_wise.fold_algorithms,
            structural.merge_intersect_subsets,
            structural.predicate_flat_terminate,
            structural.predicate_unconstrained_operands_deduce,
            structural.predicate_terminated_is_true,
            structural.empty_set,
            structural.transitive_subset,
            structural.isolate_lone_params,
            structural.uncorrelated_alias_fold,
            structural.upper_estimation_of_expressions_with_subsets,
        ],
    )

    @dataclass
    class IterationData:
        graphs: list[Graph]
        total_repr_map: Mutator.ReprMap
        repr_since_last_iteration: dict[SolverAlgorithm, REPR_MAP]

        def __rich_repr__(self):
            yield "graphs", self.graphs
            yield "total_repr_map", self.total_repr_map

        def _print(self):
            from rich import print as rprint

            rprint(self)

    @dataclass
    class IterationState:
        dirty: bool

    @dataclass
    class PartialState:
        data: "DefaultSolver.IterationData"
        print_context: ParameterOperatable.ReprContext

    def __init__(self) -> None:
        super().__init__()

        self.superset_cache: dict[Parameter, tuple[int, P_Set]] = {}

        self.partial_state: DefaultSolver.PartialState | None = None

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
    ) -> tuple[IterationState, ParameterOperatable.ReprContext]:
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
                iteration_repr_map=data.repr_since_last_iteration.get(algo),
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
                data.repr_since_last_iteration[algo] = {
                    k: k for k in mutator.get_output_operables()
                }

            if algo_result.dirty:
                data.graphs = algo_result.graphs
                iteration_repr_maps.append(algo_result.repr_map)
                # append to per-algo iteration repr_map
                assert algo_result.repr_map
                for _algo, reprs in data.repr_since_last_iteration.items():
                    if _algo is algo:
                        continue
                    for old_s, old_d in list(reprs.items()):
                        new_d = algo_result.repr_map.get(old_d)
                        if new_d is None:
                            del reprs[old_s]
                            continue
                        reprs[old_s] = new_d

        data.total_repr_map = Mutator.create_concat_repr_map(
            data.total_repr_map.repr_map, *iteration_repr_maps
        )

        return iteration_state, print_context

    @times_out(TIMEOUT)
    def simplify_symbolically(
        self,
        *gs: Graph,
        print_context: ParameterOperatable.ReprContext | None = None,
        terminal: bool = True,
    ) -> tuple[Mutator.ReprMap, ParameterOperatable.ReprContext]:
        """
        Args:
        - terminal: if False, no terminal algorithms are allowed
        """
        timings = Times(name="simplify")

        if not terminal:
            raise NotImplementedError()

        now = time.time()
        if LOG_PICK_SOLVE:
            logger.info("Phase 1 Solving: Analytical Solving ".ljust(80, "="))

        print_context_ = print_context or ParameterOperatable.ReprContext()
        if S_LOG:
            debug_name_mappings(print_context_, *gs)
            Mutator.print_all(*gs, context=print_context_, type_filter=Expression)

        self.partial_state = DefaultSolver.PartialState(
            data=DefaultSolver.IterationData(
                graphs=list(gs),
                total_repr_map=Mutator.ReprMap(
                    {
                        po: po
                        for g in gs
                        for po in GraphFunctions(g).nodes_of_type(ParameterOperatable)
                    }
                ),
                repr_since_last_iteration={},
            ),
            print_context=print_context_,
        )

        for iterno in count():
            first_iter = iterno == 0

            if iterno > MAX_ITERATIONS_HEURISTIC:
                raise TimeoutError(
                    "Solver Bug: Too many iterations, likely stuck in a loop"
                )
            v_count = sum(
                len(GraphFunctions(g).nodes_of_type(ParameterOperatable))
                for g in self.partial_state.data.graphs
            )
            logger.debug(
                (
                    f"Iteration {iterno} "
                    f"|graphs|: {len(self.partial_state.data.graphs)}, |V|: {v_count}"
                ).ljust(80, "-")
            )

            try:
                iteration_state, self.partial_state.print_context = (
                    DefaultSolver._run_iteration(
                        iterno=iterno,
                        data=self.partial_state.data,
                        algos=self.algorithms.pre
                        if first_iter
                        else self.algorithms.iterative,
                        print_context=self.partial_state.print_context,
                    )
                )
            except:
                if S_LOG:
                    Mutator.print_all(
                        *self.partial_state.data.graphs,
                        context=self.partial_state.print_context,
                    )
                raise

            if not iteration_state.dirty:
                break

            if not len(self.partial_state.data.graphs):
                break

            if S_LOG:
                Mutator.print_all(
                    *self.partial_state.data.graphs,
                    context=self.partial_state.print_context,
                )

        if LOG_PICK_SOLVE:
            logger.info(
                f"Phase 1 Solving: Analytical Solving done in {iterno} iterations"
                f" and {time.time() - now:.3f} seconds".ljust(80, "=")
            )

        out = self.partial_state.data.total_repr_map, self.partial_state.print_context
        self.partial_state = None

        timings.add("total")

        return out

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

    @override
    def inspect_get_known_supersets(
        self, param: Parameter, force_update: bool = False
    ) -> P_Set:
        all_params = GraphFunctions(param.get_graph()).nodes_of_type(
            ParameterOperatable
        )
        g_hash = hash(tuple(sorted(all_params, key=id)))
        cached_g_hash = self.superset_cache.get(param, (None, None))[0]

        ignore_hash_mismatch = not force_update
        hash_match = cached_g_hash == g_hash
        no_cache = cached_g_hash is None
        valid_hash = hash_match or ignore_hash_mismatch

        if no_cache or not valid_hash:
            self.update_superset_cache(param)

        return self.superset_cache[param][1]

    def update_superset_cache(self, *nodes: Node):
        graphs = get_graphs(nodes)
        try:
            repr_map, _ = self.simplify_symbolically(*graphs)
        except TimeoutError:
            if not ALLOW_PARTIAL_STATE:
                raise
            if self.partial_state is None:
                raise
            repr_map = self.partial_state.data.total_repr_map

        for g in graphs:
            pos = GraphFunctions(g).nodes_of_type(ParameterOperatable)
            g_hash = hash(tuple(sorted(pos, key=id)))
            for p in pos:
                if not isinstance(p, Parameter):
                    continue
                lit = repr_map.try_get_literal(p, allow_subset=True)
                # during canonicalization we use domain set
                assert lit is not None
                self.superset_cache[p] = g_hash, lit

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
            except Contradiction as e:
                if LOG_PICK_SOLVE:
                    logger.warning(f"CONTRADICTION: {pred.compact_repr(print_context)}")
                    logger.warning(f"CAUSE: {e}")
                result.false_predicates.append(p)
                continue
            except TimeoutError:
                if LOG_PICK_SOLVE:
                    logger.warning(f"TIMEOUT: {pred.compact_repr(print_context)}")
                if not ALLOW_PARTIAL_STATE:
                    raise
                if self.partial_state is None:
                    result.unknown_predicates.append(p)
                    continue
                repr_map, print_context_new = (
                    self.partial_state.data.total_repr_map,
                    self.partial_state.print_context,
                )
            finally:
                pred.constrained = False

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
                for n in GraphFunctions(new_G).nodes_of_type(ConstrainableExpression)
            ]
            not_deducted = [
                p for p in new_preds if p.constrained and not p._solver_terminated
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

        result.unknown_predicates.extend(it)

        if lock and result.true_predicates:
            if len(result.true_predicates) > 1:
                # TODO, move this decision to caller (see short-circuiting)
                logger.warning("Multiple true predicates, locking first")
            result.true_predicates[0][0].constrain()

        return result
