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
from faebryk.core.solver.mutator import REPR_MAP, Mutator, ReprMap
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
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint
from faebryk.libs.sets.sets import P_Set, as_lit
from faebryk.libs.test.times import Times
from faebryk.libs.units import dimensionless, quantity
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
        total_repr_map: ReprMap
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

        self.state: DefaultSolver.PartialState | None = None
        self.simplified_state: DefaultSolver.PartialState | None = None

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
        terminal: bool,
        phase_offset: int = 0,
    ) -> tuple[IterationState, ParameterOperatable.ReprContext]:
        iteration_state = DefaultSolver.IterationState(dirty=False)
        iteration_repr_maps: list[REPR_MAP] = []

        timings = Times(name="run_iteration")

        for phase_name, algo in enumerate(algos):
            phase_name = str(phase_name + phase_offset)

            if PRINT_START:
                logger.debug(
                    f"START Iteration {iterno} Phase 2.{phase_name}: {algo.name}"
                    f" G:{len(data.graphs)}"
                )

            timings.add("_")
            mutator = Mutator(
                *data.graphs,
                algo=algo,
                terminal=terminal,
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
                data.repr_since_last_iteration[algo] = REPR_MAP(
                    {k: k for k in mutator.get_output_operables()}
                )

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
            timings.add(
                f"{algo.name}"
                f" {'terminal' if terminal else 'non-terminal'}"
                f" {'dirty' if algo_result.dirty else 'clean'}"
            )

        data.total_repr_map = ReprMap.create_concat_repr_map(
            data.total_repr_map.repr_map, *iteration_repr_maps
        )

        return iteration_state, print_context

    def create_or_resume_state(
        self, print_context: ParameterOperatable.ReprContext | None, *gs: Graph | Node
    ):
        # TODO consider not getting full graph of node gs, but scope to only relevant
        _gs = get_graphs(gs)

        if self.simplified_state is None:
            print_context_ = print_context or ParameterOperatable.ReprContext()

            self.state = DefaultSolver.PartialState(
                data=DefaultSolver.IterationData(
                    graphs=_gs,
                    total_repr_map=ReprMap.create_from_graphs(*_gs),
                    repr_since_last_iteration={},
                ),
                print_context=print_context_,
            )
            return

        # TODO this function is unreadable, refactor and document
        # TODO consider using mutator

        if print_context is not None:
            # TODO
            logger.warning("Ignoring supplied print_context")
            # raise ValueError("print_context not allowed when using simplified state")

        print_context_ = self.simplified_state.print_context
        repr_map = self.simplified_state.data.total_repr_map

        p_ops = GraphFunctions(*_gs).nodes_of_type(ParameterOperatable)
        new_p_ops = {
            p_op
            for p_op in p_ops
            if p_op not in repr_map.repr_map and not repr_map.is_removed(p_op)
        }

        repr_map_new = REPR_MAP(repr_map.repr_map)

        # mutate new parameters
        new_params = [p for p in new_p_ops if isinstance(p, Parameter)]
        for p in new_params:
            # strip units and copy (for decoupling from old graph)
            repr_map_new[p] = Parameter(
                domain=p.domain,
                tolerance_guess=p.tolerance_guess,
                likely_constrained=p.likely_constrained,
                units=dimensionless,
                soft_set=as_lit(p.soft_set).to_dimensionless()
                if p.soft_set is not None
                else None,
                within=as_lit(p.within).to_dimensionless()
                if p.within is not None
                else None,
                guess=quantity(p.guess, dimensionless) if p.guess is not None else None,
            )

        # mutate new expressions
        new_exprs = {e for e in new_p_ops if isinstance(e, Expression)}
        for e in ParameterOperatable.sort_by_depth(new_exprs, ascending=True):
            op_mapped = []
            for op in e.operands:
                if op in repr_map_new:
                    op_mapped.append(repr_map_new[op])
                    continue
                if repr_map.is_removed(op):
                    # TODO
                    raise Exception("Using removed operand")
                if ParameterOperatable.is_literal(op):
                    op = as_lit(op)
                    if isinstance(op, Quantity_Interval_Disjoint):
                        op = op.to_dimensionless()
                op_mapped.append(op)
            e_mapped = type(e)(*op_mapped)
            repr_map_new[e] = e_mapped
            if isinstance(e, ConstrainableExpression) and e.constrained:
                assert isinstance(e_mapped, ConstrainableExpression)
                e_mapped.constrained = True

        graphs = get_graphs(repr_map_new.values())

        self.state = DefaultSolver.PartialState(
            data=DefaultSolver.IterationData(
                graphs=list(graphs),
                total_repr_map=ReprMap(repr_map_new, removed=repr_map.removed),
                repr_since_last_iteration={},
            ),
            print_context=print_context_,
        )

    @times_out(TIMEOUT)
    def simplify_symbolically(
        self,
        *gs: Graph | Node,
        print_context: ParameterOperatable.ReprContext | None = None,
        terminal: bool = True,
    ) -> tuple[ReprMap, ParameterOperatable.ReprContext]:
        """
        Args:
        - terminal: if False, no terminal algorithms are allowed
        """
        timings = Times(name="simplify")

        now = time.time()
        if LOG_PICK_SOLVE:
            logger.info("Phase 1 Solving: Symbolic Solving ".ljust(80, "="))

        self.create_or_resume_state(print_context, *gs)
        assert self.state is not None

        if S_LOG:
            _gs = self.state.data.graphs
            debug_name_mappings(self.state.print_context, *_gs)
            Mutator.print_all(
                *_gs, context=self.state.print_context, type_filter=Expression
            )

        pre_algos = self.algorithms.pre
        it_algos = self.algorithms.iterative
        if not terminal:
            pre_algos = [a for a in pre_algos if not a.terminal]
            it_algos = [a for a in it_algos if not a.terminal]

        for iterno in count():
            first_iter = iterno == 0

            if iterno > MAX_ITERATIONS_HEURISTIC:
                raise TimeoutError(
                    "Solver Bug: Too many iterations, likely stuck in a loop"
                )
            v_count = sum(
                len(GraphFunctions(g).nodes_of_type(ParameterOperatable))
                for g in self.state.data.graphs
            )
            logger.debug(
                (
                    f"Iteration {iterno} "
                    f"|graphs|: {len(self.state.data.graphs)}, |V|: {v_count}"
                ).ljust(80, "-")
            )

            try:
                iteration_state, self.state.print_context = (
                    DefaultSolver._run_iteration(
                        iterno=iterno,
                        data=self.state.data,
                        terminal=terminal,
                        algos=pre_algos if first_iter else it_algos,
                        print_context=self.state.print_context,
                    )
                )
            except:
                if S_LOG:
                    Mutator.print_all(
                        *self.state.data.graphs,
                        context=self.state.print_context,
                    )
                raise

            if not iteration_state.dirty:
                break

            if not len(self.state.data.graphs):
                break

            if S_LOG:
                Mutator.print_all(
                    *self.state.data.graphs,
                    context=self.state.print_context,
                )

        if LOG_PICK_SOLVE:
            logger.info(
                f"Phase 1 Solving: Analytical Solving done in {iterno} iterations"
                f" and {time.time() - now:.3f} seconds".ljust(80, "=")
            )

        timings.add("terminal" if terminal else "non-terminal")

        if not terminal:
            self.simplified_state = self.state

        return self.state.data.total_repr_map, self.state.print_context

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
            if self.state is None:
                raise
            repr_map = self.state.data.total_repr_map

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
                if self.state is None:
                    result.unknown_predicates.append(p)
                    continue
                repr_map, print_context_new = (
                    self.state.data.total_repr_map,
                    self.state.print_context,
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

    @override
    def simplify(self, *gs: Graph | Node):
        self.simplify_symbolically(*gs, terminal=False)
