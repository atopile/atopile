# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import product

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.test.times import Times

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "count_power, connected",
    product(range(2, 5), [True, False]),
    ids=lambda x: 10 * 2**x
    if not isinstance(x, bool)
    else "connected"
    if x
    else "simple",
)
def test_performance_graph_get_all(count_power: int, connected: bool):
    count = 10 * 2**count_power
    timings = Times()

    def _simple_resistors():
        class App(fabll.Node):
            resistors = [F.Resistor.MakeChild() for _ in range(count)]
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

        return App

    with timings.context("setup"):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

    with timings.context("fabll stage0"):
        app_type = _simple_resistors().bind_typegraph(tg)
        bound_resistor = F.Resistor.bind_typegraph(tg)

    with timings.context("typegraph"):
        bound_resistor.get_or_create_type()

    with timings.context("create_instance"):
        app = app_type.create_instance(g=g)

    if connected:
        with timings.context("connect_interfaces"):
            interfaces = [r.get().unnamed[0].get() for r in app.resistors]
            left = interfaces[0]
            left._is_interface.get().connect_to(*interfaces[1:])

    with timings.context("get_all_graph_nodes"):
        num_nodes = len(g.get_nodes())

    for n in (app, app.resistors[0].get()):
        name = type(n).__name__[0]
        assert n.has_trait(fabll.is_module)

        with timings.context(f"get_node_children_all {name}"):
            n.get_children(direct_only=False, types=fabll.Node)

        with timings.context(f"get_node_children_direct {name}"):
            n.get_children(direct_only=True, types=fabll.Node)

        with timings.context(f"get_node_children_trait_filter {name}"):
            n.get_children(
                direct_only=False,
                types=fabll.Node,
                required_trait=fabll.is_interface,
            )

    logger.info(f"\n\n{timings!r}")
    per_resistor = timings.get("create_instance") / count
    logger.info(f"----> Avg/resistor: {per_resistor * 1e3:.2f} ms")
    logger.info(f"----> Nodes generated: {num_nodes}")


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()

    typer.run(test_performance_graph_get_all)
