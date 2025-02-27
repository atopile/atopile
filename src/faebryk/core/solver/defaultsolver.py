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
from faebryk.core.solver.mutator import (
    MutationMap,
    MutationStage,
    Mutator,
    Transformations,
)
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
    get_graphs,
)
from faebryk.libs.logging import NET_LINE_WIDTH
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint
from faebryk.libs.sets.sets import P_Set, as_lit
from faebryk.libs.test.times import Times
from faebryk.libs.units import dimensionless, quantity
from faebryk.libs.util import not_none, times_out

logger = logging.getLogger(__name__)

if S_LOG:
    logger.setLevel(logging.DEBUG)


class DefaultSolver(Solver):
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
        mutation_map: MutationMap

    @dataclass
    class IterationState:
        dirty: bool

    @dataclass
    class SolverState:
        data: "DefaultSolver.IterationData"

    def __init__(self) -> None:
        super().__init__()

        self.state: DefaultSolver.SolverState | None = None
        self.reusable_state: DefaultSolver.SolverState | None = None

    @classmethod
    def _run_iteration(
        cls,
        iterno: int,
        data: IterationData,
        algos: list[SolverAlgorithm],
        terminal: bool,
    ) -> "DefaultSolver.IterationState":
        iteration_state = DefaultSolver.IterationState(dirty=False)
        timings = Times(name="run_iteration")

        for phase_name, algo in enumerate(algos):
            timings.add("_")

            if PRINT_START:
                logger.debug(
                    f"START Iteration {iterno} Phase 2.{phase_name}: {algo.name}"
                    f" G:{len(data.mutation_map.output_graphs)}"
                )

            mutator = Mutator(
                data.mutation_map,
                algo=algo,
                terminal=terminal,
                iteration=iterno,
            )
            algo_result = mutator.run()

            if algo_result.dirty and logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"DONE  Iteration {iterno} Phase 1.{phase_name}: {algo.name} "
                    f"G:{len(data.mutation_map.output_graphs)}"
                )
                # atm only one stage
                algo_result.mutation_stage.print_mutation_table()

            iteration_state.dirty |= algo_result.dirty
            data.mutation_map = data.mutation_map.extend(algo_result.mutation_stage)

            timings.add(
                f"{algo.name}"
                f" {'terminal' if terminal else 'non-terminal'}"
                f" {'dirty' if algo_result.dirty else 'clean'}"
            )

        return iteration_state

    def _create_or_resume_state(
        self, print_context: ParameterOperatable.ReprContext | None, *gs: Graph | Node
    ):
        # TODO consider not getting full graph of node gs, but scope to only relevant
        _gs = get_graphs(gs)

        if self.reusable_state is None:
            return DefaultSolver.SolverState(
                data=DefaultSolver.IterationData(
                    mutation_map=MutationMap.identity(*_gs, print_context=print_context)
                ),
            )

        if print_context is not None:
            raise ValueError("print_context not allowed when using reusable state")

        mutation_map = self.reusable_state.data.mutation_map
        p_ops = GraphFunctions(*_gs).nodes_of_type(ParameterOperatable)
        new_p_ops = p_ops - mutation_map.first_stage.input_operables

        # TODO consider using mutator
        transforms = Transformations.identity(
            *mutation_map.last_stage.output_graphs,
            input_print_context=mutation_map.output_print_context,
        )

        # inject new parameters
        new_params = [p for p in new_p_ops if isinstance(p, Parameter)]
        for p in new_params:
            # strip units and copy (for decoupling from old graph)
            transforms.mutated[p] = Parameter(
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

        # inject new expressions
        new_exprs = {e for e in new_p_ops if isinstance(e, Expression)}
        for e in ParameterOperatable.sort_by_depth(new_exprs, ascending=True):
            if S_LOG:
                logger.debug(
                    f"injecting {e.compact_repr(mutation_map.input_print_context)}"
                )
            op_mapped = []
            for op in e.operands:
                if op in transforms.mutated:
                    op_mapped.append(transforms.mutated[op])
                    continue
                if isinstance(op, ParameterOperatable) and mutation_map.is_removed(op):
                    # TODO
                    raise Exception("Using removed operand")
                if op in mutation_map.first_stage.input_operables:
                    op_mapped.append(not_none(mutation_map.map_forward(op).maps_to))
                    continue
                if ParameterOperatable.is_literal(op):
                    op = as_lit(op)
                    if isinstance(op, Quantity_Interval_Disjoint):
                        op = op.to_dimensionless()
                op_mapped.append(op)
            e_mapped = type(e)(*op_mapped)
            transforms.mutated[e] = e_mapped
            if isinstance(e, ConstrainableExpression) and e.constrained:
                assert isinstance(e_mapped, ConstrainableExpression)
                e_mapped.constrained = True

        return DefaultSolver.SolverState(
            data=DefaultSolver.IterationData(
                mutation_map.extend(
                    MutationStage(
                        "resume_state",
                        iteration=0,
                        transformations=transforms,
                        print_context=mutation_map.output_print_context,
                    )
                )
            ),
        )

    @times_out(TIMEOUT)
    def simplify_symbolically(
        self,
        *gs: Graph | Node,
        print_context: ParameterOperatable.ReprContext | None = None,
        terminal: bool = True,
    ) -> SolverState:
        """
        Args:
        - terminal: if True, result of simplication can't be reused, but simplification
            is more powerful
        """
        timings = Times(name="simplify")

        now = time.time()
        if LOG_PICK_SOLVE:
            logger.info("Phase 1 Solving: Symbolic Solving ".ljust(NET_LINE_WIDTH, "="))

        self.state = self._create_or_resume_state(print_context, *gs)

        if S_LOG:
            self.state.data.mutation_map.print_name_mappings()
            self.state.data.mutation_map.last_stage.print_graph_contents(Expression)

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
            logger.debug(
                (f"Iteration {iterno} {self.state.data.mutation_map}").ljust(
                    NET_LINE_WIDTH, "-"
                )
            )

            try:
                iteration_state = DefaultSolver._run_iteration(
                    iterno=iterno,
                    data=self.state.data,
                    terminal=terminal,
                    algos=pre_algos if first_iter else it_algos,
                )
            except:
                if S_LOG:
                    self.state.data.mutation_map.last_stage.print_graph_contents()
                raise

            if not iteration_state.dirty:
                break

            if not len(self.state.data.mutation_map.output_graphs):
                break

            if S_LOG:
                self.state.data.mutation_map.last_stage.print_graph_contents()

        if LOG_PICK_SOLVE:
            logger.info(
                f"Phase 1 Solving: Analytical Solving done in {iterno} iterations"
                f" and {time.time() - now:.3f} seconds".ljust(NET_LINE_WIDTH, "=")
            )

        timings.add("terminal" if terminal else "non-terminal")

        if not terminal:
            self.reusable_state = self.state

        return self.state

    @override
    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        print_context: ParameterOperatable.ReprContext | None = None,
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

        it = iter(predicates)

        for p in it:
            pred, _ = p
            assert not pred.constrained
            pred.constrained = True
            try:
                solver_result = self.simplify_symbolically(
                    pred.get_graph(), terminal=True
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
                solver_result = self.state
            finally:
                pred.constrained = False

            repr_map = solver_result.data.mutation_map

            # FIXME: is this correct?
            # definitely breaks a lot
            new_Gs = repr_map.output_graphs
            repr_pred = repr_map.map_forward(pred).maps_to
            print_context_new = repr_map.output_print_context

            # FIXME: workaround for above
            if repr_pred is not None:
                new_Gs = [repr_pred.get_graph()]

            new_preds = GraphFunctions(*new_Gs).nodes_of_type(ConstrainableExpression)
            not_deducted = [
                p for p in new_preds if p.constrained and not p._solver_terminated
            ]

            if not_deducted:
                if LOG_PICK_SOLVE:
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

                    repr_map.print_name_mappings(log=logger.warning)
                    repr_map.last_stage.print_graph_contents(log=logger.warning)

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

    def update_superset_cache(self, *nodes: Node):
        try:
            self.simplify_symbolically(*nodes, terminal=True)
        except TimeoutError:
            if not ALLOW_PARTIAL_STATE:
                raise
            if self.state is None:
                raise

    def inspect_get_known_supersets(self, value: Parameter) -> P_Set:
        """
        Careful, only use after solver ran!
        """
        if not self.state:
            lit = value.try_get_literal_subset()
            if lit is None:
                return value.domain_set()
            return lit

        return not_none(
            self.state.data.mutation_map.try_get_literal(
                value, allow_subset=True, domain_default=True
            )
        )

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
