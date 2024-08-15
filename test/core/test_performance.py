# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import time
import unittest
from itertools import pairwise
from textwrap import indent
from typing import Callable

import faebryk.core.util as core_util
from faebryk.core.core import GraphInterface, Module, ModuleInterface
from faebryk.library.Resistor import Resistor
from faebryk.libs.util import times


class Times:
    def __init__(self) -> None:
        self.times = {}
        self.last_time = time.time()

    def add(self, name: str):
        now = time.time()
        if name not in self.times:
            self.times[name] = now - self.last_time
        self.last_time = now

    def _format_val(self, val: float):
        return f"{val * 1000:.2f}ms"

    def __repr__(self):
        formatted = {
            k: self._format_val(v)
            for k, v in self.times.items()
            if not k.startswith("_")
        }
        longest_name = max(len(k) for k in formatted)
        return "Timings: \n" + indent(
            "\n".join(f"{k:>{longest_name}}: {v:<10}" for k, v in formatted.items()),
            " " * 4,
        )


class TestPerformance(unittest.TestCase):
    def test_get_all(self):
        def _factory_simple_resistors(count: int):
            class App(Module):
                def __init__(self, timings: Times) -> None:
                    super().__init__()

                    class NODES(super().NODES()):
                        resistors = times(count, Resistor)

                    timings.add("NODES")

                    self.NODEs = NODES(self)
                    timings.add("set NODES")

            return App

        def _factory_interconnected_resistors(count: int):
            class App(Module):
                def __init__(self, timings: Times) -> None:
                    super().__init__()

                    class NODES(super().NODES()):
                        resistors = times(count, Resistor)

                    timings.add("NODES")

                    self.NODEs = NODES(self)
                    timings.add("set NODES")

                    core_util.connect_all_interfaces(
                        r.IFs.unnamed[0] for r in self.NODEs.resistors
                    )
                    timings.add("connect")

            return App

        def _common_timings(
            factory: Callable[[], Callable[[Times], Module]], test_name: str
        ):
            timings = Times()

            App = factory()
            timings.add("classdef")

            now = time.time()
            app = App(timings)
            timings.times["instance"] = time.time() - now

            G = app.get_graph()
            timings.add("graph")

            core_util.node_projected_graph(G)
            timings.add("get_all_nodes_graph")

            for n in [app, app.NODEs.resistors[0]]:
                name = type(n).__name__[0]

                core_util.get_node_children_all(n)
                timings.add(f"get_node_children_all {name}")

                core_util.get_node_tree(n)
                timings.add(f"get_node_tree {name}")

                core_util.get_mif_tree(n)
                timings.add(f"get_mif_tree {name}")

                core_util.get_node_direct_mods_or_mifs(n)
                timings.add(f"get_module_direct_children {name}")

                core_util.get_children(n, direct_only=True, types=ModuleInterface)
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
        from faebryk.core.core import GraphImpl

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

        from faebryk.core.core import GraphImpl

        print("Counter", GraphImpl.counter, GraphImpl.counter - count)


if __name__ == "__main__":
    unittest.main()
