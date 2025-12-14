# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import warnings
from itertools import pairwise, product

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
def test_performance_graph_get_all(count_power: int = 4, connected: bool = True):
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

    with timings.context("bind_type"):
        app_type = _simple_resistors().bind_typegraph(tg)
        F.Resistor.bind_typegraph(tg).create_instance(g=g)  # warm up the typegraph >:)

    with timings.context("create_instance"):
        app = app_type.create_instance(g=g)

    if connected:
        with timings.context("connect_interfaces"):
            interfaces = [r.get().unnamed[0].get() for r in app.resistors]
            for left, right in pairwise(interfaces):
                left._is_interface.get().connect_to(right)

    with timings.context("get_all_nodes"):
        num_nodes = len(g.get_nodes())

    # FIXME: remove usage of deprecated get_tree
    with warnings.catch_warnings():
        warnings.filterwarnings("default", category=DeprecationWarning)
        for n in [app, app.resistors[0].get()]:  # type: ignore
            name = type(n).__name__[0]
            assert n.has_trait(fabll.is_module)

            with timings.context(f"get_node_children_all {name}"):
                n.get_children(direct_only=False, types=fabll.Node)

            with timings.context(f"get_node_children_direct {name}"):
                n.get_children(direct_only=True, types=fabll.Node)

            with timings.context(f"get_node_children_trait_filter {name}"):
                n.get_children(
                    direct_only=True,
                    types=fabll.Node,
                    required_trait=fabll.is_interface,
                )

            with timings.context(f"get_node_tree {name}"):
                n.get_tree(types=fabll.Node)

            with timings.context(f"get_node_tree_trait_filter {name}"):
                n.get_tree(
                    types=fabll.Node, f_filter=lambda c: c.has_trait(fabll.is_interface)
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
