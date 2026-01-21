# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import pairwise
from textwrap import indent

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import get_algorithms
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.core.solver.utils import S_LOG, set_log_level
from faebryk.libs.picker.picker import (
    NO_PROGRESS_BAR,
    PickError,
    get_pick_tree,
    pick_topologically,
)
from faebryk.libs.test.times import Times
from faebryk.libs.util import ConfigFlagInt, indented_container

logger = logging.getLogger(__name__)

GROUPS = ConfigFlagInt("GROUPS", 4)
GROUP_SIZE = ConfigFlagInt("GROUP_SIZE", 4)


@pytest.fixture(autouse=True)
def _setup():
    NO_PROGRESS_BAR.set(True)


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
def test_performance_pick_real_module():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    timings = Times()

    class _App(fabll.Node):
        resistors = [F.Resistor.MakeChild() for _ in range(2)]

    app = _App.bind_typegraph(tg).create_instance(g=g)
    timings.add("construct")

    # F.is_bus_parameter.resolve_bus_parameters(app.tg)
    # timings.add("resolve bus params")

    pick_tree = get_pick_tree(app)
    timings.add("pick tree")

    solver = Solver()

    # with timings.measure("pick"):
    pick_topologically(pick_tree, solver)
    timings.add("pick")

    logger.info(f"\n{timings}")


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
def test_performance_pick_rc_formulas():
    _GROUPS = int(GROUPS)
    _GROUP_SIZE = int(GROUP_SIZE)
    # increase factor: 1.1 +/- 20% = [0.88, 1.32]
    INCREASE_CENTER = 1.1
    INCREASE_TOLERANCE = 0.2

    timings = Times(strategy=Times.Strategy.ALL)

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        alias_res = [F.Resistor.MakeChild() for _ in range(_GROUPS)]
        res = [F.Resistor.MakeChild() for _ in range(_GROUPS * _GROUP_SIZE)]

    app = _App.bind_typegraph(tg).create_instance(g=g)
    timings.add("construct")

    # Create the increase factor literal (dimensionless)
    dl_unit = (
        F.Units.Dimensionless.bind_typegraph(tg).create_instance(g=g).is_unit.get()
    )
    increase_lit = (
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g=g)
        .setup_from_center_rel(
            center=INCREASE_CENTER, rel=INCREASE_TOLERANCE, unit=dl_unit
        )
        .can_be_operand.get()
    )

    # Set up constraints between resistors
    for i in range(_GROUPS):
        group_resistors = [
            app.res[j].get() for j in range(i, _GROUPS * _GROUP_SIZE, _GROUPS)
        ]
        for m1, m2 in pairwise(group_resistors):
            m1_res_op = m1.resistance.get().can_be_operand.get()
            m2_res_op = m2.resistance.get().can_be_operand.get()

            # m2.resistance in m1.resistance * increase
            mul_expr = F.Expressions.Multiply.c(m1_res_op, increase_lit)
            F.Expressions.IsSubset.from_operands(m2_res_op, mul_expr, assert_=True)

            # m1.resistance in m2.resistance / increase (solver doesn't reorder)
            div_expr = F.Expressions.Divide.c(m2_res_op, increase_lit)
            F.Expressions.IsSubset.from_operands(m1_res_op, div_expr, assert_=True)

        # alias_res[i].resistance = res[i].resistance
        alias_res_op = app.alias_res[i].get().resistance.get().can_be_operand.get()
        first_res_op = group_resistors[0].resistance.get().can_be_operand.get()
        F.Expressions.Is.from_operands(alias_res_op, first_res_op, assert_=True)

    timings.add("setup constraints")

    pick_tree = get_pick_tree(app)
    timings.add("pick tree")

    solver = Solver()
    try:
        with timings.measure("pick"):
            pick_topologically(pick_tree, solver)
    except PickError as e:
        logger.error(f"Error picking: {e.args[0]}")
        params = {
            m.get_full_name(): "\n" + indent(m.pretty_params(solver), prefix="  ")
            for m in app.get_children(
                direct_only=True, types=fabll.Node, required_trait=fabll.is_module
            )
        }
        params = {k: v for k, v in sorted(params.items(), key=lambda t: t[0])}
        logger.info(f"Params:{indented_container(params, use_repr=False)}")
        S_LOG.set(True, force=True)
        LOG_PICK_SOLVE.set(True, force=True)
        set_log_level(logging.DEBUG)
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
            timings.group(
                f"{dirty_str}{terminal_str}algos",
                lambda k: _is_algo(k, dirty=dirty, terminal=terminal),
            )

        timings.separator()
        for algo in get_algorithms():
            timings.group("Total " + algo.name, lambda k: algo.name + " " in k)
        timings.separator()
        for i in [None, True, False]:
            for j in [None, True, False]:
                _make_algo_group(dirty=i, terminal=j)
        timings.separator()
        timings.group(
            "mutator setup",
            lambda k: "run_iteration:setup" in k or "run_iteration:close" in k,
        )
        timings.group("backend wait", lambda k: "fetch parts" in k)
        timings.group("solver", lambda k: "algos" == k)
        logger.info(f"\n{timings.to_str()}")

    picked_values = {
        m.get().get_full_name(): str(m.get().resistance.get().try_extract_superset())
        for m in app.res
    }
    logger.info(f"Picked values: {indented_container(picked_values)}")

    pick_time = timings.get_formatted("pick", strategy=Times.Strategy.SUM)
    logger.info(f"Pick duration {_GROUPS}x{_GROUP_SIZE}: {pick_time}")


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    import typer

    from atopile.config import ProjectConfig, ProjectPaths, config

    with tempfile.TemporaryDirectory() as tmp_path_:
        tmp_path = Path(tmp_path_)
        config.project = ProjectConfig.skeleton(
            entry="", paths=ProjectPaths(build=tmp_path / "build", root=tmp_path)
        )

        typer.run(test_performance_pick_real_module)
