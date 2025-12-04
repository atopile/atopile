# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import itertools
import logging

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.exporters.netlist.graph import attach_net_names, attach_nets
from faebryk.exporters.netlist.kicad.netlist_kicad import (
    attach_kicad_info,
    faebryk_netlist_to_kicad,
)
from faebryk.exporters.netlist.netlist import FBRKNetlist, make_fbrk_netlist_from_graph
from faebryk.libs.app.designators import (
    attach_random_designators,
)
from faebryk.libs.kicad.fileformats import kicad

# from faebryk.libs.smd import SMDSize

logger = logging.getLogger(__name__)


def make_instance[T: fabll.NodeT](
    tg: fbrk.TypeGraph, g: fabll.graph.GraphView, cls: type[T]
) -> T:
    return cls.bind_typegraph(tg=tg).create_instance(g=g)


# Netlists --------------------------------------------------------------------
@pytest.fixture
def netlist_graph():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    resistor = F.Resistor.bind_typegraph(tg=tg)

    resistor1 = resistor.create_instance(g=g)
    resistor2 = resistor.create_instance(g=g)
    power = F.ElectricPower.bind_typegraph(tg=tg).create_instance(g=g)

    r100 = (
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g)
        .setup_from_singleton(
            value=100,
            unit=F.Units.Ohm.bind_typegraph(tg).create_instance(g).is_unit.get(),
        )
    )
    r200 = (
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g)
        .setup_from_singleton(
            value=200,
            unit=F.Units.Ohm.bind_typegraph(tg).create_instance(g).is_unit.get(),
        )
    )

    resistor1.resistance.get().alias_to_literal(g, r100)
    resistor2.resistance.get().alias_to_literal(g, r200)

    fabll.Traits.create_and_add_instance_to(power.hv.get(), F.has_net_name).setup(
        name="+3V3", level=F.has_net_name.Level.EXPECTED
    )
    fabll.Traits.create_and_add_instance_to(power.lv.get(), F.has_net_name).setup(
        name="GND", level=F.has_net_name.Level.SUGGESTED
    )

    resistor1.unnamed[0].get()._is_interface.get().connect_to(power.hv.get())
    resistor1.unnamed[1].get()._is_interface.get().connect_to(power.lv.get())
    resistor2.unnamed[0].get()._is_interface.get().connect_to(
        resistor1.unnamed[0].get()
    )
    resistor2.unnamed[1].get()._is_interface.get().connect_to(
        resistor1.unnamed[1].get()
    )

    # attach footprint & designator
    for i, r in enumerate([resistor1, resistor2]):
        designator = r.designator_prefix.get().get_prefix() + str(i + 1)
        fabll.Traits.create_and_add_instance_to(r, F.has_designator).setup(designator)
        fabll.Traits.create_and_add_instance_to(
            r, F.can_attach_to_footprint_symmetrically
        ).attach(F.Footprints.Footprint.bind_typegraph(tg).create_instance(g=g))

        fabll.Traits.create_and_add_instance_to(r, F.has_kicad_footprint).setup(
            kicad_identifier="Resistor_SMD:R_0805_2012Metric",  # TODO: get from SMDSize
            pinmap={
                F.Pad.bind_typegraph(tg).create_instance(g=g).setup(): "1",
                F.Pad.bind_typegraph(tg).create_instance(g=g).setup(): "2",
            },
        )

    assert power.hv.get().get_trait(F.has_net_name).name == "+3V3"
    assert power.lv.get().get_trait(F.has_net_name).name == "GND"

    # make netlist
    attach_random_designators(tg)
    attach_net_names(attach_nets(tg))
    attach_kicad_info(tg)
    return make_fbrk_netlist_from_graph(g, tg)


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

    N = kicad.netlist
    return N.NetlistFile(
        netlist=N.Netlist(
            version="E",
            design=None,
            libparts=N.Libparts(libparts=[]),
            libraries=N.Libraries(),
            components=N.Components(
                comps=[
                    N.Component(
                        ref="R1",
                        value="100Ω",
                        footprint="Resistor_SMD:R_0805_2012Metric",
                        tstamps=[str(next(tstamp))],
                        fields=N.Fields(fields=[]),
                        propertys=[],
                        datasheet=None,
                        sheetpath=None,
                        libsource=None,
                    ),
                    N.Component(
                        ref="R2",
                        value="200Ω",
                        footprint="Resistor_SMD:R_0805_2012Metric",
                        tstamps=[str(next(tstamp))],
                        fields=N.Fields(fields=[]),
                        propertys=[],
                        datasheet=None,
                        sheetpath=None,
                        libsource=None,
                    ),
                ]
            ),
            nets=N.Nets(
                nets=[
                    N.Net(
                        code="1",
                        name="+3V3",
                        nodes=[
                            N.Node(
                                ref="R1",
                                pin="1",
                                pintype=None,
                                pinfunction=None,
                            ),
                            N.Node(
                                ref="R2",
                                pin="1",
                                pintype=None,
                                pinfunction=None,
                            ),
                        ],
                    ),
                    N.Net(
                        code="2",
                        name="GND",
                        nodes=[
                            N.Node(
                                ref="R1",
                                pin="2",
                                pintype=None,
                                pinfunction=None,
                            ),
                            N.Node(
                                ref="R2",
                                pin="2",
                                pintype=None,
                                pinfunction=None,
                            ),
                        ],
                    ),
                ]
            ),
        ),
    )


def test_netlist_t2(netlist_t2, netlist_manu):
    netlist_t2 = faebryk_netlist_to_kicad(netlist_t2)
    assert kicad.dumps(netlist_t2) == kicad.dumps(netlist_manu)


def test_netlist_graph(netlist_graph, netlist_t2):
    for comp in netlist_graph.comps:
        assert isinstance(comp.properties, dict)
        comp.properties.pop("atopile_address", None)

    netlist_graph = faebryk_netlist_to_kicad(netlist_graph)
    netlist_t2 = faebryk_netlist_to_kicad(netlist_t2)
    assert kicad.dumps(netlist_graph) == kicad.dumps(netlist_t2)
