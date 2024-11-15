# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest

import faebryk.library._F as F
from faebryk.exporters.netlist.graph import attach_nets_and_kicad_info
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_graph
from faebryk.libs.app.designators import (
    attach_random_designators,
    override_names_with_designators,
)
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


# Netlists --------------------------------------------------------------------
def _test_netlist_graph():
    resistor1 = F.Resistor().builder(lambda r: r.resistance.merge(100 * P.ohm))
    resistor2 = F.Resistor().builder(lambda r: r.resistance.merge(200 * P.ohm))
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
            F.SMDTwoPin(F.SMDTwoPin.Type._0805)
        )
        r.add(
            F.has_designator_defined(
                resistor1.get_trait(F.has_designator_prefix).get_prefix() + str(i + 1)
            )
        )

    # make netlist
    G = resistor1.get_graph
    attach_random_designators(G())
    override_names_with_designators(G())
    attach_nets_and_kicad_info(G())
    t2 = make_t2_netlist_from_graph(G())
    for comp in t2.comps:
        del comp.properties["faebryk_name"]
    netlist = from_faebryk_t2_netlist(t2)

    # test
    _, netlist_t2 = _test_netlist_t2()
    kicad_netlist_t2 = from_faebryk_t2_netlist(netlist_t2)
    success = netlist.dumps() == kicad_netlist_t2.dumps()
    if not success:
        logger.error("Graph != T2")
        logger.error("T2: %s", kicad_netlist_t2)
        logger.error("Gr: %s", netlist)

    return success, netlist


def _test_netlist_t2():
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist.netlist import T2Netlist

    # t2_netlist = [(properties, vertices=[comp=(name, value, properties), pin)])]

    resistor1 = T2Netlist.Component(
        name="R1",
        value="100Ω",
        properties={
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    resistor2 = T2Netlist.Component(
        name="R2",
        value="200Ω",
        properties={
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    netlist = T2Netlist(
        nets=[
            T2Netlist.Net(
                properties={
                    "name": "GND",
                },
                vertices=[
                    T2Netlist.Net.Vertex(
                        component=resistor1,
                        pin="2",
                    ),
                    T2Netlist.Net.Vertex(
                        component=resistor2,
                        pin="2",
                    ),
                ],
            ),
            T2Netlist.Net(
                properties={
                    "name": "+3V3",
                },
                vertices=[
                    T2Netlist.Net.Vertex(
                        component=resistor1,
                        pin="1",
                    ),
                    T2Netlist.Net.Vertex(
                        component=resistor2,
                        pin="1",
                    ),
                ],
            ),
        ],
        comps=[resistor1, resistor2],
    )
    logger.debug("T2 netlist:", netlist)

    kicad_net = from_faebryk_t2_netlist(netlist)
    kicad_net_manu = _test_netlist_manu()

    success = kicad_net.dumps() == kicad_net_manu.dumps()
    if not success:
        logger.error("T2 != Manu")
        logger.error(kicad_net_manu)

    return success, netlist


def _test_netlist_manu():
    import itertools

    from faebryk.libs.kicad.fileformats import C_fields, C_kicad_netlist_file

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


class TestNetlist(unittest.TestCase):
    def test_netlist(self):
        ok, _ = _test_netlist_t2()
        self.assertTrue(ok)

        ok, _ = _test_netlist_graph()
        self.assertTrue(ok)
