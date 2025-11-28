# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from itertools import pairwise, product

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.test.times import Times
from faebryk.libs.util import times

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

    with timings.context("bind_type"):
        app_type = _simple_resistors().bind_typegraph(tg)
        F.Resistor.bind_typegraph(tg).create_instance(g=g) # warm up the typegraph >:)

    with timings.context("create_instance"):
        app = app_type.create_instance(g=g)

    if connected:
        with timings.context("connect_interfaces"):
            interfaces = [r.get().unnamed[0].get() for r in app.resistors]
            for left, right in pairwise(interfaces):
                left.get_trait(fabll.is_interface).connect_to(right)

    with timings.context("get_all_nodes"):
        num_nodes = len(g.get_nodes())

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
                required_trait=fabll.is_interface)

        with timings.context(f"get_node_tree {name}"):
            n.get_tree(types=fabll.Node)

        with timings.context(f"get_node_tree_trait_filter {name}"):
            n.get_tree(
                types=fabll.Node,
                f_filter=lambda c: c.has_trait(fabll.is_interface))

    logger.info(f"\n\n{timings!r}")
    per_resistor = timings.get("create_instance") / count
    logger.info(f"----> Avg/resistor: {per_resistor * 1e3:.2f} ms")
    logger.info(f"----> Nodes generated: {num_nodes}")


def test_performance_graph_merge_rec():
    timings = Times()
    count = 2**14
    logger.info(f"Count: {count}")

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    node_factory = fabll.Node.bind_typegraph(tg)

    gs = times(count, lambda: node_factory.create_instance(g=g))
    timings.add("instance")

    def rec_connect(gs_sub: list[fabll.Node]):
        if len(gs_sub) == 1:
            return gs_sub[0]

        mid = len(gs_sub) // 2

        with timings.context(f"split {len(gs_sub)}"):
            timings.add(f"recurse {len(gs_sub)}")
            left = rec_connect(gs_sub[:mid])
            right = rec_connect(gs_sub[mid:])

        timings.add(f"connect {len(gs_sub)}")
        fbrk.EdgeComposition.add_child(
            bound_node=left.instance,
            child=right.instance.node(),
            child_identifier=str(len(gs_sub)),
        )
        timings.add("connect")

        return left

    with timings.context("total"):
        rec_connect(gs)

    logger.info(timings)
    per_connect = timings.get_formatted("connect", Times.MultiSampleStrategy.AVG)
    logger.info(f"----> Avg/connect: {per_connect}")


def test_performance_graph_merge_it():
    timings = Times(multi_sample_strategy=Times.MultiSampleStrategy.AVG_ACC)
    count = 2**14
    logger.info(f"Count: {count}")

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    node_factory = fabll.Node.bind_typegraph(tg)

    gs = times(count, lambda: node_factory.create_instance(g=g))
    timings.add("instance")

    for idx, (gl, gr) in enumerate(pairwise(gs)):
        fbrk.EdgeComposition.add_child(
            bound_node=gl.instance,
            child=gr.instance.node(),
            child_identifier=str(idx),
        )
        timings.add("connect")

    assert gs[0].g.get_node_count() >= count

    logger.info(timings)
    per_connect = timings.get_formatted("connect", Times.MultiSampleStrategy.AVG)
    logger.info(f"----> Avg/connect: {per_connect}")
