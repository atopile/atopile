# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import pairwise
from textwrap import indent
from typing import Callable

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.algorithm import get_algorithms
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
from faebryk.libs.util import ConfigFlagInt, indented_container
from test.common.resources.fabll_modules.RP2040 import RP2040
from test.common.resources.fabll_modules.RP2040_ReferenceDesign import (
    RP2040_ReferenceDesign,
)

logger = logging.getLogger(__name__)

GROUPS = ConfigFlagInt("GROUPS", 4)
GROUP_SIZE = ConfigFlagInt("GROUP_SIZE", 4)


@pytest.fixture(autouse=True)
def _setup():
    NO_PROGRESS_BAR.set(True)


class _RP2040_Basic(Module):
    rp2040: RP2040
    ldo: F.LDO
    led: F.LED


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.parametrize(
    "module_type",
    [
        _RP2040_Basic,
        RP2040_ReferenceDesign,
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

    with timings.as_global("pick"):
        pick_topologically(pick_tree, solver)

    logger.info(f"\n{timings}")


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
def test_performance_pick_rc_formulas():
    _GROUPS = int(GROUPS)
    _GROUP_SIZE = int(GROUP_SIZE)
    INCREASE = 10 * P.percent
    TOLERANCE = 20 * P.percent

    class App(Module):
        alias_res = L.list_field(_GROUPS, F.Resistor)
        res = L.list_field(_GROUPS * _GROUP_SIZE, F.Resistor)

        def __preinit__(self):
            increase = L.Range.from_center_rel(INCREASE, TOLERANCE) + L.Single(
                100 * P.percent
            )

            for i in range(_GROUPS):
                for m1, m2 in pairwise(self.res[i::_GROUPS]):
                    m2.resistance.constrain_subset(m1.resistance * increase)
                    # solver doesn't do equation reordering, so we need to reverse
                    m1.resistance.constrain_subset(m2.resistance / increase)
                self.alias_res[i].resistance.alias_is(self.res[i].resistance)

    timings = Times(multi_sample_strategy=Times.MultiSampleStrategy.ALL)

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

        def _is_algo(
            k: str, dirty: bool | None = None, terminal: bool | None = None
        ) -> bool:
            if "run_iteration:" not in k:
                return False
            if ":setup" in k or ":close" in k:
                return False
            if "clean" not in k and "dirty" not in k:
                return False
            if dirty is not None:
                if dirty and "dirty" not in k:
                    return False
                if not dirty and "clean" not in k:
                    return False
            if terminal is not None:
                if terminal and " terminal" not in k:
                    return False
                if not terminal and "non-terminal" not in k:
                    return False
            return True

        def _make_algo_group(dirty: bool | None = None, terminal: bool | None = None):
            dirty_str = "" if dirty is None else "dirty " if dirty else "clean "
            terminal_str = (
                "" if terminal is None else "terminal " if terminal else "non-terminal "
            )
            timings.make_group(
                f"{dirty_str}{terminal_str}algos",
                lambda k: _is_algo(k, dirty=dirty, terminal=terminal),
            )

        timings.add_seperator()
        for algo in get_algorithms():
            timings.make_group("Total " + algo.name, lambda k: algo.name + " " in k)
        timings.add_seperator()
        for i in [None, True, False]:
            for j in [None, True, False]:
                _make_algo_group(dirty=i, terminal=j)
        timings.add_seperator()
        timings.make_group(
            "mutator setup",
            lambda k: "run_iteration:setup" in k or "run_iteration:close" in k,
        )
        timings.make_group("backend wait", lambda k: "fetch parts" in k)
        timings.make_group("solver", lambda k: "algos" == k)
        logger.info(f"\n{timings.to_str(force_unit='ms')}")

    picked_values = {
        m.get_full_name(): str(m.resistance.try_get_literal()) for m in app.res
    }
    logger.info(f"Picked values: {indented_container(picked_values)}")

    pick_time = timings.get_formatted("pick", strat=Times.MultiSampleStrategy.ACC)
    logger.info(f"Pick duration {_GROUPS}x{_GROUP_SIZE}: {pick_time}")
