# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging

import faebryk.library._F as F
from atopile import errors
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter, Predicate
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.mutator import MutationMap
from faebryk.core.solver.solver import Solver
from faebryk.libs.app.erc import simple_erc
from faebryk.libs.exceptions import accumulate
from faebryk.libs.util import cast_assert, not_none

logger = logging.getLogger(__name__)


def run_checks(app: Module, G: Graph):
    simple_erc(G)


class ParameterError(errors.UserException):
    """Base class for parameter faults."""


class UnspecifiedParameterError(ParameterError):
    """A parameter is required but not specified."""

    def __init__(
        self,
        orig_param: Parameter,
        param: Parameter,
        preds: list[Predicate],
        mutation_map: MutationMap,
        *args: object,
    ) -> None:
        print_context = mutation_map.output_print_context
        tracebacks = [mutation_map.get_traceback(pred).filtered() for pred in preds]
        constraints = "\n".join(
            f" - {leaf.compact_repr(print_context, use_name=True)}"
            for tb in tracebacks
            for leaf in tb.get_leaves()
        )

        super().__init__(
            f"Parameter `{orig_param}` is constrained but has not been specified.\n\n"
            f"Constrained by: \n{constraints}",
        )


def check_parameters(parameters: set[Parameter], G: Graph, solver: Solver):
    """
    Basic checks to find issues prior to picking.

    - For parts which are explicitly specified, all parameters constrained to something
      other than their domain must be specified
    """
    logger.info(f"Checking {len(parameters)} parameters")

    solver = cast_assert(DefaultSolver, solver)  # FIXME
    mutation_map = not_none(solver.state).data.mutation_map

    explicit_picks = (
        node
        for node, _ in GraphFunctions(G).nodes_with_any_trait(
            F.is_pickable_by_supplier_id, F.is_pickable_by_part_number
        )
        if isinstance(node, Module)
    )

    with accumulate(ParameterError) as accumulator:
        for module in explicit_picks:
            assert isinstance(module, Module)

            for orig_param in module.get_parameters():
                with accumulator.collect():
                    if (
                        maps_to := mutation_map.map_forward(orig_param).maps_to
                    ) is None:
                        continue

                    param = cast_assert(Parameter, maps_to)
                    preds = param.get_operations(Predicate, constrained_only=True)

                    if param.try_get_literal() is not None:
                        continue

                    constraints = [
                        pred
                        for pred in preds
                        if any(
                            lit != param.domain_set()
                            for lit in pred.get_operand_literals().values()
                        )
                    ]

                    if constraints:
                        raise UnspecifiedParameterError(
                            orig_param, param, constraints, mutation_map
                        )
