# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import pairwise
from textwrap import indent
from typing import Callable

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.solver import LOG_PICK_SOLVE
from faebryk.core.solver.utils import S_LOG, set_log_level
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


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
def test_performance_pick_rc_formulas():
    GROUPS = 4
    GROUP_SIZE = 4
    INCREASE = 10 * P.percent
    TOLERANCE = 20 * P.percent

    class App(Module):
        res = L.list_field(GROUPS * GROUP_SIZE, F.Resistor)

        def __preinit__(self):
            increase = L.Range.from_center_rel(INCREASE, TOLERANCE) + L.Single(
                100 * P.percent
            )

            for i in range(GROUPS):
                for m1, m2 in pairwise(self.res[i::GROUPS]):
                    m2.resistance.constrain_subset(m1.resistance * increase)
                    # solver doesn't do equation reordering, so we need to reverse
                    m1.resistance.constrain_subset(m2.resistance / increase)

    timings = Times(multi_sample_strategy=Times.MultiSampleStrategy.AVG_ACC)

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
        params = {k: v for k, v in sorted(params.items(), key=lambda t: t[0])}
        logger.info(f"Params:{indented_container(params, use_repr=False)}")
        S_LOG.set(True, force=True)
        LOG_PICK_SOLVE.set(True, force=True)
        set_log_level(logging.DEBUG)
        solver.update_superset_cache(app)
        # assert False
        return
    finally:
        logger.info(f"\n{timings}")

    picked_values = {
        m.get_full_name(): str(m.resistance.try_get_literal()) for m in app.res
    }
    logger.info(f"Picked values: {indented_container(picked_values)}")

    pick_time = timings.get_formatted("pick", strat=Times.MultiSampleStrategy.ACC)
    logger.info(f"Pick duration {GROUPS}x{GROUP_SIZE}: {pick_time}")
