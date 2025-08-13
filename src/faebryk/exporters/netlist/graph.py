# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Generator, Iterable, Mapping

from more_itertools import first

import faebryk.library._F as F
from atopile.errors import UserException
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import NodeNoParent
from faebryk.exporters.netlist.netlist import FBRKNetlist
from faebryk.libs.library import L
from faebryk.libs.util import FuncDict, KeyErrorAmbiguous, groupby

logger = logging.getLogger(__name__)


class can_represent_kicad_footprint(F.Footprint.TraitT.decless()):
    kicad_footprint = FBRKNetlist.Component

    def __init__(self, component: Module, graph: Graph) -> None:
        """
        graph has to be electrically closed
        """

        super().__init__()
        self.component = component
        self.graph = graph

    def get_name_and_value(self):
        return ensure_ref_and_value(self.component)

    def get_pin_name(self, pin: F.Pad):
        return self.obj.get_trait(F.has_kicad_footprint).get_pin_names()[pin]

    def get_kicad_obj(self):
        fp = self.get_obj(F.Footprint)

        properties = {
            "footprint": fp.get_trait(F.has_kicad_footprint).get_kicad_footprint()
        }

        # TODO not sure this is needed, also doing similar stuff elsewhere
        for c in [fp, self.component]:
            if c.has_trait(F.has_descriptive_properties):
                properties.update(
                    c.get_trait(F.has_descriptive_properties).get_properties()
                )

        properties["atopile_address"] = self.component.get_full_name()

        name, value = self.get_name_and_value()

        return can_represent_kicad_footprint.kicad_footprint(
            name=name,
            properties=properties,
            value=value,
        )


def ensure_ref_and_value(c: Module):
    value = (
        c.get_trait(F.has_simple_value_representation).get_value()
        if c.has_trait(F.has_simple_value_representation)
        else type(c).__name__
    )

    # At this point, all components MUST have a designator
    return c.get_trait(F.has_designator).get_designator(), value


def add_or_get_nets(*interfaces: F.Electrical):
    buses = ModuleInterface._group_into_buses(interfaces)
    nets_out = set()

    for bus_repr in buses.keys():
        nets_on_bus = F.Net.find_nets_for_mif(bus_repr)

        if not nets_on_bus:
            net = F.Net()
            net.part_of.connect(bus_repr)
            nets_on_bus = {net}

        if len(nets_on_bus) > 1:
            named_nets_on_bus = {
                n for n in nets_on_bus if n.has_trait(F.has_overriden_name)
            }
            if not named_nets_on_bus:
                nets_on_bus = {first(nets_on_bus)}
            elif len(named_nets_on_bus) == 1:
                nets_on_bus = named_nets_on_bus
            else:
                raise KeyErrorAmbiguous(
                    list(named_nets_on_bus), "Multiple (named) nets interconnected"
                )

        nets_out |= nets_on_bus

    return nets_out


def attach_nets(G: Graph) -> set[F.Net]:
    """Create nets for all the pads in the graph."""
    pad_mifs = [pad.net for pad in GraphFunctions(G).nodes_of_type(F.Pad)]
    nets = add_or_get_nets(*pad_mifs)
    return nets


# FIXME: this belongs at most in the KiCAD netlist generator
# and should likely just return the properties rather than mutating the graph
@dataclass
class _NetName:
    base_name: str | None = None
    prefix: str | None = None
    suffix: int | None = None
    required_prefix: str | None = None
    required_suffix: str | None = None

    @property
    def name(self) -> str:
        """
        Get the name of the net.
        Net names should take the form of: <prefix>-<base_name>-<suffix>
        There must always be some base, and if it's not provided, it's just 'net'
        Prefixes and suffixes are joined with a "-" if they exist.
        """
        base_name = self.base_name or "net"
        prefix = f"{self.prefix}-" if self.prefix else ""
        suffix = f"-{self.suffix}" if self.suffix else ""
        required_prefix = self.required_prefix or ""
        required_suffix = self.required_suffix or ""

        return f"{prefix}{required_prefix}{base_name}{required_suffix}{suffix}"


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

    # "line" is common from signal interfaces, but
    # if there's something else available, prefer that
    if name == "line":
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

    names = FuncDict[F.Net, _NetName]()

    # Ignore nets with names already
    unnamed_nets = {
        n: sorted(n.get_connected_interfaces(), key=lambda m: m.get_full_name())
        for n in nets
        if not n.has_trait(F.has_overriden_name)
    }
    # sort nets by
    # 1. name of first connected interface (remove hex)
    # 2. number of connected interfaces

    def stable_node_name(m: ModuleInterface) -> str:
        return ".".join([p_name for p, p_name in m.get_hierarchy() if p.get_parent()])

    unnamed_nets = dict(
        sorted(
            unnamed_nets.items(),
            key=lambda it: [stable_node_name(m) for m in it[1]],
        )
    )

    # Capture already-named nets for conflict checking
    for net in nets:
        if net.has_trait(F.has_overriden_name):
            names[net] = _NetName(
                base_name=net.get_trait(F.has_overriden_name).get_name()
            )

    # First generate candidate base names
    def _decay(depth: int) -> float:
        return 1 / (depth + 1)

    # FIXME: overriden names will be modified if multiple nets are in conflict
    # FIXME: the errors for this deserve vast improvement. Attaching an origin trait
    # to has_net_name is a start, but we need a generic way to raise those as
    # well-formed errors
    for net, mifs in unnamed_nets.items():
        net_required_names: set[str] = set()
        net_suggested_names: list[tuple[str, int]] = []
        implicit_name_candidates: Mapping[str, float] = defaultdict(float)
        case_insensitive_map: Mapping[str, str] = {}

        for mif in mifs:
            # If there's net info, use it
            depth = len(mif.get_hierarchy())

            if t := mif.try_get_trait(F.has_net_name):
                if t.level == F.has_net_name.Level.EXPECTED:
                    net_required_names.add(t.name)
                elif t.level == F.has_net_name.Level.SUGGESTED:
                    # Weight suggestions by hierarchy: higher up (shallower) wins.
                    # Apply small bonuses for coming from owner iface/module
                    # and for well-known labels.
                    rank = len(mif.get_hierarchy())
                    owner_iface = mif.get_parent_of_type(L.ModuleInterface)
                    if owner_iface is not None and not isinstance(
                        owner_iface, F.Electrical
                    ):
                        rank -= 1
                    if L.Node.nearest_common_ancestor(mif):
                        rank -= 1
                    net_suggested_names.append((t.name, rank))
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

        # Apply required affixes from connected interfaces
        prefixes: list[str] = []
        suffixes: list[str] = []
        for mif in mifs:
            if affix := mif.try_get_trait(F.has_net_name_affix):
                if getattr(affix, "required_prefix", None):
                    prefixes.append(str(affix.required_prefix))
                if getattr(affix, "required_suffix", None):
                    suffixes.append(str(affix.required_suffix))
        if prefixes:
            names[net].required_prefix = prefixes[0]
        if suffixes:
            names[net].required_suffix = suffixes[0]

        # If we have an affix and the base name is generic (e.g. 'line', 'hv'),
        # prefer the interface instance name as the base (e.g. 'iso_spi').
        def _best_iface_name_from_mifs(mifs: Iterable[F.Electrical]) -> str | None:
            candidates: list[tuple[str, int]] = []
            for mif in mifs:
                try:
                    chosen_name: str | None = None
                    chosen_depth: int | None = None
                    for node, name_in_parent in mif.get_hierarchy():
                        if not node.get_parent():
                            continue
                        if isinstance(node, L.ModuleInterface) and not isinstance(
                            node, F.Electrical
                        ):
                            chosen_name = name_in_parent
                            chosen_depth = len(node.get_hierarchy())
                            break
                    if chosen_name is None:
                        continue
                    candidates.append((chosen_name, int(chosen_depth or 0)))
                except NodeNoParent:
                    continue
            if not candidates:
                return None
            return min(candidates, key=lambda x: x[1])[0]

        base = names[net].base_name
        if (names[net].required_suffix or names[net].required_prefix) and (
            base is None
            or base == "line"
            or base == "hv"
            or base.startswith("unnamed")
            or re.match(r"^(_\d+|p\d+)$", base or "")
        ):
            if (iface_name := _best_iface_name_from_mifs(mifs)) is not None:
                names[net].base_name = iface_name

        # Do not apply diff-pair affixes to well-known power rails
        base_lower = (names[net].base_name or "").lower()
        if base_lower in {"gnd", "vcc", "vdd", "vss"}:
            names[net].required_prefix = None
            names[net].required_suffix = None

    # Resolve conflicts by prefixing with the owning interface's instance name first
    def _best_interface_prefix(net: F.Net) -> str | None:
        """Pick a good interface instance name to disambiguate a net.

        Prefer the nearest ancestor that is a ModuleInterface but not an
        Electrical (i.e. the interface instance like `power_3v3`), to avoid
        using leaf names like `vcc`/`gnd`.
        """
        candidates: list[tuple[str, int]] = []
        for mif in net.get_connected_interfaces():
            try:
                # Traverse hierarchy from root to leaf and pick the first
                # non-Electrical ModuleInterface name
                chosen_name: str | None = None
                chosen_depth: int | None = None
                for node, name_in_parent in mif.get_hierarchy():
                    if not node.get_parent():
                        continue
                    if isinstance(node, L.ModuleInterface) and not isinstance(
                        node, F.Electrical
                    ):
                        chosen_name = name_in_parent
                        chosen_depth = len(node.get_hierarchy())
                        break
                if chosen_name is None:
                    continue
                candidates.append((chosen_name, int(chosen_depth or 0)))
            except NodeNoParent:
                continue

        if not candidates:
            return None
        # Prefer smallest depth (closest to root)
        return min(candidates, key=lambda x: x[1])[0]

    for conflict_nets in _conflicts(names):
        # Prefer to add interface-based prefixes to ALL nets in the group and
        # make them unique by minimally qualifying with ancestor names
        def _interface_name_path_for_net(net: F.Net) -> list[str] | None:
            """Pick the best interface path for prefixing a net.

            Prefer ElectricPower interface instance names and include the nearest
            owning module name to minimally qualify when needed, e.g.:
            - power_5v
            - sensor-power_5v
            Avoid generic names like 'pins' or 'unnamed'.
            """
            best: tuple[int, list[str]] | None = None
            for mif in net.get_connected_interfaces():
                try:
                    hierarchy = [
                        (node, name)
                        for node, name in mif.get_hierarchy()
                        if node.get_parent()
                    ]
                    # Find first non-Electrical ModuleInterface in chain
                    anchor_idx = None
                    for idx, (node, name) in enumerate(hierarchy):
                        if isinstance(node, L.ModuleInterface) and not isinstance(
                            node, F.Electrical
                        ):
                            anchor_idx = idx
                            break
                    if anchor_idx is None:
                        continue

                    anchor_node, anchor_name = hierarchy[anchor_idx]
                    # Find nearest owning Module before the anchor
                    owner_name = None
                    for j in range(anchor_idx - 1, -1, -1):
                        node_j, name_j = hierarchy[j]
                        if isinstance(node_j, Module):
                            owner_name = name_j
                            break

                    # Compose path
                    path: list[str] = (
                        [owner_name, anchor_name] if owner_name else [anchor_name]
                    )

                    # Score candidates
                    score = 0
                    if isinstance(anchor_node, F.ElectricPower):
                        score += 2
                    if owner_name:
                        score += 1
                    if anchor_name.startswith("pins") or anchor_name.startswith(
                        "unnamed"
                    ):
                        score -= 2

                    cand = (score, path)
                    if best is None or cand > best:
                        best = cand

                except NodeNoParent:
                    continue

            return None if best is None else best[1]

        paths: dict[F.Net, list[str] | None] = {
            net: _interface_name_path_for_net(net) for net in conflict_nets
        }

        if any(p for p in paths.values()):
            # Compute minimal unique suffix per path
            suffix_len: dict[F.Net, int] = {
                net: 1 for net in conflict_nets if paths[net]
            }

            def _keys() -> dict[F.Net, tuple[str, ...]]:
                keys: dict[F.Net, tuple[str, ...]] = {}
                for net in conflict_nets:
                    p = paths[net]
                    if not p:
                        continue
                    keys[net] = tuple(p[-suffix_len[net] :])
                return keys

            keys = _keys()
            # Increase suffix length for colliding keys until unique or max depth
            progressed = True
            while progressed:
                progressed = False
                # group by key
                groups: dict[tuple[str, ...], list[F.Net]] = {}
                for net, key in keys.items():
                    groups.setdefault(key, []).append(net)
                for key, nets_in_key in groups.items():
                    if len(nets_in_key) <= 1:
                        continue
                    for net in nets_in_key:
                        p = paths[net]
                        if not p:
                            continue
                        if suffix_len[net] < len(p):
                            suffix_len[net] += 1
                            progressed = True
                if progressed:
                    keys = _keys()

            # Assign per-net prefixes
            for net in conflict_nets:
                p = paths[net]
                if p:
                    # If the chosen path is too generic (e.g., starts with 'pins' or
                    # 'unnamed') and there are no required affixes influencing
                    # semantics, prefer owner name
                    leaf = p[-1] if p else None
                    if (
                        leaf
                        and (leaf.startswith("pins") or leaf.startswith("unnamed"))
                        and not names[net].required_prefix
                        and not names[net].required_suffix
                    ):
                        owner_mod_name: str | None = None
                        for mif in net.get_connected_interfaces():
                            try:
                                for node, name_in_parent in mif.get_hierarchy():
                                    if not node.get_parent():
                                        continue
                                    if isinstance(node, Module):
                                        owner_mod_name = name_in_parent
                                        break
                                if owner_mod_name:
                                    break
                            except NodeNoParent:
                                continue
                        if owner_mod_name:
                            names[net].prefix = owner_mod_name
                        else:
                            names[net].prefix = "-".join(p[-suffix_len[net] :])
                    else:
                        names[net].prefix = "-".join(p[-suffix_len[net] :])
                else:
                    # Fallback to owning module instance name if available
                    owner_name: str | None = None
                    for mif in net.get_connected_interfaces():
                        try:
                            for node, name_in_parent in mif.get_hierarchy():
                                if not node.get_parent():
                                    continue
                                if isinstance(node, Module):
                                    owner_name = name_in_parent
                                    break
                            if owner_name:
                                break
                        except NodeNoParent:
                            continue
                    if owner_name:
                        names[net].prefix = owner_name
                    else:
                        if lcn := L.Node.nearest_common_ancestor(
                            *net.get_connected_interfaces()
                        ):
                            names[net].prefix = lcn[0].get_full_name()

    # Resolve remaining conflicts by prefixing on
    # the lowest common node's full name
    for conflict_nets in _conflicts(names):
        for net in conflict_nets:
            if names[net].prefix is None:
                if lcn := L.Node.nearest_common_ancestor(
                    *net.get_connected_interfaces()
                ):
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
