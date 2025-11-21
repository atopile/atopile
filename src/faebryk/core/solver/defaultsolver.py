# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from dataclasses import dataclass
from itertools import count
from typing import Any, override

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import SolverAlgorithm
from faebryk.core.solver.mutator import (
    MutationMap,
    MutationStage,
    Mutator,
    Transformations,
    is_terminated,
)
from faebryk.core.solver.solver import LOG_PICK_SOLVE, NotDeducibleException, Solver
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
)
from faebryk.libs.logging import NET_LINE_WIDTH
from faebryk.libs.test.times import Times
from faebryk.libs.util import not_none, times_out

logger = logging.getLogger(__name__)

if S_LOG:
    logger.setLevel(logging.DEBUG)


class DefaultSolver(Solver):
    class algorithms:
        # TODO: get order from topo sort
        # and types from decorator
        pre = [
            canonical.convert_to_canonical_literals,
            canonical.convert_to_canonical_operations,
            canonical.constrain_within_domain,
            canonical.alias_predicates_to_true,
        ]
        iterative = [
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
        ]

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
                    f" G:{data.mutation_map.G_out.get_node_count()}"
                )

            mutator = Mutator(
                data.mutation_map,
                algo=algo,
                terminal=terminal,
                iteration=iterno,
            )

            timings.add("setup")
            now = time.perf_counter()
            mutator._run()
            run_time = time.perf_counter() - now
            timings.add("_")
            algo_result = mutator.close()

            if algo_result.dirty and logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"DONE  Iteration {iterno} Phase 1.{phase_name}: {algo.name} "
                    f"G:{data.mutation_map.G_out.get_node_count()}"
                )
                # atm only one stage
                # expensive
                if S_LOG:
                    algo_result.mutation_stage.print_mutation_table()

            iteration_state.dirty |= algo_result.dirty
            data.mutation_map = data.mutation_map.extend(algo_result.mutation_stage)

            timings.add(f"close {'dirty' if algo_result.dirty else 'clean'}")

            new_name = (
                f"{algo.name}"
                f" {'terminal' if terminal else 'non-terminal'}"
                f" {'dirty' if algo_result.dirty else 'clean'}"
            )
            timings._add(new_name, run_time)

        return iteration_state

    def _create_or_resume_state(
        self,
        print_context: F.Parameters.ReprContext | None,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
    ):
        # TODO consider not getting full graph of node gs, but scope to only relevant

        if self.reusable_state is None:
            return DefaultSolver.SolverState(
                data=DefaultSolver.IterationData(
                    mutation_map=MutationMap.identity(
                        tg, g, print_context=print_context
                    )
                ),
            )

        raise NotImplementedError("Resuming state not supported yet in new core")

        if print_context is not None:
            raise ValueError("print_context not allowed when using reusable state")

        mutation_map = self.reusable_state.data.mutation_map
        p_ops = set(
            fabll.Traits.get_implementors(
                F.Parameters.is_parameter_operatable.bind_typegraph(tg), g
            )
        )
        new_p_ops = p_ops - mutation_map.first_stage.input_operables

        # TODO consider using mutator
        transforms = Transformations.identity(
            tg,
            mutation_map.last_stage.G_out,
            input_print_context=mutation_map.output_print_context,
        )

        # inject new parameters
        new_params = [
            param
            for p in new_p_ops
            if (param := p.try_get_sibling_trait(F.Parameters.is_parameter))
        ]
        # TODO
        for p in new_params:
            # strip units and copy (for decoupling from old graph)
            # FIXME
            pass
            # transforms.mutated[p] = Parameter(
            #    domain=p.domain,
            #    tolerance_guess=p.tolerance_guess,
            #    likely_constrained=p.likely_constrained,
            #    units=dimensionless,
            #    soft_set=as_lit(p.soft_set).to_dimensionless()
            #    if p.soft_set is not None
            #    else None,
            #    within=as_lit(p.within).to_dimensionless()
            #    if p.within is not None
            #    else None,
            #    guess=quantity(p.guess, dimensionless) if p.guess is not None else None,  # noqa: E501
            # )

        # inject new expressions
        new_exprs = {
            expr
            for e in new_p_ops
            if (expr := e.try_get_sibling_trait(F.Expressions.is_expression))
        }
        for e in F.Expressions.is_expression.sort_by_depth(new_exprs, ascending=True):
            if S_LOG:
                logger.debug(
                    f"injecting {e.compact_repr(mutation_map.input_print_context)}"
                )
            op_mapped = list[F.Parameters.can_be_operand]()
            for op in e.get_operands():
                po = op.try_get_sibling_trait(F.Parameters.is_parameter_operatable)
                if po:
                    if po in transforms.mutated:
                        op_mapped.append(transforms.mutated[po].as_operand())
                        continue
                    if mutation_map.is_removed(po):
                        # TODO
                        raise Exception("Using removed operand")
                    if po in mutation_map.first_stage.input_operables:
                        op_mapped.append(
                            not_none(mutation_map.map_forward(po).maps_to).as_operand()
                        )
                        continue
                elif lit := op.try_get_sibling_trait(F.Literals.is_literal):
                    op = lit.as_operand()
                    if (
                        n_lit := fabll.Traits(lit)
                        .get_obj_raw()
                        .try_cast(F.Literals.Numbers)
                    ):
                        op = n_lit.to_dimensionless().get_trait(
                            F.Parameters.can_be_operand
                        )
                op_mapped.append(op)
            # TODO
            E_factory: type[fabll.NodeT] = None
            e_mapped = E_factory.bind_typegraph(tg).create_instance(g).setup(*op_mapped)
            transforms.mutated[e.as_parameter_operatable()] = e_mapped.get_trait(
                F.Parameters.is_parameter_operatable
            )
            if e.try_get_sibling_trait(F.Expressions.is_predicate):
                e_mapped.get_trait(F.Expressions.is_assertable).assert_()

        G_in = g
        # TODO
        G_out = None
        return DefaultSolver.SolverState(
            data=DefaultSolver.IterationData(
                mutation_map.extend(
                    MutationStage(
                        tg,
                        "resume_state",
                        iteration=0,
                        transformations=transforms,
                        print_context=mutation_map.output_print_context,
                        G_in=G_in,
                        G_out=G_out,
                    )
                )
            ),
        )

    @times_out(TIMEOUT)
    def simplify_symbolically(
        self,
        tg: fbrk.TypeGraph,
        g: graph.GraphView,
        print_context: F.Parameters.ReprContext | None = None,
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

        self.state = self._create_or_resume_state(print_context, g, tg)

        if S_LOG:
            self.state.data.mutation_map.print_name_mappings()
            self.state.data.mutation_map.last_stage.print_graph_contents(
                F.Expressions.is_expression
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

            if not self.state.data.mutation_map.G_out.get_node_count():
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

        G_out = self.state.data.mutation_map.last_stage.G_out
        ifs = F.Expressions.IfThenElse.bind_typegraph(tg).get_instances(G_out)
        for i in ifs:
            i.try_run()

        return self.state

    @override
    def try_fulfill(
        self,
        predicate: F.Expressions.is_assertable,
        lock: bool,
        allow_unknown: bool = False,
    ) -> bool | None:
        assert not predicate.try_get_sibling_trait(F.Expressions.is_predicate)
        asserted = predicate.assert_()

        pred_po = predicate.get_sibling_trait(F.Parameters.is_parameter_operatable)

        g = predicate.g()
        tg = predicate.tg

        try:
            solver_result = self.simplify_symbolically(tg, g, terminal=True)
        except TimeoutError:
            if not allow_unknown:
                raise
            return None
        finally:
            asserted.unassert()

        repr_map = solver_result.data.mutation_map

        # FIXME: is this correct?
        # definitely breaks a lot
        G_out = repr_map.G_out
        repr_pred = repr_map.map_forward(pred_po).maps_to
        print_context_new = repr_map.output_print_context

        # FIXME: workaround for above
        if repr_pred is not None:
            G_out = repr_pred.g()

        new_preds = fabll.Traits.get_implementors(
            F.Expressions.is_predicate.bind_typegraph(tg), G_out
        )
        not_deduced = [
            p for p in new_preds if not p.try_get_sibling_trait(is_terminated)
        ]

        if not_deduced:
            if not allow_unknown:
                if LOG_PICK_SOLVE:
                    logger.warning(
                        f"PREDICATE not deducible: {pred_po.compact_repr()}"
                        + (
                            f" -> {repr_pred.compact_repr(print_context_new)}"
                            if repr_pred is not None
                            else ""
                        )
                    )
                    logger.warning(
                        f"NOT DEDUCED: \n    {
                            '\n    '.join(
                                [
                                    p.get_sibling_trait(
                                        F.Parameters.is_parameter_operatable
                                    ).compact_repr(print_context_new)
                                    for p in not_deduced
                                ]
                            )
                        }"
                    )

                    repr_map.print_name_mappings(log=logger.warning)
                    repr_map.last_stage.print_graph_contents(log=logger.warning)

                raise NotDeducibleException(predicate, not_deduced)
            return None

        if lock:
            predicate.assert_()
        return True

    @override
    def simplify(self, g: graph.GraphView, tg: fbrk.TypeGraph):
        self.simplify_symbolically(tg, g, terminal=False)

    def update_superset_cache(self, *nodes: fabll.Node):
        if not nodes:
            return
        tg = nodes[0].tg
        # TODO consider creating new graph view that contains only the nodes
        g = nodes[0].g()
        try:
            self.simplify_symbolically(tg, g, terminal=True)
        except TimeoutError:
            if not ALLOW_PARTIAL_STATE:
                raise
            if self.state is None:
                raise

    def inspect_get_known_supersets(
        self, value: F.Parameters.is_parameter
    ) -> F.Literals.is_literal:
        """
        Careful, only use after solver ran!
        """
        value_po = value.as_parameter_operatable()

        is_lit = value_po.try_get_literal()
        if is_lit is not None:
            return is_lit

        if self.state is not None:
            is_solver_lit = self.state.data.mutation_map.try_get_literal(
                value_po, allow_subset=False, domain_default=False
            )
            if is_solver_lit is not None:
                return is_solver_lit

        ss_lit = value_po.try_get_literal_subset()
        if ss_lit is None:
            ss_lit = value.domain_set()

        solver_lit = None
        if self.state is not None:
            solver_lit = self.state.data.mutation_map.try_get_literal(
                value_po, allow_subset=True, domain_default=False
            )

        if solver_lit is None:
            return ss_lit

        return F.Literals.is_literal.intersect_all(ss_lit, solver_lit)

    @override
    def get_any_single(
        self,
        operatable: F.Parameters.is_parameter,
        lock: bool,
        suppose_predicate: F.Expressions.is_assertable | None = None,
        minimize: F.Expressions.is_expression | None = None,
    ) -> Any:
        # TODO
        if suppose_predicate is not None:
            raise NotImplementedError()

        # TODO
        if minimize is not None:
            raise NotImplementedError()

        lit = self.inspect_get_known_supersets(operatable)
        out = lit.any()
        singleton_lit = F.Literals.make_lit(lit.tg, out)
        if lock:
            F.Expressions.Is.from_operands(
                operatable.as_operand(),
                singleton_lit.get_trait(F.Parameters.can_be_operand),
                assert_=True,
            )
        return out
