# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from typing import Any, Callable, override

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.parameter import (
    ConstrainableExpression,
    Expression,
    Parameter,
    ParameterOperatable,
    Predicate,
)
from faebryk.core.solver.analytical import (
    compress_associative,
    convert_inequality_with_literal_to_subset,
    convert_operable_aliased_to_single_into_literal,
    empty_set,
    fold_literals,
    merge_intersect_subsets,
    predicate_literal_deduce,
    predicate_unconstrained_operands_deduce,
    remove_congruent_expressions,
    remove_empty_graphs,
    remove_unconstrained,
    resolve_alias_classes,
    transitive_subset,
    upper_estimation_of_expressions_with_subsets,
)
from faebryk.core.solver.canonical import (
    constrain_within_domain,
    convert_to_canonical_literals,
    convert_to_canonical_operations,
)
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.core.solver.utils import (
    PRINT_START,
    S_LOG,
    Contradiction,
    Mutator,
    Mutators,
    SolverLiteral,
    debug_name_mappings,
    get_graphs,
    try_extract_literal,
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

    def __init__(self) -> None:
        super().__init__()

        self.superset_cache: dict[Parameter, tuple[int, P_Set]] = {}

    def has_no_solution(
        self, total_repr_map: dict[ParameterOperatable, ParameterOperatable.All]
    ) -> bool:
        # any parameter is/subset literal is empyt (implcit constraint that we forgot)
        # any constrained expression got mapped to False
        # any constrained expression literal is False
        raise NotImplementedError()

    @times_out(120)
    def phase_1_simplify_analytically(
        self,
        g: Graph,
        print_context: ParameterOperatable.ReprContext | None = None,
    ):
        now = time.time()
        if LOG_PICK_SOLVE:
            logger.info("Phase 1 Solving: Analytical Solving ".ljust(80, "="))

        # TODO move into comment here
        # strategies
        # https://www.notion.so/
        # Phase1-136836dcad9480cbb037defe359934ee?pvs=4#136836dcad94807d93bccb14598e1ef0

        pre_algorithms = [
            ("Constrain within and domain", constrain_within_domain),
            ("Canonical literal form", convert_to_canonical_literals),
            ("Canonical expression form", convert_to_canonical_operations),
        ]

        iterative_algorithms = [
            ("Remove unconstrained", remove_unconstrained),
            (
                "Convert aliased singletons into literals",
                convert_operable_aliased_to_single_into_literal,
            ),
            ("Remove congruent expressions", remove_congruent_expressions),
            ("Alias classes", resolve_alias_classes),
            (
                "Inequality with literal to subset",
                convert_inequality_with_literal_to_subset,
            ),
            ("Associative expressions Full", compress_associative),
            ("Fold literals", fold_literals),
            ("Merge intersecting subsets", merge_intersect_subsets),
            ("Predicate literal deduce", predicate_literal_deduce),
            (
                "Predicate unconstrained operands deduce",
                predicate_unconstrained_operands_deduce,
            ),
            ("Empty set", empty_set),
            ("Transitive subset", transitive_subset),
            ("Remove empty graphs", remove_empty_graphs),
        ]
        subset_dirty_algorithms = [
            ("Upper estimation", upper_estimation_of_expressions_with_subsets),
        ]

        print_context_ = print_context or ParameterOperatable.ReprContext()

        if S_LOG:
            debug_name_mappings(print_context_, g)
            Mutators.print_all(g, context=print_context_, type_filter=Expression)

        def run_algo(
            graphs: list[Graph],
            phase_name: str,
            algo_name: str,
            algo: Callable[[Mutator], None],
        ):
            nonlocal print_context_
            if PRINT_START:
                logger.debug(
                    f"START Iteration {iterno} Phase 1.{phase_name}: {algo_name}"
                    f" G:{len(graphs)}"
                )
            mutators = Mutators(*graphs, print_context=print_context_)
            mutators.run(algo)
            algo_repr_map, algo_graphs, algo_dirty = mutators.close()
            # TODO remove
            if algo_dirty:
                logger.debug(
                    f"DONE  Iteration {iterno} Phase 1.{phase_name}: {algo_name} "
                    f"G:{len(graphs)}"
                )
                print_context_ = mutators.debug_print()
            # TODO assert all new graphs
            return algo_repr_map, algo_graphs, algo_dirty

        any_dirty = True
        iterno = -1
        total_repr_map = Mutators.ReprMap({})
        graphs = [g]

        # subset specific
        param_ops_subset_literals: dict[ParameterOperatable, SolverLiteral | None] = {}

        while any_dirty and len(graphs) > 0:
            iterno += 1
            # TODO remove
            if iterno > 10:
                raise Exception("Too many iterations")
            v_count = sum(
                len(GraphFunctions(g).nodes_of_type(ParameterOperatable))
                for g in graphs
            )
            logger.debug(
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
                algo_repr_map, algo_graphs, algo_dirty = run_algo(
                    graphs, str(phase_name), algo_name, algo
                )
                if not algo_dirty:
                    continue
                iteration_dirty[(iterno, algo_name)] = algo_dirty
                graphs = algo_graphs
                iteration_repr_maps[(iterno, algo_name)] = algo_repr_map

            any_dirty = any(iteration_dirty.values())

            total_repr_map = Mutators.create_concat_repr_map(
                *([total_repr_map.repr_map] if iterno > 0 else []),
                *iteration_repr_maps.values(),
            )

            if not any_dirty:
                continue

            # subset -------------------------------------------------------------------
            if iterno == 0:
                # Build initial subset literals
                param_ops_subset_literals = {
                    po: try_extract_literal(po, allow_subset=True)
                    for G in graphs
                    for po in GraphFunctions(G).nodes_of_type(ParameterOperatable)
                }
                continue

            # check which subset literals have changed for our old paramops
            subset_dirty = False
            param_ops_subset_literals = {
                po: lit
                for po, lit in param_ops_subset_literals.items()
                if po in total_repr_map
            }
            for po in param_ops_subset_literals:
                new_subset_literal = total_repr_map.try_get_literal(
                    po, allow_subset=True
                )
                if new_subset_literal != param_ops_subset_literals[po]:
                    logger.debug(
                        f"Subset dirty {param_ops_subset_literals[po]} != "
                        f"{new_subset_literal}"
                    )
                    param_ops_subset_literals[po] = new_subset_literal
                    subset_dirty = True

            iteration_repr_maps: dict[tuple[int, str], Mutator.REPR_MAP] = {}

            if not subset_dirty and iterno > 1:
                continue
            if subset_dirty:
                logger.debug("Subset dirty, running subset dirty algorithms")
            else:
                logger.debug("Iteration 1, running subset dirty algorithms")

            phase_end = phase_name + 1
            # Run subset dirty algorithms
            for phase_name, (algo_name, algo) in enumerate(subset_dirty_algorithms):
                algo_repr_map, algo_graphs, algo_dirty = run_algo(
                    graphs, f"{phase_end}.{phase_name}", algo_name, algo
                )
                if not algo_dirty:
                    continue
                graphs = algo_graphs
                iteration_repr_maps[(iterno, algo_name)] = algo_repr_map

            total_repr_map = Mutators.create_concat_repr_map(
                total_repr_map.repr_map,
                *iteration_repr_maps.values(),
            )
            # --------------------------------------------------------------------------

        if S_LOG:
            Mutators.print_all(*graphs, context=print_context_)

        if LOG_PICK_SOLVE:
            logger.info(
                f"Phase 1 Solving: Analytical Solving done in {iterno} iterations"
                f" and {time.time() - now:.3f} seconds".ljust(80, "=")
            )
        return total_repr_map, print_context_

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
