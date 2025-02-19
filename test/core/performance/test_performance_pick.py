# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Callable

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.picker.picker import (
    NO_PROGRESS_BAR,
    get_pick_tree,
    pick_topologically,
)
from faebryk.libs.test.times import Times

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
    timings.add("test", "construct")

    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    timings.add("test", "resolve bus params")

    pick_tree = get_pick_tree(app)
    timings.add("test", "pick tree")

    solver = DefaultSolver()
    p = next(iter(app.get_children(direct_only=False, types=Parameter)))
    solver.inspect_get_known_supersets(p)
    timings.add("test", "pre-solve")

    pick_topologically(pick_tree, solver, timings=timings)
    timings.add("test", "pick")

    logger.info(f"\n{timings}")
