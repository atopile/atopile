# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

import networkx as nx
from faebryk.core.core import (
    Footprint,
    FootprintTrait,
    GraphInterfaceSelf,
    LinkDirect,
    Node,
)
from faebryk.core.graph import Graph
from faebryk.library.Electrical import Electrical
from faebryk.library.has_descriptive_properties import has_descriptive_properties
from faebryk.library.has_footprint import has_footprint
from faebryk.library.has_kicad_footprint import has_kicad_footprint
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.library.has_overriden_name_defined import has_overriden_name_defined
from faebryk.library.has_type_description import has_type_description

logger = logging.getLogger(__name__)


class can_represent_kicad_footprint(FootprintTrait):
    @dataclass
    class kicad_footprint:
        @dataclass
        class neighbor:
            fp: Footprint
            pin: str

        name: str
        properties: dict[str, Any]
        neighbors: dict[str, list[neighbor]]
        value: str

    @abstractmethod
    def get_name_and_value(self) -> tuple[str, str]:
        ...

    @abstractmethod
    def get_kicad_obj(self) -> kicad_footprint:
        ...


def get_or_set_name_and_value_of_node(c: Node):
    # TODO rename that trait
    value = c.get_trait(has_type_description).get_type_description()

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

    return c.get_trait(has_overriden_name).get_name(), value


class can_represent_kicad_footprint_via_attached_component(
    can_represent_kicad_footprint.impl()
):
    def __init__(self, component: Node, graph: nx.Graph) -> None:
        """
        graph has to be electrically closed
        """

        super().__init__()
        self.component = component
        self.graph = graph

    def get_name_and_value(self):
        return get_or_set_name_and_value_of_node(self.component)

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

        pin_names = fp.get_trait(has_kicad_footprint).get_pin_names()

        neighbors = {
            pin_names[pin]: [
                can_represent_kicad_footprint.kicad_footprint.neighbor(
                    fp=target_fp,
                    pin=target_fp.get_trait(has_kicad_footprint).get_pin_names()[
                        i.node
                    ],
                )
                for i in self.graph[pin.GIFs.connected]
                if i.node is not pin
                and isinstance(i.node, Electrical)
                and (fp_tup := i.node.get_parent()) is not None
                and isinstance((target_fp := fp_tup[0]), Footprint)
            ]
            for pin in fp.IFs.get_all()
            if isinstance(pin, Electrical)
        }

        return can_represent_kicad_footprint.kicad_footprint(
            name=name,
            properties=properties,
            neighbors=neighbors,
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


def make_t1_netlist_from_graph(g: Graph):
    # TODO not sure if needed
    #   as long as core is connecting to all MIFs anyway not needed
    # Gclosed = close_electrical_graph(g.G)
    logger.info(f"Closing graph {g.G}")
    Gclosed = g.G

    # group comps & fps
    node_fps = {
        n: n.get_trait(has_footprint).get_footprint()
        for GIF in Gclosed.nodes
        # TODO maybe nicer to just look for footprints
        # and get their respective components instead
        if isinstance(GIF, GraphInterfaceSelf)
        and (n := GIF.node) is not None
        and n.has_trait(has_footprint)
    }

    logger.info(f"Found {len(node_fps)} components with footprints")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"node_fps: {node_fps}")

    # add trait/info to footprints
    for n, fp in node_fps.items():
        fp = n.get_trait(has_footprint).get_footprint()
        if fp.has_trait(can_represent_kicad_footprint):
            continue
        fp.add_trait(can_represent_kicad_footprint_via_attached_component(n, Gclosed))

    # generate kicad_objs from footprints
    logger.info("Generating kicad objects")
    kicad_objs = {
        fp: fp.get_trait(can_represent_kicad_footprint).get_kicad_obj()
        for fp in node_fps.values()
    }

    def convert_kicad_obj_base(
        obj: can_represent_kicad_footprint.kicad_footprint,
    ) -> dict[str, Any]:
        return {
            "name": obj.name,
            "properties": obj.properties,
            "value": obj.value,
            "real": True,
            "neighbors": obj.neighbors,
        }

    # convert into old/generic format
    logger.info("Converting kicad objects")
    converted = {fp: convert_kicad_obj_base(obj) for fp, obj in kicad_objs.items()}

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"stage_1: {converted}")

    def convert_kicad_obj_neighbors(obj: dict[str, Any]):
        obj["neighbors"] = {
            k: [{"vertex": converted[n.fp], "pin": n.pin} for n in v]
            for k, v in obj["neighbors"].items()
        }

    for fp, obj in converted.items():
        convert_kicad_obj_neighbors(obj)

    return list(converted.values())
