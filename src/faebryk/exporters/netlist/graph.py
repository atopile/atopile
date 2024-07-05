# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

import networkx as nx
from faebryk.core.core import (
    LinkDirect,
    Module,
)
from faebryk.core.graph import Graph
from faebryk.core.util import get_all_nodes_graph, get_connected_mifs
from faebryk.exporters.netlist.netlist import Component
from faebryk.library.Electrical import Electrical
from faebryk.library.FootprintTrait import FootprintTrait
from faebryk.library.has_defined_descriptive_properties import (
    has_defined_descriptive_properties,
)
from faebryk.library.has_descriptive_properties import has_descriptive_properties
from faebryk.library.has_footprint import has_footprint
from faebryk.library.has_kicad_footprint import has_kicad_footprint
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.library.has_overriden_name_defined import has_overriden_name_defined
from faebryk.library.has_simple_value_representation import (
    has_simple_value_representation,
)
from faebryk.library.Net import Net
from faebryk.library.Pad import Pad

logger = logging.getLogger(__name__)


class can_represent_kicad_footprint(FootprintTrait):
    kicad_footprint = Component

    @abstractmethod
    def get_name_and_value(self) -> tuple[str, str]: ...

    @abstractmethod
    def get_kicad_obj(self) -> kicad_footprint: ...

    @abstractmethod
    def get_pin_name(self, pin: Pad) -> str: ...


def get_or_set_name_and_value_of_node(c: Module):
    value = (
        c.get_trait(has_simple_value_representation).get_value()
        if c.has_trait(has_simple_value_representation)
        else type(c).__name__
    )

    if not c.has_trait(has_overriden_name):
        c.add_trait(
            has_overriden_name_defined(
                "{}[{}:{}]".format(
                    c.get_full_name(),
                    type(c).__name__,
                    value,
                )
            )
        )

    has_defined_descriptive_properties.add_properties_to(
        c, {"faebryk_name": c.get_full_name()}
    )

    return c.get_trait(has_overriden_name).get_name(), value


class can_represent_kicad_footprint_via_attached_component(
    can_represent_kicad_footprint.impl()
):
    def __init__(self, component: Module, graph: nx.Graph) -> None:
        """
        graph has to be electrically closed
        """

        super().__init__()
        self.component = component
        self.graph = graph

    def get_name_and_value(self):
        return get_or_set_name_and_value_of_node(self.component)

    def get_pin_name(self, pin: Pad):
        return self.get_obj().get_trait(has_kicad_footprint).get_pin_names()[pin]

    def get_kicad_obj(self):
        fp = self.get_obj()

        properties = {
            "footprint": fp.get_trait(has_kicad_footprint).get_kicad_footprint()
        }

        for c in [fp, self.component]:
            if c.has_trait(has_descriptive_properties):
                properties.update(
                    c.get_trait(has_descriptive_properties).get_properties()
                )

        name, value = self.get_name_and_value()

        return can_represent_kicad_footprint.kicad_footprint(
            name=name,
            properties=properties,
            value=value,
        )


def close_electrical_graph(G: nx.Graph):
    G_only_e = nx.Graph()
    G_only_e.add_nodes_from(G.nodes)
    G_only_e.add_edges_from(
        [
            (t0, t1, d)
            for t0, t1, d in G.edges(data=True)
            if isinstance(t0.node, Electrical)
            and isinstance(t1.node, Electrical)
            and t0.node != t1.node
            and t0.node.GIFs.connected == t0
            and t1.node.GIFs.connected == t1
            and isinstance(d.get("link"), LinkDirect)
            # TODO this does not characterize an electrical link very well
        ]
    )
    G_only_e_closed = nx.transitive_closure(G_only_e)
    for t0, t1, d in G_only_e_closed.edges(data=True):
        if "link" in d:
            continue
        d["link"] = LinkDirect([t0, t1])
        # G_only_e_closed.edges(data=True)[t1,t0]["link"] = d["link"]

    Gclosed = nx.Graph(G)
    Gclosed.add_edges_from(G_only_e_closed.edges(data=True))

    return Gclosed


def add_or_get_net(interface: Electrical):
    mifs = get_connected_mifs(interface.GIFs.connected)
    nets = {
        p[0]
        for mif in mifs
        if (p := mif.get_parent()) is not None and isinstance(p[0], Net)
    }
    if not nets:
        net = Net()
        net.IFs.part_of.connect(interface)
        return net
    if len(nets) > 1:
        raise Exception(f"Multiple nets interconnected: {nets}")
    return next(iter(nets))


def attach_nets_and_kicad_info(g: Graph):
    # TODO not sure if needed
    #   as long as core is connecting to all MIFs anyway not needed
    # Gclosed = close_electrical_graph(g.G)
    logger.info(f"Closing graph {g.G}")
    Gclosed = g.G

    # group comps & fps
    node_fps = {
        n: n.get_trait(has_footprint).get_footprint()
        # TODO maybe nicer to just look for footprints
        # and get their respective components instead
        for n in get_all_nodes_graph(Gclosed)
        if n.has_trait(has_footprint) and isinstance(n, Module)
    }

    logger.info(f"Found {len(node_fps)} components with footprints")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"node_fps: {node_fps}")

    # add trait/info to footprints
    for n, fp in node_fps.items():
        if fp.has_trait(can_represent_kicad_footprint):
            continue
        fp.add_trait(can_represent_kicad_footprint_via_attached_component(n, Gclosed))

    for fp in node_fps.values():
        # TODO use graph
        for mif in fp.IFs.get_all():
            if not isinstance(mif, Pad):
                continue
            add_or_get_net(mif.IFs.net)

    g.update()
