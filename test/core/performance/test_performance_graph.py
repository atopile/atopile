# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import pairwise, product

import pytest

import faebryk.library._F as F
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.libs.library import L
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

    def _factory_simple_resistors():
        class App(Module):
            resistors = L.list_field(count, F.Resistor)

            def __init__(self, timings: Times) -> None:
                super().__init__()
                self._timings = timings

            def __preinit__(self):
                self._timings.add("setup")

        return App

    def _factory_interconnected_resistors():
        class App(Module):
            resistors = L.list_field(count, F.Resistor)

            def __init__(self, timings: Times) -> None:
                super().__init__()
                self._timings = timings

            def __preinit__(self):
                self._timings.add("setup")

                F.Electrical.connect(*(r.unnamed[0] for r in self.resistors))
                self._timings.add("connect")

        return App

    timings = Times()

    if connected:
        AppF = _factory_interconnected_resistors()
    else:
        AppF = _factory_simple_resistors()

    with timings.context("instance"):
        app = AppF(timings)

    G = app.get_graph()
    timings.add("graph")

    G.node_projection()
    timings.add("get_all_nodes_graph")

    for n in [app, app.resistors[0]]:  # type: ignore
        assert isinstance(n, Module)
        name = type(n).__name__[0]

        n.get_children(direct_only=False, types=Node)
        timings.add(f"get_node_children_all {name}")

        n.get_tree(types=Node)
        timings.add(f"get_node_tree {name}")

        n.get_tree(types=ModuleInterface)
        timings.add(f"get_mif_tree {name}")

        n.get_children(direct_only=True, types=Node)
        timings.add(f"get_module_direct_children {name}")

        n.get_children(direct_only=True, types=ModuleInterface)
        timings.add(f"get_mifs {name}")

    logger.info(f"{timings!r}")
    logger.info(str(G))

    per_resistor = timings.get("instance") / count
    logger.info(f"----> Avg/resistor: {per_resistor * 1e6:.2f} us")


def test_performance_graph_merge_rec():
    timings = Times()
    count = 2**14
    logger.info(f"Count: {count}")

    gs = times(count, GraphInterface)
    timings.add("instance")

    def rec_connect(gs_sub: list[GraphInterface]):
        if len(gs_sub) == 1:
            return gs_sub[0]

        mid = len(gs_sub) // 2

        with timings.context(f"split {len(gs_sub)}"):
            timings.add(f"recurse {len(gs_sub)}")
            left = rec_connect(gs_sub[:mid])
            right = rec_connect(gs_sub[mid:])

        timings.add(f"connect {len(gs_sub)}")
        left.connect(right)
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

    gs = times(count, GraphInterface)
    timings.add("instance")

    for gl, gr in pairwise(gs):
        gl.connect(gr)
        timings.add("connect")

    assert gs[0].G.node_count == count

    logger.info(timings)
    per_connect = timings.get_formatted("connect", Times.MultiSampleStrategy.AVG)
    logger.info(f"----> Avg/connect: {per_connect}")
