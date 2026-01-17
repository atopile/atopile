# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.test.times import Times

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "node_type",
    [
        F.Electrical,
        F.ElectricPower,
        F.ElectricLogic,
        F.I2C,
    ],
)
def test_performance_mifs_connect_check(node_type):
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    cnt = 100
    timings = Times(strategy=Times.Strategy.AVG)
    name = node_type.__name__

    type = node_type.bind_typegraph(tg)
    instances = [
        (type.create_instance(g=g), type.create_instance(g=g)) for _ in range(cnt)
    ]
    timings.add(f"{name}:construct")

    for inst1, inst2 in instances:
        inst1._is_interface.get().connect_to(inst2)
        timings.add(f"{name}:connect_to")

    for inst1, inst2 in instances:
        assert inst1._is_interface.get().is_connected_to(inst2)
        timings.add(f"{name}:is_connected_to")

    # TODO formatting of timings is broken rn
    # logger.info(f"\n{timings}")


@pytest.mark.parametrize(
    "node_type",
    [
        F.Electrical,
        F.ElectricPower,
        F.ElectricLogic,
        F.I2C,
    ],
)
def test_performance_mifs_connect_hull(node_type):
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    cnt = 30
    timings = Times()
    name = node_type.__name__

    type = node_type.bind_typegraph(tg)
    instances = [type.create_instance(g=g) for _ in range(cnt)]
    timings.add(f"{name}:construct")

    for other in instances[1:]:
        instances[0]._is_interface.get().connect_to(other)
        timings.add(f"{name}:connect_to")

    assert instances[0]._is_interface.get().is_connected_to(instances[-1])
    timings.add(f"{name}:is_connected_to")

    list(instances[0]._is_interface.get().get_connected())
    timings.add(f"{name}:get_connected")

    assert instances[0]._is_interface.get().is_connected_to(instances[-1])
    timings.add(f"{name}:is_connected cached")

    # TODO formatting of timings is broken rn
    # logger.info(f"\n{timings}")


# @pytest.mark.parametrize(
#     "module_type",
#     [
#         USB2514B,
#         RP2040,
#     ],
# )
# def test_performance_mifs_bus_params(module_type):
#     timings = Times()
#     name = module_type.__name__

#     app = module_type()
#     timings.add(name, "construct")

#     F.is_bus_parameter.resolve_bus_parameters(app.tg)
#     timings.add(name, "resolve")

#     logger.info(f"\n{timings}")


# @pytest.mark.slow
# def test_performance_mifs_no_connect():
#     CNT = 30
#     timings = Times(strategy=Times.Strategy.ALL)

#     app = RP2040_ReferenceDesign()
#     timings.add("construct")

#     ensure_typegraph(app)

#     for i in range(CNT):
#         list(app.rp2040.power_core.get_connected())
#         timings.add("get_connected")

#     logger.info(f"\n{timings}")
