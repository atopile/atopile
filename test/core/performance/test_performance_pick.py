# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import pairwise
from textwrap import indent
from typing import Callable

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Multiply, Parameter
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.library import L
from faebryk.libs.picker.picker import (
    NO_PROGRESS_BAR,
    PickError,
    get_pick_tree,
    pick_topologically,
)
from faebryk.libs.test.times import Times
from faebryk.libs.units import P
from faebryk.libs.util import indented_container

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def _setup():
    NO_PROGRESS_BAR.set(True)


class _RP2040_Basic(Module):
    rp2040: F.RP2040
    ldo: F.LDO
    led: F.LED


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.parametrize(
    "module_type",
    [
        _RP2040_Basic,
        F.RP2040_ReferenceDesign,
        lambda: F.MultiCapacitor(10),
    ],
)
def test_performance_pick_real_module(module_type: Callable[[], Module]):
    timings = Times()

    app = module_type()
    timings.add("construct")

    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    timings.add("resolve bus params")

    pick_tree = get_pick_tree(app)
    timings.add("pick tree")

    solver = DefaultSolver()
    p = next(iter(app.get_children(direct_only=False, types=Parameter)))
    solver.inspect_get_known_supersets(p)
    timings.add("pre-solve")

    with timings.as_global("pick"):
        pick_topologically(pick_tree, solver)

    logger.info(f"\n{timings}")


def test_performance_pick_rc_formulas():
    class App(Module):
        caps = L.list_field(0, F.Capacitor)
        res = L.list_field(2, F.Resistor)

        def __preinit__(self):
            # for m1, m2 in pairwise(self.caps):
            #    m2.capacitance.constrain_subset(Add(m1.capacitance, 10 * P.pF))

            for m1, m2 in pairwise(self.res):
                m2.resistance.constrain_ge(Multiply(m1.resistance, 109 * P.percent))

            # self.caps[-1].capacitance / P.F

    timings = Times()

    app = App()
    timings.add("construct")

    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    timings.add("resolve bus params")

    pick_tree = get_pick_tree(app)
    timings.add("pick tree")

    solver = DefaultSolver()
    try:
        with timings.as_global("pick"):
            pick_topologically(pick_tree, solver)
    except PickError as e:
        logger.error(f"Error picking: {e.args[0]}")
        params = {
            m.get_full_name(): "\n" + indent(m.pretty_params(solver), prefix="  ")
            for m in app.get_children_modules(direct_only=True, types=Module)
        }
        logger.info(f"Params:{indented_container(params, use_repr=False)}")
        assert False
    finally:
        logger.info(f"\n{timings}")

    picked_values = {
        m.get_full_name(): str(m.capacitance.try_get_literal()) for m in app.caps
    } | {m.get_full_name(): str(m.resistance.try_get_literal()) for m in app.res}
    logger.info(f"Picked values: {indented_container(picked_values)}")
