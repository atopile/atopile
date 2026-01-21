# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
import time
from collections.abc import Generator
from dataclasses import dataclass
from itertools import count
from typing import TYPE_CHECKING

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from faebryk.core.solver.algorithm import SolverAlgorithm

if TYPE_CHECKING:
    import faebryk.library._F as F
from atopile.logging import NET_LINE_WIDTH
from faebryk.core.solver.mutator import MutationMap, MutationStage, Mutator
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
from faebryk.libs.test.times import Times
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)

if S_LOG:
    logger.setLevel(logging.DEBUG)


class Solver:
    class algorithms:
        # TODO: get order from topo sort
        # and types from decorator
        iterative = [
            structural.remove_unconstrained,
            expression_groups.idempotent_unpack,
            expression_groups.involutory_fold,
            expression_groups.unary_identity_unpack,
            *expression_wise.fold_algorithms,
            structural.predicate_unconstrained_operands_deduce,
            structural.transitive_subset,
            structural.upper_estimation_of_expressions_with_supersets,
            structural.lower_estimation_of_expressions_with_subsets,
        ]

    @dataclass
    class IterationData:
        mutation_map: MutationMap

        def compressed(self) -> "Solver.IterationData":
            return Solver.IterationData(mutation_map=self.mutation_map.compressed())

    @dataclass
    class IterationState:
        dirty: bool

    @dataclass
    class SolverState:
        data: "Solver.IterationData"

        def destroy(self) -> None:
            self.data.mutation_map.destroy()

        def __del__(self) -> None:
            try:
                self.destroy()
            except Exception:
                pass

        def compressed(self) -> "Solver.SolverState":
            return Solver.SolverState(data=self.data.compressed())

    def __init__(self) -> None:
        self.state: Solver.SolverState | None = None
        self._terminal = False

    @classmethod
    def _run_iteration(
        cls,
        iterno: int,
        data: IterationData,
        algos: list[SolverAlgorithm],
        terminal: bool,
    ) -> "Solver.IterationState":
        iteration_state = Solver.IterationState(dirty=False)
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
            try:
                mutator._run()
                run_time = time.perf_counter() - now
                timings.add("_")
                algo_result = mutator.close()
            except:
                logger.error(f"Error running algorithm {algo.name}")
                logger.error("G_in")
                MutationStage.print_graph_contents_static(
                    mutator.tg_in, mutator.G_in, mutator.print_ctx, log=logger.error
                )
                logger.error("G_out")
                MutationStage.print_graph_contents_static(
                    mutator.tg_in, mutator.G_out, mutator.print_ctx, log=logger.error
                )
                raise

            iteration_state.dirty |= algo_result.dirty
            data.mutation_map = data.mutation_map.extend(algo_result.mutation_stage)

            timings.add(f"close {'💩' if algo_result.dirty else '🧹'}")

            new_name = (
                f"{algo.name.ljust(40)}"
                f" {'🛑' if terminal else '♻️'}"
                f" {'💩' if algo_result.dirty else '🧹'}"
            )
            timings.add(new_name, duration=run_time)

        return iteration_state

    def _create_or_resume_state(
        self,
        print_context: F.Parameters.ReprContext | None,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        relevant: list[F.Parameters.can_be_operand] | None = None,
    ):
        initial_state = (
            self.state.data.mutation_map.compressed() if self.state else None
        )
        return Solver.SolverState(
            data=Solver.IterationData(
                mutation_map=MutationMap.bootstrap(
                    tg=tg,
                    g=g,
                    print_context=print_context,
                    relevant=relevant,
                    initial_state=initial_state,
                )
            )
        )

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
        import faebryk.library._F as F

        # TODO remove compatibility layer
        if isinstance(g, fbrk.TypeGraph) and isinstance(tg, graph.GraphView):
            g, tg = tg, g
        assert isinstance(g, graph.GraphView) and isinstance(tg, fbrk.TypeGraph)

        now = time.time()
        logger.info("Symbolic Solving ".ljust(NET_LINE_WIDTH, "="))
        timings = Times(name="Symbolic Solving")

        self.state = self._create_or_resume_state(print_context, g, tg, relevant)
        assert not self._terminal, "Terminal algorithms already run"
        self._terminal = terminal

        algos = [a for a in self.algorithms.iterative if terminal or not a.terminal]

        with timings.measure("symbolic solving"):
            for iterno in count():
                if iterno > MAX_ITERATIONS_HEURISTIC:
                    raise TimeoutError(
                        "Solver Bug: Too many iterations, likely stuck in a loop"
                    )
                logger.info(
                    (f"Iteration {iterno} {self.state.data.mutation_map}").ljust(
                        NET_LINE_WIDTH, "-"
                    )
                )

                iteration_state = Solver._run_iteration(
                    iterno=iterno,
                    data=self.state.data,
                    terminal=terminal,
                    algos=algos,
                )

                if not iteration_state.dirty:
                    break

                if not self.state.data.mutation_map.G_out.get_node_count():
                    break

        if S_LOG:
            self.state.data.mutation_map.last_stage.print_graph_contents()
        logger.info(timings)
        logger.info(
            (
                f"Symbolic Solving done in {iterno} iterations"
                f" and {time.time() - now:.3f} seconds"
            ).ljust(NET_LINE_WIDTH, "=")
        )

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

    def simplify_for(
        self,
        *ops: F.Parameters.can_be_operand,
        terminal: bool = False,
    ):
        g = ops[0].g
        tg = ops[0].tg
        relevant = list(ops)
        return self.simplify(
            g=g,
            tg=tg,
            terminal=terminal,
            relevant=relevant,
        )

    def simplify_and_extract_superset(
        self,
        value: F.Parameters.is_parameter,
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        terminal: bool = False,
    ) -> F.Literals.is_literal:
        g = g or value.g
        tg = tg or value.tg
        self.simplify(g=g, tg=tg, terminal=terminal, relevant=[value.as_operand.get()])
        return self.extract_superset(value, g=g, tg=tg)

    @classmethod
    def from_initial_state(cls, state: SolverState) -> Solver:
        out = Solver()
        out.state = state
        return out

    def fork(self) -> Generator[Solver, None, None]:
        if self.state is None:
            raise ValueError("Forking failed: state is uninitialized")

        if self._terminal:
            raise ValueError("Forking failed: terminal algorithms already run")

        compressed = self.state.compressed()

        while True:
            yield Solver.from_initial_state(compressed)


# Tests --------------------------------------------------------------------------------


def test_solver_super_basic():
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
    solver = Solver()
    res = solver.simplify(tg, g, terminal=True)
    lit = res.data.mutation_map.try_extract_superset(P.is_parameter_operatable.get())
    assert lit
    print(lit.pretty_str())
    assert lit.op_setic_equals_singleton(True)


def test_solver_basic():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    import faebryk.library._F as FT

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

    solver = Solver()
    res = solver.simplify(tg, g, terminal=True)
    C_lit = res.data.mutation_map.try_extract_superset(
        app.C.get().is_parameter_operatable.get()
    )
    assert C_lit
    assert C_lit.op_setic_equals_singleton(True)
    print(res)


if __name__ == "__main__":
    import typer

    from atopile.logging import setup_basic_logging

    setup_basic_logging()
    logger.setLevel(logging.DEBUG)
    from faebryk.core.solver.mutator import logger as mutator_logger

    mutator_logger.setLevel(logging.DEBUG)

    typer.run(test_solver_basic)
