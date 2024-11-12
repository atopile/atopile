# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Iterable, cast

from more_itertools import partition

import faebryk.library._F as F
from faebryk.core.cpp import Graph
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.parameter import Parameter
from faebryk.libs.test.times import Times
from faebryk.libs.util import find, groupby

logger = logging.getLogger(__name__)


def replace_tbd_with_any(module: Module, recursive: bool, loglvl: int | None = None):
    """
    Replace all F.TBD instances with F.ANY instances in the given module.

    :param module: The module to replace F.TBD instances in.
    :param recursive: If True, replace F.TBD instances in submodules as well.
    """
    lvl = logger.getEffectiveLevel()
    if loglvl is not None:
        logger.setLevel(loglvl)

    module = module.get_most_special()

    for param in module.get_children(direct_only=True, types=Parameter):
        if isinstance(param.get_most_narrow(), F.TBD):
            logger.debug(f"Replacing in {module}: {param} with F.ANY")
            param.merge(F.ANY())

    logger.setLevel(lvl)

    if recursive:
        for m in module.get_children_modules(types=Module):
            replace_tbd_with_any(m, recursive=False, loglvl=loglvl)


def resolve_dynamic_parameters(graph: Graph):
    other_dynamic_params, connection_dynamic_params = partition(
        lambda param_trait: isinstance(param_trait[1], F.is_dynamic_by_connections),
        [
            (param, trait)
            for param, trait in GraphFunctions(graph).nodes_with_trait(
                Parameter.is_dynamic
            )
        ],
    )

    # non-connection
    for _, trait in other_dynamic_params:
        trait.execute()

    # connection
    _resolve_dynamic_parameters_connection(
        cast(
            list[tuple[Parameter, F.is_dynamic_by_connections]],
            connection_dynamic_params,
        )
    )


def _resolve_dynamic_parameters_connection(
    params: Iterable[tuple[Parameter, F.is_dynamic_by_connections]],
):
    times = Times()

    busses: list[set[ModuleInterface]] = []

    params_grouped_by_mif = groupby(params, lambda p: p[1].mif_parent())

    # find for all busses a mif that represents it, and puts its dynamic params here
    # we use the that connected mifs are the same type and thus have the same params
    # TODO: limitation: specialization (need to subgroup by type) (see exception)
    param_bus_representatives: set[tuple[Parameter, F.is_dynamic_by_connections]] = (
        set()
    )

    while params_grouped_by_mif:
        bus_representative_mif, bus_representative_params = (
            params_grouped_by_mif.popitem()
        )
        # expensive call
        paths = bus_representative_mif.get_connected(include_self=True)
        connections = set(paths.keys())

        busses.append(connections)
        if len(set(map(type, connections))) > 1:
            raise NotImplementedError(
                "No support for specialized bus with dynamic params"
            )

        for m in connections:
            if m in params_grouped_by_mif:
                del params_grouped_by_mif[m]
        param_bus_representatives |= set(bus_representative_params)

    times.add("get parameter connections")

    # exec resolution
    for _, trait in param_bus_representatives:
        bus_representative_mif = trait.mif_parent()
        param_bus = find(busses, lambda bus: bus_representative_mif in bus)
        trait.exec_for_mifs(param_bus)

    times.add("merge parameters")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(times)
