# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from abc import abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Generator, Iterable, Mapping

import faebryk.library._F as F
from atopile.errors import UserException
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import NodeNoParent
from faebryk.exporters.netlist.netlist import FBRKNetlist
from faebryk.libs.library import L
from faebryk.libs.util import FuncDict, KeyErrorAmbiguous, groupby, try_or

logger = logging.getLogger(__name__)


class can_represent_kicad_footprint(F.Footprint.TraitT):
    kicad_footprint = FBRKNetlist.Component

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


def add_or_get_nets(*interfaces: F.Electrical):
    buses = ModuleInterface._group_into_buses(interfaces)
    nets_out = set()

    for bus_repr, connected_mifs in buses.items():
        nets_on_bus = {
            net
            for mif in connected_mifs
            if (net := F.Net.from_part_of_mif(mif)) is not None
        }
        if not nets_on_bus:
            net = F.Net()
            net.part_of.connect(bus_repr)
            nets_on_bus = {net}
        if len(nets_on_bus) > 1:
            raise KeyErrorAmbiguous(list(nets_on_bus), "Multiple nets interconnected")

        nets_out |= nets_on_bus

    return nets_out


def attach_nets_and_kicad_info(G: Graph) -> set[F.Net]:
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

    mifs = [
        mif.net
        for fp in node_fps.values()
        for mif in fp.get_children(direct_only=True, types=F.Pad)
    ]
    nets = add_or_get_nets(*mifs)

    return nets


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


def _conflicts(
    names: Mapping[F.Net, _NetName],
) -> Generator[Iterable[F.Net], None, None]:
    for items in groupby(names.items(), lambda it: it[1].name).values():
        if len(items) > 1:
            yield [net for net, _ in items]


def _name_shittiness(name: str | None) -> float:
    """Caesar says 👎"""

    # These are completely shit names that
    # have no business existing
    if name is None:
        return 0

    if name == "net":
        # By the time we're here, we have a bunch
        # of pads with the name net attached
        return 0

    if name == "":
        return 0

    if name.startswith("unnamed"):
        return 0

    if re.match(r"^(_\d+|p\d+)$", name):
        return 0

    # Here are some shitty patterns, that are
    # fine as a backup, but should be avoided

    # Anything that starts with an underscore
    # is probably a temporary name
    if name.startswith("_"):
        return 0.2

    # "hv" is common from power interfaces, but
    # if there's something else available, prefer that
    if name == "hv":
        return 0.3

    # Anything with a trailing number is
    # generally less interesting
    if re.match(r".*\d+$", name):
        return 0.5

    return 1


def attach_net_names(nets: Iterable[F.Net]) -> None:
    """
    Generate good net names, assuming that we're passed all the nets in a design
    """

    # Ignore nets with names already
    unnamed_nets = [n for n in nets if not n.has_trait(F.has_overriden_name)]

    names = FuncDict[F.Net, _NetName]()

    # First generate candidate base names
    def _decay(depth: int) -> float:
        return 1 / (depth + 1)

    # FIXME: overriden names will be modified if multiple nets are in conflict
    # FIXME: the errors for this deserve vast improvement. Attaching an origin trait
    # to has_net_name is a start, but we need a generic way to raise those as
    # well-formed errors
    for net in unnamed_nets:
        net_required_names: set[str] = set()
        net_suggested_names: list[tuple[str, int]] = []
        implicit_name_candidates: Mapping[str, float] = defaultdict(float)
        case_insensitive_map: Mapping[str, str] = {}

        for mif in net.get_connected_interfaces():
            # If there's net info, use it
            depth = len(mif.get_hierarchy())

            if t := mif.try_get_trait(F.has_net_name):
                if t.level == F.has_net_name.Level.EXPECTED:
                    net_required_names.add(t.name)
                elif t.level == F.has_net_name.Level.SUGGESTED:
                    net_suggested_names.append((t.name, len(mif.get_hierarchy())))
                continue

            # Rate implicit names
            # lower case so we are not case sensitive
            try:
                name = mif.get_name()
            except NodeNoParent:
                # Skip no names
                continue

            lower_name = name.lower()
            case_insensitive_map[lower_name] = name

            if mif.get_parent_of_type(L.ModuleInterface):
                # Give interfaces on the same level a fighting chance
                depth -= 1

            implicit_name_candidates[case_insensitive_map[lower_name]] += _decay(
                depth
            ) * _name_shittiness(lower_name)

        # Check required names
        if net_required_names:
            if len(set(net_required_names)) > 1:
                raise UserException(
                    f"Multiple conflicting required net names: {net_required_names}"
                )
            net.add(F.has_overriden_name_defined(net_required_names.pop()))
            continue

        # Initialize the net name for the remaining processing
        names[net] = _NetName()

        if net_suggested_names:
            names[net].base_name = min(net_suggested_names, key=lambda x: x[1])[0]

        elif implicit_name_candidates:
            # Type ignored on this because they typing on both max and defaultdict.get
            # is poor. This is actually correct, and supposed to return None sometimes
            names[net].base_name = max(
                implicit_name_candidates,
                key=implicit_name_candidates.get,  # type: ignore
            )

    # Resolve as many conflict as possible by prefixing on
    # the lowest common node's full name
    for conflict_nets in _conflicts(names):
        for net in conflict_nets:
            if lcn := L.Node.nearest_common_ancestor(*net.get_connected_interfaces()):
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

    assert all(n.has_trait(F.has_overriden_name) for n in nets)
