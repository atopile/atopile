# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

import networkx as nx

import faebryk.library._F as F
from faebryk.core.graphinterface import Graph
from faebryk.core.module import Module
from faebryk.exporters.netlist.netlist import T2Netlist

logger = logging.getLogger(__name__)


class can_represent_kicad_footprint(F.Footprint.TraitT):
    kicad_footprint = T2Netlist.Component

    @abstractmethod
    def get_name_and_value(self) -> tuple[str, str]: ...

    @abstractmethod
    def get_kicad_obj(self) -> kicad_footprint: ...

    @abstractmethod
    def get_pin_name(self, pin: F.Pad) -> str: ...


def get_or_set_name_and_value_of_node(c: Module):
    value = (
        c.get_trait(F.has_simple_value_representation).get_value()
        if c.has_trait(F.has_simple_value_representation)
        else type(c).__name__
    )

    if not c.has_trait(F.has_overriden_name):
        c.add(
            F.has_overriden_name_defined(
                "{}[{}:{}]".format(
                    c.get_full_name(),
                    type(c).__name__,
                    value,
                )
            )
        )

    c.add(F.has_descriptive_properties_defined({"faebryk_name": c.get_full_name()}))

    return c.get_trait(F.has_overriden_name).get_name(), value


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

    def get_pin_name(self, pin: F.Pad):
        return self.obj.get_trait(F.has_kicad_footprint).get_pin_names()[pin]

    def get_kicad_obj(self):
        fp = self.get_obj(F.Footprint)

        properties = {
            "footprint": fp.get_trait(F.has_kicad_footprint).get_kicad_footprint()
        }

        for c in [fp, self.component]:
            if c.has_trait(F.has_descriptive_properties):
                properties.update(
                    c.get_trait(F.has_descriptive_properties).get_properties()
                )

        name, value = self.get_name_and_value()

        return can_represent_kicad_footprint.kicad_footprint(
            name=name,
            properties=properties,
            value=value,
        )


def add_or_get_net(interface: F.Electrical):
    nets = {
        p[0]
        for mif in interface.get_connected()
        if (p := mif.get_parent()) is not None and isinstance(p[0], F.Net)
    }
    if not nets:
        net = F.Net()
        net.part_of.connect(interface)
        return net
    if len(nets) > 1:
        raise Exception(f"Multiple nets interconnected: {nets}")
    return next(iter(nets))


def attach_nets_and_kicad_info(g: Graph):
    # g has to be closed

    Gclosed = g

    # group comps & fps
    node_fps = {
        n: t.get_footprint()
        # TODO maybe nicer to just look for footprints
        # and get their respective components instead
        for n, t in Gclosed.nodes_with_trait(F.has_footprint)
        if isinstance(n, Module)
    }

    logger.info(f"Found {len(node_fps)} components with footprints")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"node_fps: {node_fps}")

    # add trait/info to footprints
    for n, fp in node_fps.items():
        if fp.has_trait(can_represent_kicad_footprint):
            continue
        fp.add(can_represent_kicad_footprint_via_attached_component(n, Gclosed))

    for fp in node_fps.values():
        # TODO use graph
        for mif in fp.get_children(direct_only=True, types=F.Pad):
            add_or_get_net(mif.net)
