# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.graph import InstanceGraphFunctions
from faebryk.libs.test.times import Times
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


def ensure_typegraph(node: fabll.Node) -> None:
    """Build TypeGraph, instantiate, and bind for the node's tree."""

    root = node._get_root()

    # Assert not already built
    assert not root.get_lifecycle_stage() == "runtime", "TypeGraph already built"
    assert not getattr(root, "_instance_bound", None), "Instance already bound"

    # Build type graph
    typegraph, _ = root.create_typegraph()

    # Instantiate instance graph (independent of fabll.Node)
    instance_root = InstanceGraphFunctions.create(typegraph, type(root).__qualname__)

    # Bind instance to tree
    root._bind_instance_hierarchy(instance_root)

    # Execute runtime hooks
    root._execute_runtime_functions()


@pytest.mark.parametrize(
    "mif_type",
    [
        fabll.Node,
        F.Electrical,
        F.ElectricPower,
        F.ElectricLogic,
        F.I2C,
    ],
)
def test_performance_mifs_connect_check(mif_type):
    cnt = 100
    timings = Times(multi_sample_strategy=Times.MultiSampleStrategy.AVG)
    name = mif_type.__name__

    def _construct():
        out = mif_type(), mif_type()
        timings.add(name, "construct")
        return out

    instances = times(cnt, _construct)

    for inst1, inst2 in instances:
        inst1.connect(inst2)
        timings.add(name, "connect")

    for inst1, inst2 in instances:
        assert inst1.is_connected_to(inst2)
        timings.add(name, "is_connected")

    logger.info(f"\n{timings}")


@pytest.mark.parametrize(
    "mif_type",
    [
        fabll.Node,
        F.Electrical,
        F.ElectricPower,
        F.ElectricLogic,
        F.I2C,
    ],
)
def test_performance_mifs_connect_hull(mif_type):
    cnt = 30
    timings = Times()
    name = mif_type.__name__

    def _construct():
        out = mif_type()
        timings.add(name, "construct")
        return out

    instances = times(cnt, _construct)

    for other in instances[1:]:
        instances[0].connect(other)
        timings.add(name, "connect")

    assert instances[0].is_connected_to(instances[-1])
    timings.add(name, "is_connected")

    if issubclass(mif_type, fabll.ModuleInterface):
        ensure_typegraph(instances[0])
        list(instances[0].get_connected())
    else:
        instances[0].edges
    timings.add(name, "get_connected")

    assert instances[0].is_connected_to(instances[-1])
    timings.add(name, "is_connected cached")

    logger.info(f"\n{timings}")


@pytest.mark.parametrize(
    "module_type",
    [
        USB2514B,
        RP2040,
    ],
)
def test_performance_mifs_bus_params(module_type):
    timings = Times()
    name = module_type.__name__

    app = module_type()
    timings.add(name, "construct")

    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    timings.add(name, "resolve")

    logger.info(f"\n{timings}")


@pytest.mark.slow
def test_performance_mifs_no_connect():
    CNT = 30
    timings = Times(multi_sample_strategy=Times.MultiSampleStrategy.ALL)

    app = RP2040_ReferenceDesign()
    timings.add("construct")

    ensure_typegraph(app)

    for i in range(CNT):
        list(app.rp2040.power_core.get_connected())
        timings.add("get_connected")

    logger.info(f"\n{timings}")
