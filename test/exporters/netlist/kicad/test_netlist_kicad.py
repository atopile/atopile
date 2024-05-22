# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest

from faebryk.core.graph import Graph
from faebryk.exporters.netlist.graph import attach_nets_and_kicad_info
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_graph
from faebryk.library.can_attach_to_footprint import can_attach_to_footprint
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_defined import has_designator_defined
from faebryk.library.has_designator_prefix import has_designator_prefix
from faebryk.library.Net import Net
from faebryk.libs.app.designators import (
    attach_random_designators,
    override_names_with_designators,
)

logger = logging.getLogger(__name__)


# Netlists --------------------------------------------------------------------
def _test_netlist_graph():
    from faebryk.library.Resistor import Resistor
    from faebryk.library.SMDTwoPin import SMDTwoPin

    resistor1 = Resistor().builder(lambda r: r.PARAMs.resistance.merge(100))
    resistor2 = Resistor().builder(lambda r: r.PARAMs.resistance.merge(200))
    power = ElectricPower()

    # net labels
    vcc = Net.with_name("+3V3")
    gnd = Net.with_name("GND")
    power.IFs.hv.connect(vcc.IFs.part_of)
    power.IFs.lv.connect(gnd.IFs.part_of)

    # connect
    resistor1.IFs.unnamed[0].connect(power.IFs.hv)
    resistor1.IFs.unnamed[1].connect(power.IFs.lv)
    resistor2.IFs.unnamed[0].connect(resistor1.IFs.unnamed[0])
    resistor2.IFs.unnamed[1].connect(resistor1.IFs.unnamed[1])

    # attach footprint & designator
    for i, r in enumerate([resistor1, resistor2]):
        r.get_trait(can_attach_to_footprint).attach(SMDTwoPin(SMDTwoPin.Type._0805))
        r.add_trait(
            has_designator_defined(
                resistor1.get_trait(has_designator_prefix).get_prefix() + str(i + 1)
            )
        )

    # make netlist
    G = Graph([resistor1, resistor2])
    attach_random_designators(G)
    override_names_with_designators(G)
    attach_nets_and_kicad_info(G)
    t2 = make_t2_netlist_from_graph(G)
    for comp in t2["comps"]:
        del comp.properties["faebryk_name"]
    netlist = from_faebryk_t2_netlist(t2)

    # test
    _, netlist_t2 = _test_netlist_t2()
    kicad_netlist_t2 = from_faebryk_t2_netlist(netlist_t2)
    success = netlist == kicad_netlist_t2
    if not success:
        logger.error("Graph != T2")
        logger.error("T2: %s", kicad_netlist_t2)
        logger.error("Graph: %s", netlist)

    return success, netlist


def _test_netlist_t2():
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist.netlist import Component, Net, Vertex

    # t2_netlist = [(properties, vertices=[comp=(name, value, properties), pin)])]

    resistor1 = Component(
        name="R1",
        value="100Ω",
        properties={
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    resistor2 = Component(
        name="R2",
        value="200Ω",
        properties={
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    netlist = {
        "nets": [
            Net(
                properties={
                    "name": "GND",
                },
                vertices=[
                    Vertex(
                        component=resistor1,
                        pin="2",
                    ),
                    Vertex(
                        component=resistor2,
                        pin="2",
                    ),
                ],
            ),
            Net(
                properties={
                    "name": "+3V3",
                },
                vertices=[
                    Vertex(
                        component=resistor1,
                        pin="1",
                    ),
                    Vertex(
                        component=resistor2,
                        pin="1",
                    ),
                ],
            ),
        ],
        "comps": [resistor1, resistor2],
    }
    logger.debug("T2 netlist:", netlist)

    kicad_net = from_faebryk_t2_netlist(netlist)
    kicad_net_manu = _test_netlist_manu()

    success = kicad_net == kicad_net_manu
    if not success:
        logger.error("T2 != Manu")
        logger.error(kicad_net_manu)

    return success, netlist


def _test_netlist_manu():
    import itertools

    import faebryk.libs.kicad.sexp as sexp
    from faebryk.exporters.netlist.kicad.netlist_kicad import (
        _defaulted_comp,
        _defaulted_netlist,
        _gen_net,
        _gen_node,
    )

    # Footprint pins are just referenced by number through netlist of symbol
    # We only need
    #   - components
    #       - ref
    #       - value (for silk)
    #       - footprint
    #       - tstamp (uuid gen)
    #   - nets
    #       - code (uuid gen)
    #       - name
    #       - nodes
    #           - ref (comp)
    #           - pin (of footprint)
    # Careful comps need distinct timestamps
    tstamp = itertools.count(1)

    resistor_comp = _defaulted_comp(
        ref="R1",
        value="100Ω",
        footprint="Resistor_SMD:R_0805_2012Metric",
        tstamp=next(tstamp),
        fields=[],
        properties={},
    )
    resistor_comp2 = _defaulted_comp(
        ref="R2",
        value="200Ω",
        footprint="Resistor_SMD:R_0805_2012Metric",
        tstamp=next(tstamp),
        fields=[],
        properties={},
    )

    device_nets = [
        _gen_net(
            code=1,
            name="+3V3",
            nodes=[
                _gen_node(
                    ref="R1",
                    pin="1",
                ),
                _gen_node(
                    ref="R2",
                    pin="1",
                ),
            ],
        ),
        _gen_net(
            code=2,
            name="GND",
            nodes=[
                _gen_node(
                    ref="R1",
                    pin="2",
                ),
                _gen_node(
                    ref="R2",
                    pin="2",
                ),
            ],
        ),
    ]

    netlist = _defaulted_netlist(
        components=[resistor_comp, resistor_comp2],
        nets=[*device_nets],
    )

    sexpnet = sexp.gensexp(netlist)
    assert isinstance(sexpnet, str)
    sexpnet = sexp.prettify_sexp_string(sexpnet)

    return sexpnet


class TestNetlist(unittest.TestCase):
    def test_netlist(self):
        ok, _ = _test_netlist_t2()
        self.assertTrue(ok)

        ok, _ = _test_netlist_graph()
        self.assertTrue(ok)
