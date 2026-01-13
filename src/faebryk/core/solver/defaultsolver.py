# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from dataclasses import dataclass
from itertools import count
from typing import override

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
)
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.core.solver.symbolic import (
    expression_groups,
    expression_wise,
    structural,
)
from faebryk.core.solver.utils import (
    MAX_ITERATIONS_HEURISTIC,
    PRINT_START,
    S_LOG,
)
from faebryk.libs.logging import NET_LINE_WIDTH
from faebryk.libs.test.times import Times
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)

if S_LOG:
    logger.setLevel(logging.DEBUG)


class DefaultSolver(Solver):
    class algorithms:
        # TODO: get order from topo sort
        # and types from decorator
        iterative = [
            structural.check_literal_contradiction,
            structural.remove_unconstrained,
            structural.convert_operable_aliased_to_single_into_literal,
            structural.resolve_alias_classes,
            structural.distribute_literals_across_alias_classes,
            expression_groups.associative_flatten,
            expression_groups.reflexive_predicates,
            expression_groups.idempotent_deduplicate,
            expression_groups.idempotent_unpack,
            expression_groups.involutory_fold,
            expression_groups.unary_identity_unpack,
            *expression_wise.fold_algorithms,
            structural.predicate_flat_terminate,
            structural.predicate_unconstrained_operands_deduce,
            structural.transitive_subset,
            structural.isolate_lone_params,
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

        def destroy(self) -> None:
            self.data.mutation_map.destroy()

        def __del__(self) -> None:
            try:
                self.destroy()
            except Exception:
                pass

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
                G_in = data.mutation_map.G_out
                logger.debug(
                    f"START Iteration {iterno} Phase {phase_name}: {algo.name}"
                    f" G_in:{G_in}"
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
                    f"DONE  Iteration {iterno} Phase {phase_name}: {algo.name}"
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
        relevant: list[F.Parameters.can_be_operand] | None = None,
    ):
        # TODO consider not getting full graph of node gs, but scope to only relevant

        if self.reusable_state is None:
            # TODO: strip graph from all unnecessary nodes
            # strip = copy only stuff over we are interested in (po and is_lit)
            # be careful: mutator map resolution is using the original object
            # if you copy it into the stripped graph its going to be missing
            # check what is easier:
            # 1. handle that detail
            # 2. add the stripping to the canonicalization algorithm, where the mutator will take care of the rest

            return DefaultSolver.SolverState(
                data=DefaultSolver.IterationData(
                    mutation_map=MutationMap.bootstrap(
                        tg=tg,
                        g=g,
                        print_context=print_context,
                        relevant=relevant,
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
            input_print_context=mutation_map.print_ctx,
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
                        print_ctx=mutation_map.print_ctx,
                        G_in=G_in,
                        G_out=G_out,
                    )
                )
            ),
        )

    @override
    # @times_out(TIMEOUT)
    def simplify(
        self,
        g: graph.GraphView | fbrk.TypeGraph,
        tg: fbrk.TypeGraph | graph.GraphView,
        print_context: F.Parameters.ReprContext | None = None,
        terminal: bool = True,
        relevant: list[F.Parameters.can_be_operand] | None = None,
    ) -> SolverState:
        """
        Args:
        - terminal: if True, result of simplication can't be reused, but simplification
            is more powerful
        """
        # TODO remove compatibility layer
        if isinstance(g, fbrk.TypeGraph) and isinstance(tg, graph.GraphView):
            g, tg = tg, g
        assert isinstance(g, graph.GraphView) and isinstance(tg, fbrk.TypeGraph)
        timings = Times(name="simplify")

        now = time.time()
        if LOG_PICK_SOLVE:
            logger.info("Phase 1 Solving: Symbolic Solving ".ljust(NET_LINE_WIDTH, "="))

        self.state = self._create_or_resume_state(print_context, g, tg, relevant)

        if S_LOG:
            self.state.data.mutation_map.print_name_mappings()
            self.state.data.mutation_map.last_stage.print_graph_contents(
                F.Expressions.is_expression
            )

        algos = [a for a in self.algorithms.iterative if terminal or not a.terminal]
        for iterno in count():
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
                    iterno=iterno, data=self.state.data, terminal=terminal, algos=algos
                )
            except Exception:
                if S_LOG:
                    self.state.data.mutation_map.last_stage.print_graph_contents()
                raise

            if not iteration_state.dirty:
                break

            if not self.state.data.mutation_map.G_out.get_node_count():
                break

            if S_LOG:
                # TODO remove logger.debug
                self.state.data.mutation_map.last_stage.print_graph_contents(
                    log=logger.debug
                )

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

    def extract_superset(
        self,
        value: F.Parameters.is_parameter,
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> F.Literals.is_literal:
        """
        Careful, only use after solver ran!
        """
        g = g or value.g
        tg = tg or value.tg
        value_po = value.as_parameter_operatable.get()

        if self.state is not None:
            return not_none(
                # TODO should take g, tg
                self.state.data.mutation_map.try_extract_superset(
                    value_po, domain_default=True
                )
            )
        else:
            ss_lit = value_po.try_extract_superset()
            if ss_lit is None:
                return value.domain_set(g=g, tg=tg)
            return ss_lit


# Tests --------------------------------------------------------------------------------


def test_defaultsolver_super_basic():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    import faebryk.library._F as FT

    # Fill typegraph
    # for E in (
    #    list(vars(FT.Expressions).values())
    #    + list(vars(FT.Parameters).values())
    #    + list(vars(FT.Literals).values())
    #    + [is_terminated]
    # ):
    #    if not isinstance(E, type) or not issubclass(E, fabll.Node):
    #        continue
    #    fabll.TypeNodeBoundTG.get_or_create_type_in_tg(tg=tg, E)

    P = FT.Parameters.BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    P.set_singleton(True)
    solver = DefaultSolver()
    res = solver.simplify(tg, g, terminal=True)
    lit = res.data.mutation_map.try_extract_superset(P.is_parameter_operatable.get())
    assert lit
    print(lit.pretty_str())
    assert lit.op_setic_equals_singleton(True)


def test_defaultsolver_basic():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    import faebryk.library._F as FT

    # Fill typegraph
    # for E in (
    #    list(vars(FT.Expressions).values())
    #    + list(vars(FT.Parameters).values())
    #    + list(vars(FT.Literals).values())
    #    + [is_terminated]
    # ):
    #    if not isinstance(E, type) or not issubclass(E, fabll.Node):
    #        continue
    #    fabll.TypeNodeBoundTG.get_or_create_type_in_tg(tg=tg, E)

    class _App(fabll.Node):
        A = FT.Parameters.BooleanParameter.MakeChild()
        B = FT.Parameters.BooleanParameter.MakeChild()
        C = FT.Parameters.BooleanParameter.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    app.A.get().set_singleton(True)
    FT.Expressions.Is.c(
        FT.Expressions.Or.c(
            app.A.get().can_be_operand.get(),
            app.B.get().can_be_operand.get(),
            assert_=False,
        ),
        app.C.get().can_be_operand.get(),
        assert_=True,
    )

    solver = DefaultSolver()
    res = solver.simplify(tg, g, terminal=True)
    C_lit = res.data.mutation_map.try_extract_superset(
        app.C.get().is_parameter_operatable.get()
    )
    assert C_lit
    assert C_lit.op_setic_equals_singleton(True)
    print(res)


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    logger.setLevel(logging.DEBUG)
    from faebryk.core.solver.mutator import logger as mutator_logger

    mutator_logger.setLevel(logging.DEBUG)

    typer.run(test_defaultsolver_basic)
