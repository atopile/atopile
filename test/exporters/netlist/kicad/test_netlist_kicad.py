# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import itertools
import logging

import pytest

import faebryk.library._F as F
from faebryk.exporters.netlist.graph import attach_nets
from faebryk.exporters.netlist.kicad.netlist_kicad import (
    attach_kicad_info,
    faebryk_netlist_to_kicad,
)
from faebryk.exporters.netlist.netlist import FBRKNetlist, make_fbrk_netlist_from_graph
from faebryk.libs.app.designators import (
    attach_random_designators,
)
from faebryk.libs.kicad.fileformats_latest import (
    C_fields,
    C_kicad_netlist_file,
)
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


# Netlists --------------------------------------------------------------------
@pytest.fixture
def netlist_graph():
    resistor1 = F.Resistor().builder(lambda r: r.resistance.alias_is(100 * P.ohm))
    resistor2 = F.Resistor().builder(lambda r: r.resistance.alias_is(200 * P.ohm))
    power = F.ElectricPower()

    # net labels
    vcc = F.Net.with_name("+3V3")
    gnd = F.Net.with_name("GND")
    power.hv.connect(vcc.part_of)
    power.lv.connect(gnd.part_of)

    # connect
    resistor1.unnamed[0].connect(power.hv)
    resistor1.unnamed[1].connect(power.lv)
    resistor2.unnamed[0].connect(resistor1.unnamed[0])
    resistor2.unnamed[1].connect(resistor1.unnamed[1])

    # attach footprint & designator
    for i, r in enumerate([resistor1, resistor2]):
        r.get_trait(F.can_attach_to_footprint).attach(
            F.SMDTwoPin(SMDSize.I0805, F.SMDTwoPin.Type.Resistor)
        )
        r.add(
            F.has_designator(
                resistor1.get_trait(F.has_designator_prefix).get_prefix() + str(i + 1)
            )
        )

    # make netlist
    G = resistor1.get_graph
    attach_random_designators(G())
    attach_nets(G())
    attach_kicad_info(G())
    return make_fbrk_netlist_from_graph(G())


@pytest.fixture
def netlist_t2():
    # t2_netlist = [(properties, vertices=[comp=(name, value, properties), pin)])]
    resistor1 = FBRKNetlist.Component(
        name="R1",
        value="100Ω",
        properties={
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    resistor2 = FBRKNetlist.Component(
        name="R2",
        value="200Ω",
        properties={
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    return FBRKNetlist(
        nets=[
            FBRKNetlist.Net(
                properties={
                    "name": "GND",
                },
                vertices=[
                    FBRKNetlist.Net.Vertex(
                        component=resistor1,
                        pin="2",
                    ),
                    FBRKNetlist.Net.Vertex(
                        component=resistor2,
                        pin="2",
                    ),
                ],
            ),
            FBRKNetlist.Net(
                properties={
                    "name": "+3V3",
                },
                vertices=[
                    FBRKNetlist.Net.Vertex(
                        component=resistor1,
                        pin="1",
                    ),
                    FBRKNetlist.Net.Vertex(
                        component=resistor2,
                        pin="1",
                    ),
                ],
            ),
        ],
        comps=[resistor1, resistor2],
    )


@pytest.fixture
def netlist_manu():
    # Footprint pins are just referenced by number through netlist of symbol
    # Careful comps need distinct timestamps
    tstamp = itertools.count(1)

    N = C_kicad_netlist_file
    return C_kicad_netlist_file(
        N.C_netlist(
            version="E",
            components=N.C_netlist.C_components(
                comps=[
                    N.C_netlist.C_components.C_component(
                        ref="R1",
                        value="100Ω",
                        footprint="Resistor_SMD:R_0805_2012Metric",
                        tstamps=str(next(tstamp)),
                        fields=C_fields(fields={}),
                        propertys={},
                    ),
                    N.C_netlist.C_components.C_component(
                        ref="R2",
                        value="200Ω",
                        footprint="Resistor_SMD:R_0805_2012Metric",
                        tstamps=str(next(tstamp)),
                        fields=C_fields(fields={}),
                        propertys={},
                    ),
                ]
            ),
            nets=N.C_netlist.C_nets(
                nets=[
                    N.C_netlist.C_nets.C_net(
                        code=1,
                        name="+3V3",
                        nodes=[
                            N.C_netlist.C_nets.C_net.C_node(
                                ref="R1",
                                pin="1",
                            ),
                            N.C_netlist.C_nets.C_net.C_node(
                                ref="R2",
                                pin="1",
                            ),
                        ],
                    ),
                    N.C_netlist.C_nets.C_net(
                        code=2,
                        name="GND",
                        nodes=[
                            N.C_netlist.C_nets.C_net.C_node(
                                ref="R1",
                                pin="2",
                            ),
                            N.C_netlist.C_nets.C_net.C_node(
                                ref="R2",
                                pin="2",
                            ),
                        ],
                    ),
                ]
            ),
        ),
    )


def test_netlist_t2(netlist_t2, netlist_manu):
    netlist_t2 = faebryk_netlist_to_kicad(netlist_t2)
    assert netlist_t2.dumps() == netlist_manu.dumps()


def test_netlist_graph(netlist_graph, netlist_t2):
    for comp in netlist_graph.comps:
        assert isinstance(comp.properties, dict)
        comp.properties.pop("atopile_address", None)

    netlist_graph = faebryk_netlist_to_kicad(netlist_graph)
    netlist_t2 = faebryk_netlist_to_kicad(netlist_t2)
    assert netlist_graph.dumps() == netlist_t2.dumps()
