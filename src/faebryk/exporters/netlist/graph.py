# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Generator, Iterable

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import NodeNoParent
from faebryk.exporters.netlist.netlist import T2Netlist
from faebryk.libs.library import L
from faebryk.libs.util import FuncDict, KeyErrorAmbiguous, groupby, try_or

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

    return c.get_trait(F.has_overriden_name).get_name(), value


class can_represent_kicad_footprint_via_attached_component(
    can_represent_kicad_footprint.impl()
):
    def __init__(self, component: Module, graph: Graph) -> None:
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

        # FIXME: this should be a part of the Node.get_full_name(),
        # but it's not yet implemented, so we're patching in the same
        # functionality here. See: https://github.com/atopile/atopile/issues/547
        if root_trait := try_or(
            lambda: self.component.get_parent_with_trait(F.is_app_root)
        ):
            root, _ = root_trait
            address = self.component.relative_address(root)
        else:
            address = self.component.get_full_name()
        properties["atopile_address"] = address

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
        raise KeyErrorAmbiguous(list(nets), "Multiple nets interconnected")
    return next(iter(nets))


def attach_nets_and_kicad_info(G: Graph):
    # group comps & fps
    node_fps = {
        n: t.get_footprint()
        # TODO maybe nicer to just look for footprints
        # and get their respective components instead
        for n, t in GraphFunctions(G).nodes_with_trait(F.has_footprint)
        if isinstance(n, Module)
    }

    logger.info(f"Found {len(node_fps)} components with footprints")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"node_fps: {node_fps}")

    # add trait/info to footprints
    for n, fp in node_fps.items():
        if fp.has_trait(can_represent_kicad_footprint):
            continue
        fp.add(can_represent_kicad_footprint_via_attached_component(n, G))

    nets = []
    for fp in node_fps.values():
        for mif in fp.get_children(direct_only=True, types=F.Pad):
            nets.append(add_or_get_net(mif.net))

    generate_net_names(nets)


@dataclass
class _NetName:
    base_name: str | None = None
    prefix: str | None = None
    suffix: int | None = None

    @property
    def name(self) -> str:
        """
        Get the name of the net.
        Net names should take the form of: <prefix>-<base_name>-<suffix>
        There must always be some base, and if it's not provided, it's just 'net'
        Prefixes and suffixes are joined with a "-" if they exist.
        """
        return "-".join(
            str(n) for n in [self.prefix, self.base_name or "net", self.suffix] if n
        )


def _lowest_common_ancestor(nodes: Iterable[L.Node]) -> tuple[L.Node, str] | None:
    """
    Finds the deepest common ancestor of the given nodes.

    Args:
        nodes: Iterable of Node objects to find common ancestor for

    Returns:
        Tuple of (node, name) for the deepest common ancestor,
        or None if no common ancestor exists
    """
    nodes = list(nodes)  # Convert iterable to list to ensure multiple iterations
    if not nodes:
        return None

    # Get hierarchies for all nodes
    hierarchies = [list(n.get_hierarchy()) for n in nodes]
    min_length = min(len(h) for h in hierarchies)

    # Find the last matching ancestor
    last_match = None
    for i in range(min_length):
        ref_node, ref_name = hierarchies[0][i]
        if any(h[i][0] is not ref_node for h in hierarchies[1:]):
            break
        last_match = (ref_node, ref_name)

    return last_match


def _conflicts(names: dict[F.Net, _NetName]) -> Generator[Iterable[F.Net], None, None]:
    for items in groupby(names.items(), lambda it: it[1].name).values():
        if len(items) > 1:
            yield [net for net, _ in items]


def _shit_name(name: str) -> bool:
    if name in {"p1", "p2"}:
        return True

    if "unnamed" in name:
        return True

    return False


def generate_net_names(nets: list[F.Net]) -> None:
    """
    Generate good net names, assuming that we're passed all the nets in a design
    """

    # Ignore nets with names already
    nets = filter(lambda n: not n.has_trait(F.has_overriden_name), nets)

    names = FuncDict[F.Net, _NetName]()

    # First generate candidate base names
    def _decay(depth: int) -> float:
        return 1 / (depth + 1)

    for net in nets:
        name_candidates = defaultdict(float)
        for mif in net.get_connected_interfaces():
            # lower case so we are not case sensitive
            try:
                name = mif.get_name().lower()
            except NodeNoParent:
                # Skip no names
                continue

            if _shit_name(name):
                # Skip ranking shitty names
                continue

            depth = len(mif.get_hierarchy())
            if mif.get_parent_of_type(L.ModuleInterface):
                # Give interfaces on the same level a fighting chance
                depth -= 1

            name_candidates[name] += _decay(depth)

        names[net] = _NetName()
        if name_candidates:
            names[net].base_name = max(name_candidates, key=name_candidates.get)

    # Resolve as many conflict as possible by prefixing on the lowest common node's full name # noqa: E501  # pre-existing
    for conflict_nets in _conflicts(names):
        for net in conflict_nets:
            if lcn := _lowest_common_ancestor(net.get_connected_interfaces()):
                names[net].prefix = lcn[0].get_full_name()

    # Resolve remaining conflicts by suffixing on a number
    for conflict_nets in _conflicts(names):
        for i, net in enumerate(conflict_nets):
            names[net].suffix = i

    # Override the net names we've derived
    for net, name in names.items():
        # Limit name length to 255 chars
        if len(name.name) > 255:
            name_str = name.name[:200] + "..." + name.name[-50:]
        else:
            name_str = name.name
        net.add(F.has_overriden_name_defined(name_str))
