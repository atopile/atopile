# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
import unittest
from itertools import pairwise
from typing import Callable

import pytest

import faebryk.library._F as F
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.core.parameter import Parameter
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.library import L
from faebryk.libs.picker.picker import pick_part_recursively
from faebryk.libs.test.times import Times
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


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

            logger.info(f"{test_name:-<80}")
            logger.info(f"{timings!r}")
            logger.info(str(G))
            return timings

        # _common_timings(lambda: _factory_simple_resistors(100), "simple")
        # return

        for i in range(2, 5):
            count = 10 * 2**i
            timings = _common_timings(
                lambda: _factory_simple_resistors(count), f"Simple resistors: {count}"
            )
            per_resistor = timings.times["instance"] / count
            logger.info(f"----> Avg/resistor: {per_resistor*1e3:.2f} ms")

        logger.info("=" * 80)
        for i in range(2, 5):
            count = 10 * 2**i
            timings = _common_timings(
                lambda: _factory_interconnected_resistors(count),
                f"Connected resistors: {count}",
            )
            per_resistor = timings.times["instance"] / count
            logger.info(f"----> Avg/resistor: {per_resistor*1e3:.2f} ms")

    def test_graph_merge_rec(self):
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

    def test_graph_merge_it(self):
        timings = Times()
        count = 2**14
        logger.info(f"Count: {count}")

        gs = times(count, GraphInterface)
        timings.add("instance")

        for gl, gr in pairwise(gs):
            gl.connect(gr)

        timings.add("connect")

        self.assertEqual(gs[0].G.node_count, count)

        per_connect = timings.times["connect"] / count
        # self.assertLess(timings.times["connect"], 500e-3)
        # self.assertLess(timings.times["instance"], 200e-3)
        # self.assertLess(per_connect, 25e-6)
        logger.info(timings)
        logger.info(f"----> Avg/connect: {per_connect*1e6:.2f} us")

    def test_mif_connect_check(self):
        cnt = 100

        timings = Times(cnt=cnt, unit="us")

        for t in [
            GraphInterface,
            ModuleInterface,
            F.Electrical,
            F.ElectricPower,
            F.ElectricLogic,
            F.I2C,
        ]:
            instances = [(t(), t()) for _ in range(cnt)]
            timings.add(f"{t.__name__}: construct")

            for inst1, inst2 in instances:
                inst1.connect(inst2)
            timings.add(f"{t.__name__}: connect")

            for inst1, inst2 in instances:
                self.assertTrue(inst1.is_connected_to(inst2))
            timings.add(f"{t.__name__}: is_connected")

        logger.info(f"\n{timings}")

    def test_mif_connect_hull(self):
        cnt = 30

        timings = Times(cnt=1, unit="ms")

        for t in [
            GraphInterface,
            ModuleInterface,
            F.Electrical,
            F.ElectricPower,
            F.ElectricLogic,
            F.I2C,
        ]:
            instances = [t() for _ in range(cnt)]
            timings.add(f"{t.__name__}: construct")

            for other in instances[1:]:
                instances[0].connect(other)
            timings.add(f"{t.__name__}: connect")

            self.assertTrue(instances[0].is_connected_to(instances[-1]))
            timings.add(f"{t.__name__}: is_connected")

            if issubclass(t, ModuleInterface):
                list(instances[0].get_connected())
            else:
                instances[0].edges
            timings.add(f"{t.__name__}: get_connected")

            self.assertTrue(instances[0].is_connected_to(instances[-1]))
            timings.add(f"{t.__name__}: is_connected cached")

        logger.info(f"\n{timings}")

    def test_complex_module(self):
        timings = Times()

        modules = [
            F.USB2514B,
            F.RP2040,
        ]

        for t in modules:
            app = t()  # noqa: F841
            timings.add(f"{t.__name__}: construct")

            F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
            timings.add(f"{t.__name__}: resolve")

        logger.info(f"\n{timings}")

    def test_no_connect(self):
        CNT = 30

        timings = Times()

        app = F.RP2040_ReferenceDesign()
        timings.add("construct")

        for i in range(CNT):
            list(app.rp2040.power_core.get_connected())
            timings.add(f"_get_connected {i}")

        all_times = [
            timings.times[k] for k in timings.times if k.startswith("_get_connected")
        ]

        timings.times["min"] = min(all_times)
        timings.times["max"] = max(all_times)
        timings.times["avg"] = sum(all_times) / len(all_times)
        timings.times["median"] = sorted(all_times)[len(all_times) // 2]
        timings.times["80%"] = sorted(all_times)[int(0.8 * len(all_times))]
        timings.times["total"] = sum(all_times)

        logger.info(f"\n{timings}")


# TODO dont commit
@pytest.mark.slow
def test_complex_module_full():
    timings = Times()

    class App(Module):
        rp2040: F.RP2040
        ldo: F.LDO
        led: F.LED

    app = App()
    timings.add("construct")

    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    timings.add("resolve bus params")

    solver = DefaultSolver()

    p = next(iter(app.get_children(direct_only=False, types=Parameter)))
    solver.inspect_get_known_supersets(p)
    timings.add("pre-solve")

    pick_part_recursively(app, solver)
    timings.add("pick")

    logger.info(f"\n{timings}")


@pytest.mark.slow
@pytest.mark.xfail(reason="TODO")
def test_very_complex_module_full():
    timings = Times()

    app = F.RP2040_ReferenceDesign()
    timings.add("construct")

    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    timings.add("resolve bus params")

    solver = DefaultSolver()

    p = next(iter(app.get_children(direct_only=False, types=Parameter)))
    solver.inspect_get_known_supersets(p)
    timings.add("pre-solve")

    pick_part_recursively(app, solver)
    timings.add("pick")

    logger.info(f"\n{timings}")


@pytest.mark.slow
def test_complex_module_comp_count():
    timings = Times()

    class App(Module):
        caps = L.f_field(F.MultiCapacitor)(10)

    app = App()
    timings.add("construct")

    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    timings.add("resolve bus params")

    solver = DefaultSolver()

    p = next(iter(app.get_children(direct_only=False, types=Parameter)))
    solver.inspect_get_known_supersets(p)
    timings.add("pre-solve")

    pick_part_recursively(app, solver)
    timings.add("pick")

    logger.info(f"\n{timings}")
