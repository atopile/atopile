# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.library._F as F
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.test.times import Times

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
    timings = Times(cnt=cnt, unit="us")

    instances = [(mif_type(), mif_type()) for _ in range(cnt)]
    timings.add(f"{mif_type.__name__}: construct")

    for inst1, inst2 in instances:
        inst1.connect(inst2)
    timings.add(f"{mif_type.__name__}: connect")

    for inst1, inst2 in instances:
        assert inst1.is_connected_to(inst2)
    timings.add(f"{mif_type.__name__}: is_connected")

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
    timings = Times(cnt=1, unit="ms")

    instances = [mif_type() for _ in range(cnt)]
    timings.add(f"{mif_type.__name__}: construct")

    for other in instances[1:]:
        instances[0].connect(other)
    timings.add(f"{mif_type.__name__}: connect")

    assert instances[0].is_connected_to(instances[-1])
    timings.add(f"{mif_type.__name__}: is_connected")

    if issubclass(mif_type, ModuleInterface):
        list(instances[0].get_connected())
    else:
        instances[0].edges
    timings.add(f"{mif_type.__name__}: get_connected")

    assert instances[0].is_connected_to(instances[-1])
    timings.add(f"{mif_type.__name__}: is_connected cached")

    logger.info(f"\n{timings}")


@pytest.mark.parametrize(
    "module_type",
    [
        F.USB2514B,
        F.RP2040,
    ],
)
def test_performance_mifs_bus_params(module_type):
    timings = Times()

    app = module_type()
    timings.add(f"{module_type.__name__}: construct")

    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    timings.add(f"{module_type.__name__}: resolve")

    logger.info(f"\n{timings}")


@pytest.mark.slow
def test_performance_mifs_no_connect():
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
