# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.library._F as F
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.test.times import Times
from faebryk.libs.util import times
from test.common.resources.fabll_modules.RP2040 import RP2040
from test.common.resources.fabll_modules.RP2040_ReferenceDesign import (
    RP2040_ReferenceDesign,
)
from test.common.resources.fabll_modules.USB2514B import USB2514B

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "mif_type",
    [
        GraphInterface,
        ModuleInterface,
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
        GraphInterface,
        ModuleInterface,
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

    if issubclass(mif_type, ModuleInterface):
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

    for i in range(CNT):
        list(app.rp2040.power_core.get_connected())
        timings.add("get_connected")

    logger.info(f"\n{timings}")
