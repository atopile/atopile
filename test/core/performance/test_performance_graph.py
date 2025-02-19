# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from itertools import pairwise, product
from typing import Callable

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

    def _common_timings(factory: Callable[[], Callable[[Times], Module]]):
        timings = Times()

        AppF = factory()
        timings.add("classdef")

        now = time.time()
        app = AppF(timings)
        timings.times["instance"] = time.time() - now

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
        return timings

    timings = _common_timings(
        _factory_interconnected_resistors if connected else _factory_simple_resistors
    )
    per_resistor = timings.times["instance"] / count
    logger.info(f"----> Avg/resistor: {per_resistor*1e3:.2f} ms")


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

        now = time.time()
        timings.add(f"recurse {len(gs_sub)}")
        left = rec_connect(gs_sub[:mid])
        right = rec_connect(gs_sub[mid:])
        timings.times[f"split {len(gs_sub)}"] = time.time() - now

        timings.add(f"connect {len(gs_sub)}")
        left.connect(right)

        return left

    now = time.time()
    rec_connect(gs)
    timings.times["connect"] = time.time() - now
    per_connect = timings.times["connect"] / count

    # self.assertLess(per_connect, 80e-6)
    # self.assertLess(timings.times["connect 2"], 20e-6)
    # self.assertLess(timings.times["connect 1024"], 3e-3)
    # self.assertLess(timings.times["split 1024"], 50e-3)
    # self.assertLess(timings.times["instance"], 300e-3)
    # self.assertLess(timings.times["connect"], 1200e-3)
    logger.info(timings)
    logger.info(f"----> Avg/connect: {per_connect*1e6:.2f} us")


def test_performance_graph_merge_it():
    timings = Times()
    count = 2**14
    logger.info(f"Count: {count}")

    gs = times(count, GraphInterface)
    timings.add("instance")

    for gl, gr in pairwise(gs):
        gl.connect(gr)

    timings.add("connect")

    assert gs[0].G.node_count == count

    per_connect = timings.times["connect"] / count
    # self.assertLess(timings.times["connect"], 500e-3)
    # self.assertLess(timings.times["instance"], 200e-3)
    # self.assertLess(per_connect, 25e-6)
    logger.info(timings)
    logger.info(f"----> Avg/connect: {per_connect*1e6:.2f} us")
