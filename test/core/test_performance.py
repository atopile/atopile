# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import time
import unittest
from itertools import pairwise
from typing import Callable

import faebryk.library._F as F
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.libs.library import L
from faebryk.libs.test.times import Times
from faebryk.libs.util import times


class TestPerformance(unittest.TestCase):
    def test_get_all(self):
        def _factory_simple_resistors(count: int):
            class App(Module):
                resistors = L.list_field(count, F.Resistor)

                def __init__(self, timings: Times) -> None:
                    super().__init__()
                    self._timings = timings

                def __preinit__(self):
                    self._timings.add("setup")

            return App

        def _factory_interconnected_resistors(count: int):
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

        def _common_timings(
            factory: Callable[[], Callable[[Times], Module]], test_name: str
        ):
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

            for n in [app, app.resistors[0]]:
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

            print(f"{test_name:-<80}")
            print(f"{timings!r}")
            print(str(G))
            return timings

        # _common_timings(lambda: _factory_simple_resistors(100), "simple")
        # return

        for i in range(2, 5):
            count = 10 * 2**i
            timings = _common_timings(
                lambda: _factory_simple_resistors(count), f"Simple resistors: {count}"
            )
            per_resistor = timings.times["instance"] / count
            print(f"----> Avg/resistor: {per_resistor*1e3:.2f} ms")

        print("=" * 80)
        for i in range(2, 5):
            count = 10 * 2**i
            timings = _common_timings(
                lambda: _factory_interconnected_resistors(count),
                f"Connected resistors: {count}",
            )
            per_resistor = timings.times["instance"] / count
            print(f"----> Avg/resistor: {per_resistor*1e3:.2f} ms")

    def test_graph_merge_rec(self):
        timings = Times()
        count = 2**14
        print(f"Count: {count}")

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
        print(timings)
        print(f"----> Avg/connect: {per_connect*1e6:.2f} us")
        from faebryk.core.graphinterface import GraphImpl

        print("Counter", GraphImpl.counter, GraphImpl.counter - count)

    def test_graph_merge_it(self):
        timings = Times()
        count = 2**14
        print(f"Count: {count}")

        gs = times(count, GraphInterface)
        timings.add("instance")

        for gl, gr in pairwise(gs):
            gl.connect(gr)

        timings.add("connect")

        self.assertEqual(gs[0].G.node_cnt, count)

        per_connect = timings.times["connect"] / count
        # self.assertLess(timings.times["connect"], 500e-3)
        # self.assertLess(timings.times["instance"], 200e-3)
        # self.assertLess(per_connect, 25e-6)
        print(timings)
        print(f"----> Avg/connect: {per_connect*1e6:.2f} us")

        from faebryk.core.graphinterface import GraphImpl

        print("Counter", GraphImpl.counter, GraphImpl.counter - count)


if __name__ == "__main__":
    unittest.main()