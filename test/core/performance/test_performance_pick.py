# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.library import L
from faebryk.libs.picker.picker import pick_part_recursively
from faebryk.libs.test.times import Times

logger = logging.getLogger(__name__)


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
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
@pytest.mark.usefixtures("setup_project_config")
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
@pytest.mark.usefixtures("setup_project_config")
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
