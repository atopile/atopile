# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
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
from faebryk.libs.util import FuncDict, KeyErrorAmbiguous, groupby, once

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

    # Iterate buses in a deterministic order by their string representation
    for bus_repr in sorted(buses.keys(), key=lambda b: str(b)):
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
                # Deterministically select a representative net by stable key
                nets_on_bus = {min(nets_on_bus, key=_get_net_stable_key)}
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
    # Sort pad interfaces by stable node name to ensure deterministic bus grouping
    pad_mifs = sorted(pad_mifs, key=_get_stable_node_name)
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
        numeric_suffix = f"-{self.suffix}" if self.suffix is not None else ""
        required_prefix = self.required_prefix or ""
        required_suffix = self.required_suffix or ""

        # Order: prefix + required_prefix + base + numeric_suffix + required_suffix
        # Ensures diff-pair affix (_P/_N) is last, e.g. "line-1_N"
        return f"{prefix}{required_prefix}{base_name}{numeric_suffix}{required_suffix}"


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


@once
def _get_stable_node_name(mif: ModuleInterface) -> str:
    """Get a stable hierarchical name for a module interface."""
    return ".".join([p_name for p, p_name in mif.get_hierarchy() if p.get_parent()])


def _get_net_stable_key(net: F.Net) -> tuple[str, ...]:
    """Return a deterministic key for a net based on connected interface paths.

    Using the sorted list of stable module-interface paths ensures that
    operations that depend on iteration order (e.g. suffix assignment)
    are repeatable across runs for the same design.
    """
    try:
        mifs = net.get_connected_interfaces()
    except Exception:
        # In case a backend returns a generator that raises mid-iteration,
        # fall back to an empty key which still sorts deterministically.
        return tuple()

    stable_names = sorted(_get_stable_node_name(m) for m in mifs)
    return tuple(stable_names)


def _collect_unnamed_nets(nets: Iterable[F.Net]) -> dict[F.Net, list[F.Electrical]]:
    """Collect nets without overridden names and their connected interfaces."""
    unnamed_nets = {
        n: sorted(n.get_connected_interfaces(), key=lambda m: m.get_full_name())
        for n in nets
        if not n.has_trait(F.has_overriden_name)
    }

    # Sort nets by stable node names for deterministic ordering
    return dict(
        sorted(
            unnamed_nets.items(),
            key=lambda it: [_get_stable_node_name(m) for m in it[1]],
        )
    )


def _register_named_nets(
    nets: Iterable[F.Net], names: FuncDict[F.Net, _NetName]
) -> None:
    """Register nets that already have overridden names."""
    for net in nets:
        if net.has_trait(F.has_overriden_name):
            names[net] = _NetName(
                base_name=net.get_trait(F.has_overriden_name).get_name()
            )


def _calculate_suggested_name_rank(mif: ModuleInterface, base_depth: int) -> int:
    """Calculate rank for a suggested name based on hierarchy."""
    rank = base_depth

    owner_iface = mif.get_parent_of_type(L.ModuleInterface)
    if owner_iface and not isinstance(owner_iface, F.Electrical):
        rank -= 1

    if L.Node.nearest_common_ancestor(mif):
        rank -= 1

    return rank


def _extract_net_name_info(
    mif: ModuleInterface,
) -> tuple[set[str], list[tuple[str, int]], dict[str, float]]:
    """Extract naming information from an interface."""
    required_names: set[str] = set()
    suggested_names: list[tuple[str, int]] = []
    implicit_candidates: dict[str, float] = {}

    depth = len(mif.get_hierarchy())

    # Handle explicit net naming traits on this interface
    if trait := mif.try_get_trait(F.has_net_name):
        if trait.level == F.has_net_name.Level.EXPECTED:
            required_names.add(trait.name)
        elif trait.level == F.has_net_name.Level.SUGGESTED:
            rank = _calculate_suggested_name_rank(mif, depth)
            suggested_names.append((trait.name, rank))

    # Also consider traits on ancestor interfaces in the hierarchy
    try:
        for node, _name_in_parent in mif.get_hierarchy():
            if not node.get_parent():
                continue
            if not isinstance(node, L.ModuleInterface):
                continue
            if not node.has_trait(F.has_net_name):
                continue
            trait = node.get_trait(F.has_net_name)
            node_depth = len(node.get_hierarchy())
            if trait.level == F.has_net_name.Level.EXPECTED:
                required_names.add(trait.name)
            elif trait.level == F.has_net_name.Level.SUGGESTED:
                rank = _calculate_suggested_name_rank(mif, node_depth)
                suggested_names.append((trait.name, rank))
    except NodeNoParent:
        pass

    # Handle implicit names
    try:
        name = mif.get_name()
    except NodeNoParent:
        return required_names, suggested_names, implicit_candidates

    # Adjust depth for interfaces on the same level
    if mif.get_parent_of_type(L.ModuleInterface):
        depth -= 1

    # Calculate implicit name score
    score = (1 / (depth + 1)) * _name_shittiness(name.lower())
    implicit_candidates[name] = score

    return required_names, suggested_names, implicit_candidates


def _collect_naming_info_from_interfaces(
    mifs: list[F.Electrical],
) -> tuple[set[str], list[tuple[str, int]], dict[str, float]]:
    """Aggregate naming information from multiple interfaces."""
    all_required: set[str] = set()
    all_suggested: list[tuple[str, int]] = []
    all_implicit: dict[str, float] = defaultdict(float)

    for mif in mifs:
        required, suggested, implicit = _extract_net_name_info(mif)
        all_required.update(required)
        all_suggested.extend(suggested)
        for name, score in implicit.items():
            all_implicit[name] += score

    return all_required, all_suggested, all_implicit


def _determine_base_name(
    suggested: list[tuple[str, int]], implicit: dict[str, float]
) -> str | None:
    """Determine the best base name from suggested and implicit candidates."""
    if suggested:
        # Use the suggestion with the lowest rank (highest priority),
        # break ties by lexicographically smallest name for determinism
        return min(suggested, key=lambda x: (x[1], x[0]))[0]

    if implicit:
        # Use the implicit name with the highest score; break ties by name
        best_score = max(implicit.values())
        candidates = [name for name, score in implicit.items() if score == best_score]
        return min(candidates)

    return None


def _process_unnamed_nets(
    unnamed_nets: dict[F.Net, list[F.Electrical]], names: FuncDict[F.Net, _NetName]
) -> None:
    """Process nets without names, determining their base names."""
    for net, mifs in unnamed_nets.items():
        # Collect all naming information
        required, suggested, implicit = _collect_naming_info_from_interfaces(mifs)

        # Handle required names (highest priority)
        if required:
            if len(required) > 1:
                raise UserException(
                    f"Multiple conflicting required net names: {required}"
                )
            net.add(F.has_overriden_name_defined(required.pop()))
            continue

        # Create net name entry and determine base name
        names[net] = _NetName()
        names[net].base_name = _determine_base_name(suggested, implicit)


def _is_generic_name(name: str | None) -> bool:
    """Check if a name is generic and should be replaced."""
    if name is None:
        return True

    generic_names = {"line", "hv", "p", "n"}
    generic_patterns = [
        lambda n: n.startswith("unnamed"),
        lambda n: re.match(r"^(_\d+|p\d+)$", n) is not None,
    ]

    return name in generic_names or any(pattern(name) for pattern in generic_patterns)


def _is_power_rail_name(name: str | None) -> bool:
    """Check if a name is a well-known power rail."""
    if name is None:
        return False
    return name.lower() in {"gnd", "vcc", "vdd", "vss"}


def _extract_interface_candidate(mif: F.Electrical) -> tuple[str, int] | None:
    """Extract a naming candidate from a single interface."""
    try:
        for node, name_in_parent in mif.get_hierarchy():
            if not node.get_parent():
                continue

            is_interface = isinstance(node, L.ModuleInterface)
            is_not_electrical = not isinstance(node, F.Electrical)

            if is_interface and is_not_electrical:
                return (name_in_parent, len(node.get_hierarchy()))
    except NodeNoParent:
        pass

    return None


def _find_best_interface_name(mifs: Iterable[F.Electrical]) -> str | None:
    """Find the best interface name from connected interfaces."""
    candidates = [
        candidate
        for mif in mifs
        if (candidate := _extract_interface_candidate(mif)) is not None
    ]

    if not candidates:
        return None

    # Return the name with the smallest depth (highest in hierarchy),
    # and lexicographically smallest name as deterministic tie-breaker
    return min(candidates, key=lambda x: (x[1], x[0]))[0]


def _collect_affixes(mifs: list[F.Electrical]) -> tuple[str | None, str | None]:
    """Collect prefix and suffix from interfaces."""
    prefixes: list[str] = []
    suffixes: list[str] = []

    for mif in mifs:
        affix = mif.try_get_trait(F.has_net_name_affix)
        if not affix:
            continue

        if prefix := getattr(affix, "required_prefix", None):
            prefixes.append(str(prefix))
        if suffix := getattr(affix, "required_suffix", None):
            suffixes.append(str(suffix))

    # Return first prefix and suffix found
    return prefixes[0] if prefixes else None, suffixes[0] if suffixes else None


def _should_replace_generic_name(net_name: _NetName) -> bool:
    """Check if a generic base name should be replaced."""
    has_affixes = bool(net_name.required_suffix or net_name.required_prefix)
    return _is_generic_name(net_name.base_name) and has_affixes


def _apply_affixes(
    unnamed_nets: dict[F.Net, list[F.Electrical]], names: FuncDict[F.Net, _NetName]
) -> None:
    """Apply prefixes and suffixes from net name affixes."""
    for net, mifs in unnamed_nets.items():
        if net not in names:
            continue

        net_name = names[net]

        # Apply affixes
        prefix, suffix = _collect_affixes(mifs)
        net_name.required_prefix = prefix
        net_name.required_suffix = suffix

        # Replace generic names when affixes are present
        if _should_replace_generic_name(net_name):
            if better_name := _find_best_interface_name(mifs):
                net_name.base_name = better_name

        # Protect power rails from affixes
        if _is_power_rail_name(net_name.base_name):
            net_name.required_prefix = None
            net_name.required_suffix = None


def _find_anchor_interface(hierarchy: list[tuple]) -> tuple[int, tuple] | None:
    """Find the first non-Electrical ModuleInterface in hierarchy."""
    for idx, (node, name) in enumerate(hierarchy):
        is_interface = isinstance(node, L.ModuleInterface)
        is_not_electrical = not isinstance(node, F.Electrical)

        if is_interface and is_not_electrical:
            return idx, (node, name)

    return None


def _find_owner_module(hierarchy: list[tuple], before_idx: int) -> str | None:
    """Find the nearest owning Module before the given index."""
    for j in range(before_idx - 1, -1, -1):
        node, name = hierarchy[j]
        if isinstance(node, Module):
            return name
    return None


def _score_interface_path(anchor_node, anchor_name: str, has_owner: bool) -> int:
    """Calculate score for an interface path."""
    score = 0

    if isinstance(anchor_node, F.ElectricPower):
        score += 2

    if has_owner:
        score += 1

    if anchor_name.startswith("pins") or anchor_name.startswith("unnamed"):
        score -= 2

    return score


def _process_single_interface(mif: F.Electrical) -> tuple[int, list[str]] | None:
    """Process a single interface to get its path and score."""
    try:
        hierarchy = [
            (node, name) for node, name in mif.get_hierarchy() if node.get_parent()
        ]

        # Find anchor interface
        anchor_result = _find_anchor_interface(hierarchy)
        if not anchor_result:
            return None

        anchor_idx, (anchor_node, anchor_name) = anchor_result

        # Find owner module
        owner_name = _find_owner_module(hierarchy, anchor_idx)

        # Build path
        path = [owner_name, anchor_name] if owner_name else [anchor_name]

        # Calculate score
        score = _score_interface_path(anchor_node, anchor_name, bool(owner_name))

        return score, path

    except NodeNoParent:
        return None


def _get_interface_path_for_net(net: F.Net) -> list[str] | None:
    """Get the best interface path for prefixing a net."""
    candidates = [
        result
        for mif in net.get_connected_interfaces()
        if (result := _process_single_interface(mif)) is not None
    ]

    if not candidates:
        return None

    # Return the path with the highest score; break ties deterministically by
    # preferring shorter paths and then lexicographical order
    _, best_path = max(candidates, key=lambda x: (x[0], -len(x[1]), tuple(x[1])))
    return best_path


def _get_owner_module_name(net: F.Net) -> str | None:
    """Get the name of the owning module for a net."""
    owner_names: set[str] = set()
    for mif in net.get_connected_interfaces():
        try:
            hierarchy = mif.get_hierarchy()
            for node, name_in_parent in hierarchy:
                if node.get_parent() and isinstance(node, Module):
                    owner_names.add(name_in_parent)
        except NodeNoParent:
            continue
    if not owner_names:
        return None
    # Choose a deterministic owner module name
    return min(owner_names)


def _compute_minimal_unique_prefixes(
    paths: dict[F.Net, list[str] | None], conflict_nets: list[F.Net]
) -> dict[F.Net, int]:
    """Compute minimal suffix lengths to make paths unique."""
    suffix_len: dict[F.Net, int] = {net: 1 for net in conflict_nets if paths[net]}

    def get_keys() -> dict[F.Net, tuple[str, ...]]:
        return {net: tuple(p[-suffix_len[net] :]) for net, p in paths.items() if p}

    keys = get_keys()

    # Increase suffix length until all keys are unique
    while True:
        # Group nets by their current key
        groups: dict[tuple[str, ...], list[F.Net]] = {}
        for net, key in keys.items():
            groups.setdefault(key, []).append(net)

        # Check if any groups have conflicts
        has_conflict = False
        for key, nets_in_key in groups.items():
            if len(nets_in_key) <= 1:
                continue

            # Increase suffix length for conflicting nets
            for net in nets_in_key:
                p = paths[net]
                if p and suffix_len[net] < len(p):
                    suffix_len[net] += 1
                    has_conflict = True

        if not has_conflict:
            break

        keys = get_keys()

    return suffix_len


def _is_generic_path_leaf(path: list[str] | None) -> bool:
    """Check if the leaf of a path is generic."""
    if not path:
        return False

    leaf = path[-1]
    return leaf.startswith("pins") or leaf.startswith("unnamed")


def _get_fallback_prefix(net: F.Net) -> str | None:
    """Get a fallback prefix for a net without a path."""
    # Try owner module name
    if owner_name := _get_owner_module_name(net):
        return owner_name

    # Try best interface name across connected interfaces
    interfaces = net.get_connected_interfaces()
    if best := _find_best_interface_name(interfaces):
        return best

    # Try lowest common ancestor
    if lcn := L.Node.nearest_common_ancestor(*interfaces):
        return lcn[0].get_full_name()

    return None


def _assign_prefix_for_net(
    net: F.Net,
    path: list[str] | None,
    suffix_len: dict[F.Net, int],
    names: FuncDict[F.Net, _NetName],
) -> None:
    """Assign a prefix to a single net."""
    net_name = names[net]

    if not path:
        # No path available, use fallback
        net_name.prefix = _get_fallback_prefix(net)
        return

    # Check if we should use owner name instead of generic path
    should_use_owner = (
        _is_generic_path_leaf(path)
        and not net_name.required_prefix
        and not net_name.required_suffix
    )

    if should_use_owner:
        if owner_name := _get_owner_module_name(net):
            net_name.prefix = owner_name
            return

    # Use the computed suffix from the path
    net_name.prefix = "-".join(path[-suffix_len[net] :])


def _resolve_conflicts_with_prefixes(names: FuncDict[F.Net, _NetName]) -> None:
    """Resolve naming conflicts by adding interface-based prefixes."""
    for conflict_nets in _conflicts(names):
        # Sort nets deterministically within the conflict group
        ordered_conflict_nets = sorted(conflict_nets, key=_get_net_stable_key)

        # Get interface paths for all conflicting nets
        paths = {net: _get_interface_path_for_net(net) for net in ordered_conflict_nets}

        # Skip if no paths available
        if not any(paths.values()):
            continue

        # Compute minimal unique prefixes
        suffix_len = _compute_minimal_unique_prefixes(
            paths, list(ordered_conflict_nets)
        )

        # Assign prefixes to each net
        for net in ordered_conflict_nets:
            _assign_prefix_for_net(net, paths[net], suffix_len, names)


def _resolve_conflicts_with_lca(names: FuncDict[F.Net, _NetName]) -> None:
    """Resolve remaining conflicts using lowest common ancestor."""
    for conflict_nets in _conflicts(names):
        for net in conflict_nets:
            # Skip if already has a prefix
            if names[net].prefix is not None:
                continue

            # Try to use lowest common ancestor
            interfaces = net.get_connected_interfaces()
            lcn = L.Node.nearest_common_ancestor(*interfaces)

            if lcn:
                names[net].prefix = lcn[0].get_full_name()


def _resolve_conflicts_with_suffixes(names: FuncDict[F.Net, _NetName]) -> None:
    """Resolve remaining conflicts by adding numeric suffixes."""
    for conflict_nets in _conflicts(names):
        # Assign suffixes in a deterministic order within a conflict group
        ordered_conflict_nets = sorted(conflict_nets, key=_get_net_stable_key)
        for i, net in enumerate(ordered_conflict_nets):
            names[net].suffix = i


def _truncate_long_name(name: str, max_length: int = 255) -> str:
    """Truncate a long name to fit within the maximum length."""
    if len(name) <= max_length:
        return name

    # Keep first 200 chars and last 50 chars
    return name[:200] + "..." + name[-50:]


def _apply_names_to_nets(names: FuncDict[F.Net, _NetName]) -> None:
    """Apply the computed names to nets, with length limiting."""
    for net, net_name in names.items():
        final_name = _truncate_long_name(net_name.name)
        net.add(F.has_overriden_name_defined(final_name))


def attach_net_names(nets: Iterable[F.Net]) -> None:
    """
    Generate good net names for all nets in a design.

    This function assigns meaningful names to nets based on:
    1. Required names from has_net_name traits (highest priority)
    2. Suggested names from has_net_name traits
    3. Implicit names from connected interfaces
    4. Conflict resolution through prefixing and suffixing

    The naming process follows these steps:
    - Collect and sort unnamed nets
    - Register already-named nets
    - Process unnamed nets to determine base names
    - Apply affixes (prefixes/suffixes) from traits
    - Resolve conflicts through hierarchical prefixing
    - Apply numeric suffixes for remaining conflicts
    - Apply final names to nets
    """
    names = FuncDict[F.Net, _NetName]()

    # Work on a deterministically ordered view of nets throughout
    nets_list = list(nets)
    nets_ordered = sorted(nets_list, key=_get_net_stable_key)

    # Collect unnamed nets
    unnamed_nets = _collect_unnamed_nets(nets_ordered)

    # Register already-named nets
    _register_named_nets(nets_ordered, names)

    # Process unnamed nets
    _process_unnamed_nets(unnamed_nets, names)

    # Apply affixes
    _apply_affixes(unnamed_nets, names)

    # Note: differential pair harmonization removed to avoid cross-net coupling

    # Resolve conflicts through prefixing
    _resolve_conflicts_with_prefixes(names)

    # Resolve remaining conflicts with lowest common ancestor
    _resolve_conflicts_with_lca(names)

    # Final conflict resolution with numeric suffixes
    _resolve_conflicts_with_suffixes(names)

    # Apply the computed names to nets
    _apply_names_to_nets(names)

    assert all(n.has_trait(F.has_overriden_name) for n in nets)
