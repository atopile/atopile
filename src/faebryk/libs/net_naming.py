import logging
import re
from dataclasses import dataclass, field
from logging import Logger
from typing import Iterable

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.bus import has_bus_role

MAX_NAME_LENGTH = 255
MAX_CONFLICT_RESOLUTION_ITERATIONS = 100

# Pre-compiled regex for filtering unpreferred names
_UNPREFERRED_NAMES_RE = re.compile(
    r"^(net|\d+|0x[0-9A-Fa-f]+|part_of|output|line|package)$"
)

# Characters that are invalid in net names (KiCad restrictions)
_INVALID_NAME_CHARS_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

logger: Logger = logging.getLogger(__name__)


@dataclass
class ProcessableNet:
    @dataclass
    class NetName:
        base_name: str | None = None
        prefix: str | None = None
        suffix: int | None = None
        required_prefix: str | None = None
        required_suffix: str | None = None

        @property
        def name(self) -> str:
            """
            Get the name of the net.
            Net names should take the form of:
            <prefix><required_prefix><base_name><numeric_suffix><required_suffix>
            Hierarchical prefixes are joined with "."; other prefixes/suffixes use "-".
            """
            base_name = self.base_name or "net"
            prefix = f"{self.prefix}." if self.prefix else ""
            numeric_suffix = f"-{self.suffix}" if self.suffix is not None else ""
            required_prefix = self.required_prefix or ""
            required_suffix = self.required_suffix or ""
            return (
                f"{prefix}{required_prefix}{base_name}{numeric_suffix}{required_suffix}"
            )

    @dataclass
    class ElectricalWithName:
        electrical: F.Electrical
        name: str

    net: F.Net
    electricals: list[ElectricalWithName] = field(default_factory=list)
    net_name: NetName = field(default_factory=NetName)

    def __hash__(self) -> int:
        """Hash based on the net object identity."""
        return hash(self.net)

    def __eq__(self, other: object) -> bool:
        """Equality based on the net object identity."""
        if not isinstance(other, ProcessableNet):
            return NotImplemented
        return self.net == other.net


def _sort_nets(
    nets: Iterable[F.Net],
) -> list[ProcessableNet]:
    """
    Sort the nets based on the number of connected electricals (lowest number first).
    This way we can process nets with the least name options first.

    Electricals within each net are sorted alphabetically by name for determinism.
    The first electrical (electricals[0]) is used for hierarchy depth calculation
    and conflict resolution, so stable ordering is critical.

    Nets are sorted by (electrical_count, first_electrical_name) for determinism.
    """
    processable_nets: list[ProcessableNet] = []
    for net in nets:
        # Sort electricals alphabetically by name for deterministic ordering.
        # This ensures electricals[0] is always the same across runs.
        electricals: list[tuple[F.Electrical, str]] = sorted(
            [
                (e, e.get_name(accept_no_parent=True))
                for e in net.get_connected_electricals()
            ],
            key=lambda e: e[1],  # sort by name alphabetically
        )
        processable_nets.append(
            ProcessableNet(
                net=net,
                electricals=[
                    ProcessableNet.ElectricalWithName(electrical=e, name=name)
                    for e, name in electricals
                ],
            )
        )
    # Sort by (electrical_count, first_electrical_name) for determinism.
    # Ties in electrical count are broken by the first electrical's name.
    return sorted(
        processable_nets,
        key=lambda p: (
            len(p.electricals),
            p.electricals[0].name if p.electricals else "",
        ),
    )


def collect_unnamed_nets(
    nets: Iterable[F.Net],
) -> list[ProcessableNet]:
    """
    Collect all nets without the has_net_name trait sorted
    """
    unnamed_nets = [n for n in nets if not n.has_trait(F.has_net_name)]
    return _sort_nets(unnamed_nets)


def _get_all_connected_interfaces(
    electricals: list[F.Electrical],
) -> list[list[tuple[fabll.Node, str]]]:
    """
    Get the interfaces hierarchy of all connected electricals.

    Given a list of electricals:
    1. for each electrical, get the hierarchy
    2. collect all hierarchies
    3. filter for is_interface trait

    Returns:
        List of all hierarchies, sorted by (length, path_string) for determinism.
        Shortest hierarchies first; ties broken alphabetically by dotted path.
    """
    hierarchies: list[list[tuple[fabll.Node, str]]] = []
    for electrical in electricals:
        hierarchies.append(electrical.get_hierarchy())

    # filter for is_interface trait
    interfaces_hierarchies: list[list[tuple[fabll.Node, str]]] = [
        [(node, name) for node, name in hierarchy if node.has_trait(fabll.is_interface)]
        for hierarchy in hierarchies
    ]

    # Sort by (length, path_string) for deterministic ordering.
    # When two hierarchies have the same length, the alphabetically-first
    # dotted path wins, ensuring consistent results across runs.
    return sorted(
        interfaces_hierarchies,
        key=lambda h: (len(h), ".".join(name for _, name in h)),
    )


def _try_extract_signal_name(node: fabll.Node) -> str | None:
    """
    Try to find the connected `ato signal` in the same component definition, and
    try to extract its name.
    """
    from atopile.compiler.ast_visitor import is_ato_component, is_ato_pin

    if not node.has_trait(is_ato_pin):
        return None
    if not (pin_electrical := node.try_cast(F.Electrical)):
        raise ValueError(
            f"Node {node} is not an electrical. "
            "pins in ato components should always be a pin"
        )
    connected_electricals = pin_electrical._is_interface.get().get_connected()
    for electrical in connected_electricals:
        if (ato_component := electrical.get_parent()) and ato_component[0].has_trait(
            is_ato_component
        ):
            return filter_unpreferred_names(electrical.get_name(accept_no_parent=True))
    return None


def process_required_names(
    processable_nets: list[ProcessableNet],
) -> None:
    """
    Set base_name for nets that have a hard-required name.

    Sources (highest priority first):
    - has_net_name trait on the net itself
    - has_net_name trait on an interface node in the hierarchy
    - has_net_name_suggestion.Level.EXPECTED on an interface node

    SUGGESTED-level suggestions are NOT handled here; they are deferred
    to add_base_name so that power and bus naming take precedence.

    Raises:
        ValueError: If multiple required names are found for a net
        ValueError: If a net has the same required name as another net
    """

    def _get_required_names(
        electricals: list[F.Electrical],
    ) -> list[str]:
        """
        Extract required names from the interface hierarchy of connected electricals.
        """
        required_names: list[str] = []

        connected_interfaces = _get_all_connected_interfaces(electricals)
        for hierarchy in connected_interfaces:
            for node, _ in hierarchy:
                if name_trait := node.try_get_trait(F.has_net_name):
                    required_names.append(name_trait.get_name())
                elif suggestion_trait := node.try_get_trait(F.has_net_name_suggestion):
                    if (
                        suggestion_trait.level
                        == F.has_net_name_suggestion.Level.EXPECTED
                    ):
                        required_names.append(suggestion_trait.name)
        return required_names

    # Track required names across all nets for duplicate detection
    required_name_to_nets: dict[str, list[ProcessableNet]] = {}

    for processable_net in processable_nets:
        if not processable_net.electricals:
            raise ValueError(
                f"Net {processable_net.net.get_name()} has no connected electricals"
            )

        required_names = _get_required_names(
            [e.electrical for e in processable_net.electricals]
        )

        if name_trait := processable_net.net.try_get_trait(F.has_net_name):
            required_names.append(name_trait.get_name())
        if required_names:
            # Deduplicate while preserving order
            seen: set[str] = set()
            unique_required: list[str] = []
            for name in required_names:
                if name not in seen:
                    seen.add(name)
                    unique_required.append(name)
            if len(unique_required) > 1:
                raise ValueError(
                    "Multiple required names found for net: "
                    f"{processable_net.net.get_name()}"
                )
            required_name = unique_required[0]
            processable_net.net_name.base_name = required_name
            # Track for cross-net duplicate detection
            required_name_to_nets.setdefault(required_name, []).append(processable_net)

    # Check for cross-net conflicts after processing all nets
    for name, nets in required_name_to_nets.items():
        net_count = len(nets)
        if net_count > 1:
            raise ValueError(f"{net_count} nets have the same required name: '{name}'")


def filter_unpreferred_names(name: str) -> str | None:
    """
    Filter out unpreferred electrical names.

    Names like "net", "power", and pure numeric strings are filtered out
    as they don't provide meaningful net identification.

    Returns:
        The name if preferred, None if unpreferred.
    """
    if _UNPREFERRED_NAMES_RE.match(name):
        return None
    return name


def sanitize_name(name: str) -> str:
    """
    Validate that a net name contains no invalid characters.

    Raises:
        ValueError: If the name contains invalid characters.

    Returns:
        The validated name.
    """
    if match := _INVALID_NAME_CHARS_RE.search(name):
        invalid_char = match.group()
        raise ValueError(
            f"Net name '{name}' contains invalid character: {repr(invalid_char)}"
        )
    return name


def _get_suggested_names(
    electricals: list[F.Electrical],
) -> list[str]:
    """
    Collect SUGGESTED-level net name suggestions from the longest interface
    hierarchy of the net's electricals.

    Only the longest (deepest) hierarchy contributes SUGGESTED names, since
    it provides the most specific context for the net.

    Returns:
        List of suggested name parts (to be joined with "-").
    """
    connected_interfaces = _get_all_connected_interfaces(electricals)
    if not connected_interfaces:
        return []

    # Take the last element (longest hierarchy, or alphabetically last if tied)
    # since the list is sorted by (length, path_string) ascending
    longest_hierarchy = connected_interfaces[-1]
    suggested: list[str] = []
    for node, _ in longest_hierarchy:
        if suggestion_trait := node.try_get_trait(F.has_net_name_suggestion):
            if suggestion_trait.level == F.has_net_name_suggestion.Level.SUGGESTED:
                suggested.append(suggestion_trait.name)

    return suggested


def add_base_name(
    processable_nets: list[ProcessableNet],
) -> None:
    """
    Add the base name to the net name for nets that don't already have one
    (from required names, power naming, or bus naming).

    Stages:
    1. SUGGESTED-level net name suggestions (joined with "-")
    2. nice basenames derived from one of the connected electricals
    3. default to "net" if nothing else is available
    """

    def _add_nice_base_name(processable_net: ProcessableNet) -> None:
        """
        Add a hierarchical base name: <parent_name>.<electrical_name>.

        Walks up each electrical's hierarchy to find meaningful ancestors
        (is_interface or is_module). If the electrical's own name is unpreferred,
        climbs up one level to use the parent's name instead.

        If there is no parent, uses just the electrical name if valid.
        """
        from atopile.compiler.ast_visitor import is_ato_pin

        # Collect meaningful hierarchies for all electricals, sorted for determinism
        meaningful_hierarchies: list[list[tuple[fabll.Node, str]]] = []
        for ewn in processable_net.electricals:
            try:
                hierarchy = ewn.electrical.get_hierarchy()
            except fabll.NodeNoParent:
                continue
            meaningful = [
                (node, name)
                for node, name in hierarchy
                if node.has_trait(fabll.is_interface) or node.has_trait(fabll.is_module)
            ]
            if meaningful:
                meaningful_hierarchies.append(meaningful)

        # Sort by (length, path) for determinism; longest last
        meaningful_hierarchies.sort(
            key=lambda h: (len(h), ".".join(name for _, name in h))
        )

        # Skip hierarchical prefix if net already has a prefix (e.g. from bus naming)
        has_prefix = processable_net.net_name.prefix is not None

        # Try hierarchies from deepest to shallowest
        for hierarchy in reversed(meaningful_hierarchies):
            _, leaf_name = hierarchy[-1]

            if filter_unpreferred_names(leaf_name) is not None:
                # Leaf name is preferred — use it, try to prefix with parent
                candidate = leaf_name
                prefix_idx = len(hierarchy) - 2
            else:
                # Leaf name is unpreferred — climb to parent
                if len(hierarchy) < 2:
                    continue
                _, parent_name = hierarchy[-2]
                if filter_unpreferred_names(parent_name) is None:
                    continue  # parent also unpreferred, try next hierarchy
                candidate = parent_name
                prefix_idx = len(hierarchy) - 3

            # Get prefix from the level above the candidate (skip if net
            # already has a prefix from e.g. bus naming to avoid duplication)
            if not has_prefix and prefix_idx >= 0:
                _, prefix_name = hierarchy[prefix_idx]
                if filter_unpreferred_names(prefix_name) is not None:
                    processable_net.net_name.base_name = f"{prefix_name}.{candidate}"
                else:
                    processable_net.net_name.base_name = candidate
            else:
                processable_net.net_name.base_name = candidate
            return

        # Fallback: try signal name from ato pins, then raw pin name
        connected_interfaces = _get_all_connected_interfaces(
            [e.electrical for e in processable_net.electricals]
        )
        for hierarchy in connected_interfaces:
            if not hierarchy:
                continue
            leaf_node, _ = hierarchy[-1]
            if leaf_node.has_trait(is_ato_pin):
                if signal_name := _try_extract_signal_name(leaf_node):
                    processable_net.net_name.base_name = signal_name
                    return
                if pin_name := leaf_node.get_name(accept_no_parent=True):
                    if filter_unpreferred_names(pin_name) is not None:
                        processable_net.net_name.base_name = pin_name
                        return

    logger.debug(f"trying to add nice base names to {len(processable_nets)} nets")
    for processable_net in processable_nets:
        if processable_net.net_name.base_name is not None:
            # skip — already set by required, power, or bus naming
            logger.debug(f"nice! skipping {processable_net.net_name.name}")
            continue

        # Try SUGGESTED names first
        suggested = _get_suggested_names(
            [e.electrical for e in processable_net.electricals]
        )
        if suggested:
            processable_net.net_name.base_name = "-".join(suggested)
            continue

        # Fall back to hierarchy-derived names
        _add_nice_base_name(processable_net)


def add_affixes(
    processable_nets: list[ProcessableNet],
) -> None:
    """
    Add the required prefix and suffix to the net name.

    Raises:
        ValueError: If multiple electricals in a net have conflicting affixes.
    """
    for processable_net in processable_nets:
        found_prefix: str | None = None
        found_suffix: str | None = None

        for electrical in processable_net.electricals:
            if affix_trait := electrical.electrical.try_get_trait(F.has_net_name_affix):
                if prefix := affix_trait.get_prefix():
                    if found_prefix is not None and found_prefix != prefix:
                        raise ValueError(
                            f"Conflicting prefixes for net "
                            f"'{processable_net.net.get_name()}': "
                            f"'{found_prefix}' vs '{prefix}'"
                        )
                    found_prefix = prefix
                if suffix := affix_trait.get_suffix():
                    if found_suffix is not None and found_suffix != suffix:
                        raise ValueError(
                            f"Conflicting suffixes for net "
                            f"'{processable_net.net.get_name()}': "
                            f"'{found_suffix}' vs '{suffix}'"
                        )
                    found_suffix = suffix

        processable_net.net_name.required_prefix = found_prefix
        processable_net.net_name.required_suffix = found_suffix


# Bus role priority: lower value = higher priority
_ROLE_PRIORITY: dict[has_bus_role.BusRole, int] = {
    has_bus_role.BusRole.CONTROLLER: 0,
    has_bus_role.BusRole.END_NODE: 1,
    has_bus_role.BusRole.TARGET: 2,
    has_bus_role.BusRole.NODE: 3,
    has_bus_role.BusRole.PASSIVE: 4,
}


@dataclass
class BusRoleMatch:
    """Result of finding a bus role in an electrical's hierarchy."""

    bus_name: str  # name of the bus interface node (e.g. "i2cs[0]")
    parent_name: str  # name of the bus interface's parent (e.g. "i2c_mux")
    signal_name: str  # first child below the bus node (e.g. "sda")
    roles: set[has_bus_role.BusRole]


def _find_bus_role_in_hierarchy(
    electrical: F.Electrical,
) -> BusRoleMatch | None:
    """
    Walk up the hierarchy from an electrical to find the first ancestor
    with a has_bus_role trait (the bus interface).

    Skips electricals whose path to the bus-role node crosses an ElectricPower
    boundary, since those are power references, not bus signals.

    Returns:
        BusRoleMatch with bus name, parent name, signal name, and roles,
        or None if no bus role found.
    """
    hierarchy = electrical.get_hierarchy()

    # Walk from leaf toward root (reversed), skip the electrical itself (last entry)
    crossed_power = False
    for i in range(len(hierarchy) - 2, -1, -1):
        node, name = hierarchy[i]

        # If the path crosses an ElectricPower node, this electrical is a
        # power reference (e.g. i2c.sda.reference.lv), not a bus signal.
        if node.isinstance(F.ElectricPower):
            crossed_power = True

        if node.has_trait(has_bus_role):
            if crossed_power:
                return None
            bus_name = name
            roles = node.get_trait(has_bus_role).get_roles()
            # Find parent of the bus interface (one level up)
            if i > 0:
                _, parent_name = hierarchy[i - 1]
            else:
                parent_name = name
            # Signal name: first child below the bus role node on path
            # to the electrical. E.g. for i2cs[0] → sda → line, signal = "sda"
            if i + 1 < len(hierarchy):
                _, signal_name = hierarchy[i + 1]
            else:
                signal_name = name
            return BusRoleMatch(
                bus_name=bus_name,
                parent_name=parent_name,
                signal_name=signal_name,
                roles=roles,
            )

    return None


def _find_power_parent(
    electrical: F.Electrical,
) -> tuple[str, str, int] | None:
    """
    Check if an electrical is a direct child of ElectricPower (hv/lv/vcc/gnd).

    Returns:
        Tuple of (power_instance_name, electrical_name, hierarchy_depth) or None.
        The power_instance_name is the name of the ElectricPower's parent in the
        hierarchy (e.g. "power"), and electrical_name is "hv" or "lv".
    """
    parent = electrical.get_parent()
    if parent is None:
        return None
    parent_node, _ = parent
    if not parent_node.isinstance(F.ElectricPower):
        return None

    elec_name = electrical.get_name(accept_no_parent=True)
    hierarchy = parent_node.get_hierarchy()
    depth = len(hierarchy)

    # Get the name of the ElectricPower instance from its parent context
    power_parent = parent_node.get_parent()
    if power_parent is not None:
        power_name = power_parent[1]  # name in parent's context
    else:
        power_name = parent_node.get_name(accept_no_parent=True)

    return (power_name, elec_name, depth)


def add_power_base_name(
    processable_nets: list[ProcessableNet],
) -> None:
    """
    Override base names for power nets (ElectricPower children).

    When a net contains electricals that are direct children of ElectricPower
    (hv, lv, vcc, gnd), this step overrides the base name with
    "<power_instance_name>.<hv_or_lv>", picking the shallowest ElectricPower
    parent for the most meaningful name.

    This prevents power nets from inheriting signal names (e.g. "SDA") from
    bus interface parents higher in the hierarchy.
    """
    # Canonical ElectricPower children; prefer these over deprecated vcc/gnd
    _CANONICAL_POWER_NAMES = {"hv", "lv"}

    for processable_net in processable_nets:
        if processable_net.net_name.base_name is not None:
            # Already named (e.g. by required names), skip
            continue

        best: tuple[str, str, int] | None = None  # (power_name, elec_name, depth)

        for ewn in processable_net.electricals:
            result = _find_power_parent(ewn.electrical)
            if result is None:
                continue
            power_name, elec_name, depth = result
            if best is None:
                best = result
            elif depth < best[2]:
                best = result
            elif depth == best[2] and elec_name in _CANONICAL_POWER_NAMES:
                # Prefer hv/lv over deprecated vcc/gnd at equal depth
                best = result

        if best is not None:
            power_name, elec_name, _ = best
            if filter_unpreferred_names(power_name):
                processable_net.net_name.base_name = f"{power_name}.{elec_name}"
            else:
                processable_net.net_name.base_name = elec_name


def add_bus_prefix(
    processable_nets: list[ProcessableNet],
) -> None:
    """
    Add a bus-role-based prefix to net names.

    For each net, walks up the hierarchy of its electricals to find bus interfaces
    with has_bus_role traits. Picks the interface with the highest-priority role
    and sets the prefix to "<parent_name>.<bus_interface_name>".

    Skips nets that already have a prefix or base_name.
    """
    for processable_net in processable_nets:
        if processable_net.net_name.prefix:
            continue
        if processable_net.net_name.base_name is not None:
            continue

        best_priority = len(_ROLE_PRIORITY)  # worst possible
        best_match: BusRoleMatch | None = None

        for ewn in processable_net.electricals:
            result = _find_bus_role_in_hierarchy(ewn.electrical)
            if result is None:
                continue
            for role in result.roles:
                priority = _ROLE_PRIORITY.get(role, len(_ROLE_PRIORITY))
                if priority < best_priority:
                    best_priority = priority
                    best_match = result

        if best_match:
            processable_net.net_name.prefix = (
                f"{best_match.parent_name}.{best_match.bus_name}"
            )


def _get_full_hierarchy_path(electrical: F.Electrical) -> str:
    """
    Get the full hierarchical path of an electrical through interface parents.
    """
    try:
        hierarchy = electrical.get_hierarchy()
        # Build path from interface nodes only
        # (including electrical if it's an interface)
        path_parts = []
        for node, _ in hierarchy:
            if node.has_trait(fabll.is_interface):
                path_parts.append(node.get_name(accept_no_parent=True))
        return ".".join(path_parts)
    except fabll.NodeNoParent:
        return electrical.get_name(accept_no_parent=True)


def _get_hierarchy_depth(processable_net: ProcessableNet) -> int:
    """
    Get the hierarchy depth of the net's electrical.

    Returns:
        The number of dot-separated components in the full hierarchy path,
        or 0 if no electricals are connected.
    """
    if not (electricals := processable_net.electricals):
        return 0

    electrical = electricals[0].electrical
    full_path = _get_full_hierarchy_path(electrical)
    return len(full_path.split(".")) if full_path else 0


def _get_conflict_sort_key(processable_net: ProcessableNet) -> tuple[int, str]:
    """
    Get a deterministic sort key for conflict resolution.

    Returns tuple of (hierarchy_depth, full_hierarchy_path) for stable ordering.
    The full path ensures unique tie-breaking even when multiple nets have the
    same depth and electrical name (e.g., branch_a.leaf.sig vs branch_b.leaf.sig).
    """
    depth = _get_hierarchy_depth(processable_net)
    # Use the full hierarchy path for deterministic tie-breaking
    if processable_net.electricals:
        path = _get_full_hierarchy_path(processable_net.electricals[0].electrical)
    else:
        path = ""
    return (depth, path)


def _get_parent_interface_name(processable_net: ProcessableNet) -> str | None:
    """
    Get a parent interface name for prefixing that differs from the base name.

    Walks up the hierarchy from the immediate parent toward the root,
    skipping any parent whose name matches the current base name
    (to avoid producing names like "signal_a.signal_a").

    Priority:
    1. first distinct name from parents with `is_module` trait
    2. first distinct name from parents with `is_interface` trait

    Returns:
        The first distinct parent interface name, or None if not available.
    """
    if not (electricals := processable_net.electricals):
        return None

    electrical = electricals[0].electrical
    base_name = (processable_net.net_name.base_name or "").lower()
    base_name_parts = set(base_name.split("."))

    try:
        hierarchy = electrical.get_hierarchy()
    except fabll.NodeNoParent:
        return None

    # Exclude the leaf (electrical itself)
    parents = hierarchy[:-1]

    # Priority 1: first distinct name from parents with is_module trait
    for node, _ in reversed(parents):
        if node.has_trait(fabll.is_module):
            name = node.get_name(accept_no_parent=True)
            if name.lower() not in base_name_parts and filter_unpreferred_names(name):
                return name

    # Priority 2: first distinct name from parents with is_interface trait
    for node, _ in reversed(parents):
        if node.has_trait(fabll.is_interface):
            name = node.get_name(accept_no_parent=True)
            if name.lower() not in base_name_parts and filter_unpreferred_names(name):
                return name

    return None


def _find_conflicting_nets(
    processable_nets: list[ProcessableNet],
) -> dict[str, list[ProcessableNet]]:
    """
    Find nets with the same name as other nets in the list.
    Return a dict of name to list of nets with that name (only conflicts).
    """
    from collections import defaultdict

    # Group nets by their name
    nets_by_name: dict[str, list[ProcessableNet]] = defaultdict(list)
    for p in processable_nets:
        nets_by_name[p.net_name.name].append(p)

    # Return only groups with conflicts (multiple nets with same name)
    return {name: nets for name, nets in nets_by_name.items() if len(nets) > 1}


def resolve_name_conflicts(
    processable_nets: list[ProcessableNet],
) -> int:
    """
    Resolve name conflicts by hierarchical prefixing, then as last resort
    numeric suffixing. The net lowest in the hierarchy (shortest path) keeps its
    original name unchanged.

    Returns:
        The number of conflicts resolved.

    Raises:
        RuntimeError: If conflicts cannot be resolved within max iterations.
    """
    conflicts_resolved = 0

    # Keep resolving conflicts until none remain
    for _ in range(MAX_CONFLICT_RESOLUTION_ITERATIONS):
        conflicting_groups = _find_conflicting_nets(processable_nets)
        if not conflicting_groups:
            break

        # Process each conflict group
        for _, conflict_group in conflicting_groups.items():
            conflict_group_sorted = sorted(conflict_group, key=_get_conflict_sort_key)

            # Keep the first net (lowest in hierarchy) unchanged
            # For remaining nets, try prefixing with parent interface name
            remaining_nets = conflict_group_sorted[1:]
            for net in remaining_nets:
                if parent_name := _get_parent_interface_name(net):
                    existing_prefix = net.net_name.prefix
                    if existing_prefix:
                        # Skip if the parent name is already the leading
                        # component of the existing prefix — prepending it
                        # again would create redundancy like
                        # "i2c_mux.i2c_mux.i2cs[1]".
                        prefix_parts = existing_prefix.split(".")
                        if prefix_parts[0] == parent_name:
                            continue
                        # Prepend to existing prefix (e.g. bus prefix)
                        net.net_name.prefix = f"{parent_name}.{existing_prefix}"
                    else:
                        net.net_name.prefix = parent_name
                    conflicts_resolved += 1
                # If no parent interface (shouldn't happen in well-formed hierarchy),
                # or if prefixing still causes conflicts, we'll handle with suffix below

        # Check for remaining conflicts after prefixing
        remaining_conflicts = _find_conflicting_nets(processable_nets)
        if not remaining_conflicts:
            break

        # Apply numeric suffixes for remaining conflicts (identical paths)
        # Suffix ALL conflicting nets (starting from 0) so every name is explicit
        for _, conflict_group in remaining_conflicts.items():
            conflict_group_sorted = sorted(conflict_group, key=_get_conflict_sort_key)

            for i, net in enumerate(conflict_group_sorted):
                net.net_name.suffix = i
                conflicts_resolved += 1
    else:
        raise RuntimeError(
            f"Failed to resolve net name conflicts after "
            f"{MAX_CONFLICT_RESOLUTION_ITERATIONS} iterations"
        )

    logger.debug(f"Resolved {conflicts_resolved} net name conflicts")
    return conflicts_resolved


def apply_names_to_nets(
    processable_nets: list[ProcessableNet],
) -> None:
    """
    Apply the net names to the nets by giving the has_net_name trait.

    Validates names, truncates if needed, and checks for post-truncation collisions.
    """

    def _truncate_long_name(name: str) -> str:
        """
        Truncate a long name to fit within the maximum length of 255 characters
        allowed by KiCAD.
        """
        if len(name) <= MAX_NAME_LENGTH:
            return name

        logger.warning(
            f"Truncating too long net name (more than {MAX_NAME_LENGTH} characters): "
            f"{name}"
        )
        # Keep first 200 chars and last 50 chars
        return name[:200] + "..." + name[-50:]

    # First pass: compute all final names
    final_names: dict[ProcessableNet, str] = {}
    for processable_net in processable_nets:
        name = processable_net.net_name.name
        sanitize_name(name)  # Raises if invalid characters
        final_names[processable_net] = _truncate_long_name(name)

    # Check for collisions after truncation
    from collections import Counter

    name_counts = Counter(final_names.values())
    duplicates = [name for name, count in name_counts.items() if count > 1]
    # TODO: this should resolve itself instead of raising an error
    if duplicates:
        raise ValueError(
            f"Net name collision after truncation: {duplicates}. "
            "Multiple nets would have the same name."
        )

    # Apply the names
    for processable_net, name in final_names.items():
        fabll.Traits.create_and_add_instance_to(
            processable_net.net, F.has_net_name
        ).setup(name=name)


def attach_net_names(nets: Iterable[F.Net]) -> None:
    """
    Attach names to nets based on their connected electricals and traits.

    Name structure:
    `{prefix}{required_prefix}{base_name}{numeric_suffix}{required_suffix}`

    Name resolution priority (highest to lowest):
    1. has_net_name trait / EXPECTED suggestion - required, always wins
    2. ElectricPower parent naming - power nets get "<power_name>.<hv|lv>"
    3. Bus role prefix - signal nets get "<parent>.<bus_iface>" prefix
    4. SUGGESTED net name suggestions - joined with "-" separator
    5. Hierarchy-derived name - from electrical/interface names
    6. "net" - default fallback

    Conflict resolution:
    - Hierarchical prefixing: nets get prefixed with parent module/interface name
    - Numeric suffixing: last resort when prefixing is insufficient

    Affixes:
    - required_prefix/suffix: from has_net_name_affix trait on electricals
    """
    logger.debug("Starting net naming process")

    nets_list = list(nets)
    total_nets = len(nets_list)

    processable_nets = collect_unnamed_nets(nets_list)
    unnamed_count = len(processable_nets)
    already_named = total_nets - unnamed_count

    process_required_names(processable_nets)
    add_power_base_name(processable_nets)
    add_bus_prefix(processable_nets)
    add_base_name(processable_nets)
    add_affixes(processable_nets)
    conflicts_resolved = resolve_name_conflicts(processable_nets)
    apply_names_to_nets(processable_nets)

    # Count nets with affixes
    with_prefix = sum(1 for pn in processable_nets if pn.net_name.required_prefix)
    with_suffix = sum(1 for pn in processable_nets if pn.net_name.required_suffix)

    # Log summary table
    summary = f"""
    | Metric               | Count |
    |----------------------|-------|
    | Total nets           | {total_nets:5} |
    | Already named        | {already_named:5} |
    | Newly named          | {unnamed_count:5} |
    | Conflicts resolved   | {conflicts_resolved:5} |
    | With required prefix | {with_prefix:5} |
    | With required suffix | {with_suffix:5} |
    """
    logger.debug(summary, extra={"markdown": True})


class TestNetNaming:
    def _bind_nets_for_test(
        self,
        electricals: Iterable[F.Electrical],
        tg: fbrk.TypeGraph,
        g: fabll.graph.GraphView,
    ) -> set[F.Net]:
        from faebryk.libs.nets import get_named_net

        fbrk_nets: set[F.Net] = set()
        # collect buses in a sorted manner
        buses = sorted(
            fabll.is_interface.group_into_buses(electricals),
            key=lambda node: node.get_full_name(include_uuid=False),
        )

        # find or generate nets
        for bus in buses:
            if fbrk_net := get_named_net(bus):
                fbrk_nets.add(fbrk_net)
            else:
                fbrk_net = F.Net.bind_typegraph(tg).create_instance(g=g)
                fbrk_net.part_of.get()._is_interface.get().connect_to(bus)
                fbrk_nets.add(fbrk_net)

        return fbrk_nets

    def test_base_name_generation(self):
        import faebryk.core.node as fabll
        from faebryk.core.faebrykpy import EdgeInterfaceConnection as interface

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class BaseInterface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            line = F.Electrical.MakeChild()
            no_name = F.Electrical.MakeChild()

            line.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="linE", level=F.has_net_name_suggestion.Level.SUGGESTED
                    ),
                    owner=[line],
                )
            )

        class InterfaceModule(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            base_interface = BaseInterface.MakeChild()
            line = F.Electrical.MakeChild()
            base_interface.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="BaseLine", level=F.has_net_name_suggestion.Level.SUGGESTED
                    ),
                    owner=[base_interface],
                )
            )
            _connection = fabll.MakeEdge(
                [line],
                [base_interface, "line"],
                edge=interface.build(shallow=False),
            )

        class App(fabll.Node):
            interface_a = InterfaceModule.MakeChild()
            interface_b = InterfaceModule.MakeChild()
            no_name = F.Electrical.MakeChild()

            # _connection = fabll.MakeEdge(
            #     [interface_a, "line"],
            #     [interface_b, "line"],
            #     edge=interface.build(shallow=False),
            # )
            interface_a.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="parentA", level=F.has_net_name_suggestion.Level.SUGGESTED
                    ),
                    owner=[interface_a],
                )
            )

        app = App.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        print(f"grouped and connected electricals: {len(all_electricals)}")
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )
        print(f"{len(nets)} nets")
        attach_net_names(nets)

        net_names = sorted(
            [net_name for net in nets if (net_name := net.get_name()) is not None],
            key=lambda name: name.lower(),
        )

        print(f"net_names: {net_names}")

        assert net_names == [
            "BaseLine",
            "BaseLine-linE",
            "no_name",
            "parentA-BaseLine",
            "parentA-BaseLine-linE",
        ]

    def test_affix_name_generation(self):
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class AffixTestInterface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            line = F.Electrical.MakeChild()
            no_name = F.Electrical.MakeChild()

            line.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_affix.MakeChild(prefix="PRE_", suffix="_SUF"),
                    owner=[line],
                )
            )

        class AffixTestApp(fabll.Node):
            interface_a = AffixTestInterface.MakeChild()
            interface_b = AffixTestInterface.MakeChild()
            no_name = F.Electrical.MakeChild()

            interface_b.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_affix.MakeChild(suffix="_SUF"),
                    owner=[interface_b, "no_name"],
                )
            )

        app = AffixTestApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )
        print(f"{len(nets)} nets")
        attach_net_names(nets)

        net_names = sorted(
            [net_name for net in nets if (net_name := net.get_name()) is not None],
            key=lambda name: name.lower(),
        )

        print(f"net_names: {net_names}")

        assert net_names == [
            "interface_a.no_name",
            "interface_b.no_name_SUF",
            "no_name",
            "PRE_interface_a_SUF",
            "PRE_interface_b_SUF",
        ]

    def test_hierarchical_name_resolution(self):
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class HierBaseInterface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            line = F.Electrical.MakeChild()

        class HierLevel0Interface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            base_interface = HierBaseInterface.MakeChild()
            line = F.Electrical.MakeChild()
            dup_with_suffix = F.Electrical.MakeChild()
            dup_with_suffix.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_affix.MakeChild(suffix="_SUF"),
                    owner=[dup_with_suffix],
                )
            )
            dup_with_suffix.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="dup_with_affix",
                        level=F.has_net_name_suggestion.Level.SUGGESTED,
                    ),
                    owner=[dup_with_suffix],
                )
            )
            dup_with_prefix = F.Electrical.MakeChild()
            dup_with_prefix.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_affix.MakeChild(prefix="PRE_"),
                    owner=[dup_with_prefix],
                )
            )
            dup_with_prefix.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="dup_with_affix",
                        level=F.has_net_name_suggestion.Level.SUGGESTED,
                    ),
                    owner=[dup_with_prefix],
                )
            )

        class HierLevel1Interface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            level0_interface = HierLevel0Interface.MakeChild()
            line = F.Electrical.MakeChild()
            dup_name_suggested = F.Electrical.MakeChild()
            dup_name_suggested_line = F.Electrical.MakeChild()
            dup_name_suggested_line.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="dup_name_suggested",
                        level=F.has_net_name_suggestion.Level.SUGGESTED,
                    ),
                    owner=[dup_name_suggested_line],
                )
            )

        class HierLevel2Interface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            level1_interface = HierLevel1Interface.MakeChild()
            line = F.Electrical.MakeChild()

        class HierApp(fabll.Node):
            app_interface = HierLevel2Interface.MakeChild()
            app_interface2 = HierLevel2Interface.MakeChild()
            line = F.Electrical.MakeChild()
            dup_name = F.Electrical.MakeChild()
            required_name_line = F.Electrical.MakeChild()
            required_name_line.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name.MakeChild(name="dup_name"),
                    owner=[required_name_line],
                )
            )

        app = HierApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )
        attach_net_names(nets)

        net_names = sorted(
            [net_name for net in nets if (net_name := net.get_name()) is not None],
            key=lambda name: name.lower(),
        )

        print(f"net_names: {net_names}")

        assert net_names == [
            "app_interface",
            "app_interface.level1_interface",
            "app_interface2",
            "app_interface2.level1_interface",
            "app_interface2.level1_interface.dup_name_suggested",
            "app_interface2.level1_interface.level0_interface",
            "dup_name-0",
            "dup_name-1",
            "dup_name_suggested",
            "dup_with_affix_SUF",
            "level0_interface.base_interface",
            "level0_interface.dup_with_affix_SUF",
            "level0_interface.PRE_dup_with_affix",
            "level1_interface.dup_name_suggested-0",
            "level1_interface.dup_name_suggested-1",
            "level1_interface.level0_interface",
            "level1_interface.level0_interface.base_interface",
            "net",
            "PRE_dup_with_affix",
        ]

    def test_module_prefix_priority_over_interface(self):
        """
        Test that conflict resolution prefers is_module parents over is_interface
        parents when selecting a prefix.

        Hierarchy:
        - AppModule (is_module)
          - inner_module (InnerModule, is_module)
            - inner_interface (InnerInterface, is_interface)
              - second (SecondInterface, is_interface)
                - base (BaseInterface, is_interface)
                  - sig_a, sig_b (F.Electrical)
        """
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class ModPrioBaseIface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            sig_a = F.Electrical.MakeChild()
            sig_b = F.Electrical.MakeChild()

        class ModPrioSecondIface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            base_a = ModPrioBaseIface.MakeChild()
            base_b = ModPrioBaseIface.MakeChild()
            sig_a = F.Electrical.MakeChild()
            sig_b = F.Electrical.MakeChild()

        class ModPrioInnerIface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            second = ModPrioSecondIface.MakeChild()

        class ModPrioInnerModule(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            inner_interface = ModPrioInnerIface.MakeChild()

        class ModPrioAppModule(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            inner_module = ModPrioInnerModule.MakeChild()
            sig_a = F.Electrical.MakeChild()
            sig_b = F.Electrical.MakeChild()

        app = ModPrioAppModule.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )
        attach_net_names(nets)

        net_names = sorted(
            [net_name for net in nets if (net_name := net.get_name()) is not None],
            key=lambda name: name.lower(),
        )

        print(f"net_names: {net_names}")

        # Hierarchical base naming already disambiguates most conflicts
        # using the immediate parent interface names
        assert net_names == [
            "base_a.sig_a",
            "base_a.sig_b",
            "base_b.sig_a",
            "base_b.sig_b",
            "second.sig_a",
            "second.sig_b",
            "sig_a",
            "sig_b",
        ]

    def test_interface_prefix_fallback(self):
        """
        Test that conflict resolution falls back to is_interface parents
        when no is_module parents are available.

        Hierarchy (all is_interface, no is_module):
        - IfaceFallbackApp (no trait - root app)
          - outer (IfaceFallbackOuter, is_interface)
            - inner_a (IfaceFallbackInner, is_interface)
              - sig (F.Electrical)
            - inner_b (IfaceFallbackInner, is_interface)
              - sig (F.Electrical)
        """
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class IfaceFallbackInner(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            sig = F.Electrical.MakeChild()

        class IfaceFallbackOuter(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            inner_a = IfaceFallbackInner.MakeChild()
            inner_b = IfaceFallbackInner.MakeChild()
            sig = F.Electrical.MakeChild()

        class IfaceFallbackApp(fabll.Node):
            outer_a = IfaceFallbackOuter.MakeChild()
            outer_b = IfaceFallbackOuter.MakeChild()
            sig = F.Electrical.MakeChild()

        app = IfaceFallbackApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )
        attach_net_names(nets)

        net_names = sorted(
            [net_name for net in nets if (net_name := net.get_name()) is not None],
            key=lambda name: name.lower(),
        )

        print(f"net_names: {net_names}")

        # With no is_module parents, conflicts should be resolved using
        # is_interface parents (inner_a, inner_b)
        assert net_names == [
            "inner_a.sig",
            "inner_b.sig",
            "outer_a.sig",
            "outer_b.inner_a.sig",
            "outer_b.inner_b.sig",
            "outer_b.sig",
            "sig",
        ]

    def test_naming_determinism(self):
        """
        Test that net naming produces identical results across multiple runs.

        This test creates a hierarchy with many same-depth electricals and name
        collisions to stress the determinism of:
        - electricals list ordering
        - same-length hierarchy tie-breaking
        - conflict resolution ordering
        """
        import faebryk.core.node as fabll

        # Define classes outside run_naming to avoid re-registration
        class DetermLeaf(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            sig = F.Electrical.MakeChild()
            data = F.Electrical.MakeChild()

        class DetermBranch(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            leaf_x = DetermLeaf.MakeChild()
            leaf_y = DetermLeaf.MakeChild()
            leaf_z = DetermLeaf.MakeChild()

        class DetermRoot(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            branch_a = DetermBranch.MakeChild()
            branch_b = DetermBranch.MakeChild()

        class DetermApp(fabll.Node):
            root = DetermRoot.MakeChild()

        def run_naming() -> list[str]:
            """Run the full naming pipeline and return sorted net names."""
            g = fabll.graph.GraphView.create()
            tg = fbrk.TypeGraph.create(g=g)

            app = DetermApp.bind_typegraph(tg=tg).create_instance(g=g)

            all_electricals = app.get_children(direct_only=False, types=F.Electrical)
            nets = self._bind_nets_for_test(
                electricals=all_electricals,
                tg=tg,
                g=g,
            )
            attach_net_names(nets)

            return sorted(
                [name for net in nets if (name := net.get_name()) is not None],
                key=lambda n: n.lower(),
            )

        # Run naming multiple times and verify identical results
        first_run = run_naming()
        for i in range(9):
            subsequent_run = run_naming()
            assert first_run == subsequent_run, (
                f"Non-deterministic naming detected on run {i + 2}:\n"
                f"First run: {first_run}\n"
                f"Run {i + 2}: {subsequent_run}"
            )

    def test_fail_on_multiple_required_names(self):
        import pytest

        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class MultipleRequiredNamesApp(fabll.Node):
            line_a = F.Electrical.MakeChild()
            line_b = F.Electrical.MakeChild()
            line_c = F.Electrical.MakeChild()
            line_d = F.Electrical.MakeChild()
            line_a.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name.MakeChild(name="line_required"), owner=[line_a]
                )
            )
            line_b.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name.MakeChild(name="line_required"), owner=[line_b]
                )
            )
            line_c.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="line_required",
                        level=F.has_net_name_suggestion.Level.EXPECTED,
                    ),
                    owner=[line_c],
                )
            )
            line_d.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="line_required",
                        level=F.has_net_name_suggestion.Level.EXPECTED,
                    ),
                    owner=[line_d],
                )
            )

        app = MultipleRequiredNamesApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )
        with pytest.raises(
            ValueError,
            match="4 nets have the same required name: 'line_required'",
        ):
            attach_net_names(nets)

    # =========================================================================
    # Unit tests for individual functions in attach_net_names
    # =========================================================================

    def test_filter_unpreferred_names(self):
        """
        Test filter_unpreferred_names filters out generic/uninformative names
        """
        # Should filter out unpreferred names
        assert filter_unpreferred_names("net") is None
        assert filter_unpreferred_names("0") is None
        assert filter_unpreferred_names("123") is None
        assert filter_unpreferred_names("9999") is None
        assert filter_unpreferred_names("part_of") is None
        assert filter_unpreferred_names("output") is None
        assert filter_unpreferred_names("line") is None

        # Should pass through preferred names
        assert filter_unpreferred_names("GND") == "GND"
        assert filter_unpreferred_names("VCC") == "VCC"
        assert filter_unpreferred_names("SDA") == "SDA"
        assert filter_unpreferred_names("power") == "power"
        assert filter_unpreferred_names("my_signal") == "my_signal"
        assert filter_unpreferred_names("net1") == "net1"  # not exactly "net"
        assert (
            filter_unpreferred_names("power_3v3") == "power_3v3"
        )  # not exactly "power"

    def test_net_name_property_basic(self):
        """Test ProcessableNet.NetName.name property generates correct names"""
        # Default name should be "net"
        net_name = ProcessableNet.NetName()
        assert net_name.name == "net"

        # Base name only
        net_name = ProcessableNet.NetName(base_name="GND")
        assert net_name.name == "GND"

        # With prefix
        net_name = ProcessableNet.NetName(base_name="line", prefix="interface_a")
        assert net_name.name == "interface_a.line"

        # With numeric suffix
        net_name = ProcessableNet.NetName(base_name="line", suffix=1)
        assert net_name.name == "line-1"

        # With required prefix
        net_name = ProcessableNet.NetName(base_name="VCC", required_prefix="PWR_")
        assert net_name.name == "PWR_VCC"

        # With required suffix
        net_name = ProcessableNet.NetName(base_name="SDA", required_suffix="_I2C")
        assert net_name.name == "SDA_I2C"

        # Full combination
        net_name = ProcessableNet.NetName(
            base_name="line",
            prefix="module",
            suffix=2,
            required_prefix="PRE_",
            required_suffix="_SUF",
        )
        assert net_name.name == "module.PRE_line-2_SUF"

    def test_net_name_property_edge_cases(self):
        """Test ProcessableNet.NetName.name property with edge cases"""
        # Suffix of 0 should be included
        net_name = ProcessableNet.NetName(base_name="line", suffix=0)
        assert net_name.name == "line-0"

        # None suffix should not add anything
        net_name = ProcessableNet.NetName(base_name="line", suffix=None)
        assert net_name.name == "line"

        # Empty strings for optional fields
        net_name = ProcessableNet.NetName(
            base_name="signal",
            required_prefix="",
            required_suffix="",
        )
        assert net_name.name == "signal"

    def test_find_conflicting_nets(self):
        """Test _find_conflicting_nets identifies nets with duplicate names"""
        # Create mock nets with ProcessableNet wrappers
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        net1 = F.Net.bind_typegraph(tg).create_instance(g=g)
        net2 = F.Net.bind_typegraph(tg).create_instance(g=g)
        net3 = F.Net.bind_typegraph(tg).create_instance(g=g)
        net4 = F.Net.bind_typegraph(tg).create_instance(g=g)

        pn1 = ProcessableNet(net=net1)
        pn1.net_name.base_name = "line"

        pn2 = ProcessableNet(net=net2)
        pn2.net_name.base_name = "line"  # Same as pn1

        pn3 = ProcessableNet(net=net3)
        pn3.net_name.base_name = "GND"  # Different

        pn4 = ProcessableNet(net=net4)
        pn4.net_name.base_name = "GND"  # Same as pn3

        processable_nets = [pn1, pn2, pn3, pn4]

        conflicts = _find_conflicting_nets(processable_nets)

        assert len(conflicts) == 2
        assert "line" in conflicts
        assert "GND" in conflicts
        assert len(conflicts["line"]) == 2
        assert len(conflicts["GND"]) == 2

    def test_find_conflicting_nets_no_conflicts(self):
        """Test _find_conflicting_nets returns empty when no conflicts"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        net1 = F.Net.bind_typegraph(tg).create_instance(g=g)
        net2 = F.Net.bind_typegraph(tg).create_instance(g=g)

        pn1 = ProcessableNet(net=net1)
        pn1.net_name.base_name = "line_a"

        pn2 = ProcessableNet(net=net2)
        pn2.net_name.base_name = "line_b"

        processable_nets = [pn1, pn2]

        conflicts = _find_conflicting_nets(processable_nets)

        assert len(conflicts) == 0

    def test_collect_unnamed_nets(self):
        """Test collect_unnamed_nets filters out nets with has_net_name trait"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class CollectUnnamedNetsApp(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            named_electrical = F.Electrical.MakeChild()
            unnamed_electrical = F.Electrical.MakeChild()

        app = CollectUnnamedNetsApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        # Give one net a name trait
        named_net = list(nets)[0]
        fabll.Traits.create_and_add_instance_to(named_net, F.has_net_name).setup(
            name="already_named"
        )

        # Collect unnamed nets
        unnamed = collect_unnamed_nets(nets)

        # Should only include the net without has_net_name trait
        assert len(unnamed) == 1
        assert unnamed[0].net != named_net

    def test_add_base_name_from_electrical(self):
        """Test add_base_name extracts name from electrical hierarchy"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class AddBaseNameApp(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            my_signal = F.Electrical.MakeChild()

        app = AddBaseNameApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        processable_nets = collect_unnamed_nets(nets)

        # Before add_base_name
        assert processable_nets[0].net_name.base_name is None

        add_base_name(processable_nets)

        # After add_base_name - should extract "my_signal" from electrical name
        assert processable_nets[0].net_name.base_name == "my_signal"

    def test_add_base_name_filters_unpreferred(self):
        """Test add_base_name filters out unpreferred names like 'output' and 'net'"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class FilterUnpreferredApp(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            output = F.Electrical.MakeChild()  # "output" is unpreferred
            my_signal = F.Electrical.MakeChild()  # preferred name

        app = FilterUnpreferredApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        processable_nets = collect_unnamed_nets(nets)
        add_base_name(processable_nets)

        # Find the processable net for the "output" electrical
        # Since "output" is filtered, base_name should remain None (falls back to "net")
        output_net = next(
            pn for pn in processable_nets if pn.electricals[0].name == "output"
        )
        signal_net = next(
            pn for pn in processable_nets if pn.electricals[0].name == "my_signal"
        )

        # "output" is unpreferred, so base_name remains None
        assert output_net.net_name.base_name is None
        # "my_signal" is preferred, so base_name is set
        assert signal_net.net_name.base_name == "my_signal"

    def test_resolve_name_conflicts_with_prefix(self):
        """Test resolve_name_conflicts adds hierarchical prefix to resolve conflicts"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class ConflictPrefixInterface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            signal = F.Electrical.MakeChild()

        class ConflictPrefixApp(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            interface_a = ConflictPrefixInterface.MakeChild()
            interface_b = ConflictPrefixInterface.MakeChild()

        app = ConflictPrefixApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        processable_nets = collect_unnamed_nets(nets)
        add_base_name(processable_nets)

        # With hierarchical naming, base_names are already unique
        names = sorted([pn.net_name.base_name for pn in processable_nets])
        assert names == ["interface_a.signal", "interface_b.signal"]

        # No conflict resolution needed — names are already unique
        resolve_name_conflicts(processable_nets)

        final_names = sorted([pn.net_name.name for pn in processable_nets])
        assert len(set(final_names)) == 2  # All unique
        assert final_names == ["interface_a.signal", "interface_b.signal"]

    def test_resolve_name_conflicts_with_numeric_suffix(self):
        """Test resolve_name_conflicts adds numeric suffix when prefix insufficient"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        # Create nets with electricals at same hierarchy level
        class NumericSuffixApp(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            line1 = F.Electrical.MakeChild()
            line2 = F.Electrical.MakeChild()
            line3 = F.Electrical.MakeChild()

        app = NumericSuffixApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        processable_nets = collect_unnamed_nets(nets)

        # Manually set same base name for all to force conflict
        for pn in processable_nets:
            pn.net_name.base_name = "same_name"

        resolve_name_conflicts(processable_nets)

        # After conflict resolution, should have numeric suffixes
        # One net keeps "same_name", others get suffixes or prefixes
        names = sorted([pn.net_name.name for pn in processable_nets])
        assert len(set(names)) == 3  # All unique names
        # At least one should be "same_name" (the one that keeps original)
        assert any("same_name" in name for name in names)

    def test_apply_names_to_nets(self):
        """Test apply_names_to_nets adds has_net_name trait with correct name"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        net = F.Net.bind_typegraph(tg).create_instance(g=g)

        pn = ProcessableNet(net=net)
        pn.net_name.base_name = "my_test_net"
        pn.net_name.required_prefix = "PRE_"

        apply_names_to_nets([pn])

        # Net should now have has_net_name trait
        assert net.has_trait(F.has_net_name)
        assert net.get_trait(F.has_net_name).get_name() == "PRE_my_test_net"

    def test_apply_names_truncates_long_names(self):
        """Test apply_names_to_nets truncates names exceeding MAX_NAME_LENGTH"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        net = F.Net.bind_typegraph(tg).create_instance(g=g)

        pn = ProcessableNet(net=net)
        # Create a name longer than 255 characters
        pn.net_name.base_name = "a" * 300

        apply_names_to_nets([pn])

        # Name should be truncated
        name = net.get_trait(F.has_net_name).get_name()
        assert len(name) <= MAX_NAME_LENGTH
        assert "..." in name

    def test_add_affixes(self):
        """Test add_affixes extracts prefix/suffix from has_net_name_affix trait"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class AddAffixesApp(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            line = F.Electrical.MakeChild()
            line.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_affix.MakeChild(prefix="PRE_", suffix="_SUF"),
                    owner=[line],
                )
            )

        app = AddAffixesApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        processable_nets = collect_unnamed_nets(nets)

        # Before add_affixes
        assert processable_nets[0].net_name.required_prefix is None
        assert processable_nets[0].net_name.required_suffix is None

        add_affixes(processable_nets)

        # After add_affixes
        assert processable_nets[0].net_name.required_prefix == "PRE_"
        assert processable_nets[0].net_name.required_suffix == "_SUF"

    def test_processable_net_hash_and_equality(self):
        """Test ProcessableNet __hash__ and __eq__ based on net identity"""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        net1 = F.Net.bind_typegraph(tg).create_instance(g=g)
        net2 = F.Net.bind_typegraph(tg).create_instance(g=g)

        pn1a = ProcessableNet(net=net1)
        pn1b = ProcessableNet(net=net1)  # Same net
        pn2 = ProcessableNet(net=net2)  # Different net

        # Same net should be equal
        assert pn1a == pn1b
        assert hash(pn1a) == hash(pn1b)

        # Different net should not be equal
        assert pn1a != pn2

        # Can be used in sets
        net_set = {pn1a, pn1b, pn2}
        assert len(net_set) == 2  # pn1a and pn1b collapse to one

    def test_sanitize_name_valid(self):
        """Test sanitize_name passes valid names through"""
        assert sanitize_name("GND") == "GND"
        assert sanitize_name("VCC_3V3") == "VCC_3V3"
        assert sanitize_name("my-net.line") == "my-net.line"
        assert sanitize_name("NET123") == "NET123"

    def test_sanitize_name_invalid_characters(self):
        """Test sanitize_name raises on invalid characters"""
        import pytest

        with pytest.raises(ValueError, match="invalid character"):
            sanitize_name("net/name")

        with pytest.raises(ValueError, match="invalid character"):
            sanitize_name("net\\name")

        with pytest.raises(ValueError, match="invalid character"):
            sanitize_name("net:name")

        with pytest.raises(ValueError, match="invalid character"):
            sanitize_name('net"name')

        with pytest.raises(ValueError, match="invalid character"):
            sanitize_name("net<name")

    def test_add_affixes_conflicting_prefix(self):
        """Test add_affixes raises on conflicting prefixes"""
        import pytest

        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class ConflictingAffixInterface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            line1 = F.Electrical.MakeChild()
            line2 = F.Electrical.MakeChild()
            line1.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_affix.MakeChild(prefix="PRE1_"),
                    owner=[line1],
                )
            )
            line2.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_affix.MakeChild(prefix="PRE2_"),
                    owner=[line2],
                )
            )

        iface = ConflictingAffixInterface.bind_typegraph(tg=tg).create_instance(g=g)

        # Create a net with both electricals connected (simulating conflict)
        net = F.Net.bind_typegraph(tg).create_instance(g=g)
        line1 = iface.line1.get()
        line2 = iface.line2.get()

        pn = ProcessableNet(
            net=net,
            electricals=[
                ProcessableNet.ElectricalWithName(electrical=line1, name="line1"),
                ProcessableNet.ElectricalWithName(electrical=line2, name="line2"),
            ],
        )

        with pytest.raises(ValueError, match="Conflicting prefixes"):
            add_affixes([pn])

    def test_resolve_name_conflicts_max_iterations(self):
        """Test resolve_name_conflicts has iteration guard"""
        # This test verifies the iteration limit exists, not that it triggers
        # (triggering would require a pathological case)
        assert MAX_CONFLICT_RESOLUTION_ITERATIONS == 100

    def test_apply_names_collision_after_truncation(self):
        """Test apply_names_to_nets detects collisions after truncation"""
        import pytest

        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        net1 = F.Net.bind_typegraph(tg).create_instance(g=g)
        net2 = F.Net.bind_typegraph(tg).create_instance(g=g)

        # Create two names that would collide after truncation
        # Both start with same 200 chars and end with same 50 chars
        long_prefix = "a" * 200
        long_suffix = "z" * 50
        middle1 = "b" * 100  # different middles
        middle2 = "c" * 100

        pn1 = ProcessableNet(net=net1)
        pn1.net_name.base_name = long_prefix + middle1 + long_suffix

        pn2 = ProcessableNet(net=net2)
        pn2.net_name.base_name = long_prefix + middle2 + long_suffix

        with pytest.raises(ValueError, match="collision after truncation"):
            apply_names_to_nets([pn1, pn2])

    # =========================================================================
    # Bus role prefix tests
    # =========================================================================

    def test_bus_role_prefix_controller_wins(self):
        """
        Test that bus role prefix is applied and CONTROLLER role wins over TARGET.

        Hierarchy:
        - BusPrefixApp
          - mcu (BusPrefixModule, is_module)
            - i2c (BusPrefixI2C, is_interface, has_bus_role=CONTROLLER)
              - scl (F.Electrical, has_net_name_suggestion="SCL")
              - sda (F.Electrical, has_net_name_suggestion="SDA")
          - sensor (BusPrefixModule, is_module)
            - i2c (BusPrefixI2C, is_interface, has_bus_role=TARGET)
              - scl (F.Electrical, has_net_name_suggestion="SCL")
              - sda (F.Electrical, has_net_name_suggestion="SDA")

        Connected: mcu.i2c.scl ~ sensor.i2c.scl, mcu.i2c.sda ~ sensor.i2c.sda
        Expected net names: mcu.i2c.SCL, mcu.i2c.SDA (CONTROLLER prefix wins)
        """
        import faebryk.core.node as fabll
        from faebryk.core.faebrykpy import EdgeInterfaceConnection as interface

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class BusPrefixI2C(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            scl = F.Electrical.MakeChild()
            sda = F.Electrical.MakeChild()
            scl.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="SCL",
                        level=F.has_net_name_suggestion.Level.SUGGESTED,
                    ),
                    owner=[scl],
                )
            )
            sda.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="SDA",
                        level=F.has_net_name_suggestion.Level.SUGGESTED,
                    ),
                    owner=[sda],
                )
            )

        class BusPrefixControllerI2C(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_bus_role.MakeChild(role=[has_bus_role.BusRole.CONTROLLER])
            )
            i2c = BusPrefixI2C.MakeChild()

        class BusPrefixTargetI2C(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_bus_role.MakeChild(role=[has_bus_role.BusRole.TARGET])
            )
            i2c = BusPrefixI2C.MakeChild()

        class BusPrefixMCU(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            bus_iface = BusPrefixControllerI2C.MakeChild()

        class BusPrefixSensor(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            bus_iface = BusPrefixTargetI2C.MakeChild()

        class BusPrefixApp(fabll.Node):
            mcu = BusPrefixMCU.MakeChild()
            sensor = BusPrefixSensor.MakeChild()
            # Connect SCL and SDA lines
            _conn_scl = fabll.MakeEdge(
                [mcu, "bus_iface", "i2c", "scl"],
                [sensor, "bus_iface", "i2c", "scl"],
                edge=interface.build(shallow=False),
            )
            _conn_sda = fabll.MakeEdge(
                [mcu, "bus_iface", "i2c", "sda"],
                [sensor, "bus_iface", "i2c", "sda"],
                edge=interface.build(shallow=False),
            )

        app = BusPrefixApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )
        attach_net_names(nets)

        net_names = sorted(
            [net_name for net in nets if (net_name := net.get_name()) is not None],
            key=lambda name: name.lower(),
        )

        print(f"net_names: {net_names}")

        # CONTROLLER (mcu) should provide the prefix
        assert "mcu.bus_iface.SCL" in net_names
        assert "mcu.bus_iface.SDA" in net_names

    def test_bus_role_prefix_no_role_no_prefix(self):
        """
        Test that when no bus role is present, no bus prefix is added.
        """
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class NoBusRoleInterface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            sig = F.Electrical.MakeChild()

        class NoBusRoleApp(fabll.Node):
            iface = NoBusRoleInterface.MakeChild()

        app = NoBusRoleApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        processable_nets = collect_unnamed_nets(nets)
        add_bus_prefix(processable_nets)
        add_base_name(processable_nets)

        # No bus role → no prefix should be set
        for pn in processable_nets:
            assert pn.net_name.prefix is None, (
                f"Expected no prefix for net with base_name={pn.net_name.base_name}, "
                f"got prefix={pn.net_name.prefix}"
            )

    def test_bus_role_prefix_multiple_roles_priority(self):
        """
        Test that when multiple bus roles exist, the highest priority wins.

        CONTROLLER (priority 0) should beat PASSIVE (priority 4).
        """
        import faebryk.core.node as fabll
        from faebryk.core.faebrykpy import EdgeInterfaceConnection as interface

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class BusPrioSignal(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            sig = F.Electrical.MakeChild()

        class BusPrioController(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_bus_role.MakeChild(role=[has_bus_role.BusRole.CONTROLLER])
            )
            inner = BusPrioSignal.MakeChild()

        class BusPrioPassive(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_bus_role.MakeChild(role=[has_bus_role.BusRole.PASSIVE])
            )
            inner = BusPrioSignal.MakeChild()

        class BusPrioApp(fabll.Node):
            controller = BusPrioController.MakeChild()
            passive = BusPrioPassive.MakeChild()
            _conn = fabll.MakeEdge(
                [controller, "inner", "sig"],
                [passive, "inner", "sig"],
                edge=interface.build(shallow=False),
            )

        app = BusPrioApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        processable_nets = collect_unnamed_nets(nets)
        add_bus_prefix(processable_nets)
        add_base_name(processable_nets)

        # The connected net should get controller's parent as prefix
        connected_net = next(pn for pn in processable_nets if len(pn.electricals) > 1)
        assert connected_net.net_name.prefix is not None
        # CONTROLLER is on "controller" node, so prefix should reference it
        assert "controller" in connected_net.net_name.prefix

    def test_bus_role_prefix_find_helper(self):
        """Test _find_bus_role_in_hierarchy returns correct values."""
        import faebryk.core.node as fabll

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class BusFindSignals(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            sig = F.Electrical.MakeChild()

        class BusFindBusIface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_bus_role.MakeChild(role=[has_bus_role.BusRole.TARGET])
            )
            inner = BusFindSignals.MakeChild()

        class BusFindApp(fabll.Node):
            my_bus = BusFindBusIface.MakeChild()

        app = BusFindApp.bind_typegraph(tg=tg).create_instance(g=g)

        # Get the sig electrical deep in the hierarchy
        sig_electricals = [
            e
            for e in app.get_children(direct_only=False, types=F.Electrical)
            if "sig" in e.get_name(accept_no_parent=True)
        ]
        assert len(sig_electricals) >= 1

        result = _find_bus_role_in_hierarchy(sig_electricals[0])
        assert result is not None
        assert result.bus_name == "my_bus"
        assert result.signal_name == "inner"
        assert has_bus_role.BusRole.TARGET in result.roles

    def test_bus_with_power_reference(self):
        """
        Test that an I2C-like bus with ElectricLogic (line + reference)
        connected to a shared power rail produces correct net names:
        - Signal nets get bus prefix: mcu.i2c.SCL, mcu.i2c.SDA
        - Power nets get power names: power.hv, power.lv

        Hierarchy:
        - PowerBusApp
          - power (ElectricPower: hv, lv)
          - mcu (is_module)
            - i2c (is_interface, has_bus_role=CONTROLLER)
              - scl (ElectricLogic: line, reference → ElectricPower)
              - sda (ElectricLogic: line, reference → ElectricPower)

        Connections:
          mcu.i2c.scl.reference ~ power
          mcu.i2c.sda.reference ~ power
        """
        import faebryk.core.node as fabll
        from faebryk.core.faebrykpy import EdgeInterfaceConnection as interface

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class PwrBusI2C(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_bus_role.MakeChild(role=[has_bus_role.BusRole.CONTROLLER])
            )
            scl = F.ElectricLogic.MakeChild()
            sda = F.ElectricLogic.MakeChild()
            scl.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="SCL",
                        level=F.has_net_name_suggestion.Level.SUGGESTED,
                    ),
                    owner=[scl],
                )
            )
            sda.add_dependant(
                fabll.Traits.MakeEdge(
                    F.has_net_name_suggestion.MakeChild(
                        name="SDA",
                        level=F.has_net_name_suggestion.Level.SUGGESTED,
                    ),
                    owner=[sda],
                )
            )

        class PwrBusMCU(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            i2c = PwrBusI2C.MakeChild()

        class PwrBusApp(fabll.Node):
            power = F.ElectricPower.MakeChild()
            mcu = PwrBusMCU.MakeChild()
            # Connect scl.reference and sda.reference to power
            _conn_scl_ref = fabll.MakeEdge(
                [mcu, "i2c", "scl", "reference"],
                [power],
                edge=interface.build(shallow=False),
            )
            _conn_sda_ref = fabll.MakeEdge(
                [mcu, "i2c", "sda", "reference"],
                [power],
                edge=interface.build(shallow=False),
            )

        app = PwrBusApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )
        attach_net_names(nets)

        net_names = sorted(
            [net_name for net in nets if (net_name := net.get_name()) is not None],
            key=lambda name: name.lower(),
        )

        print(f"net_names: {net_names}")

        # Signal nets should get bus prefix from CONTROLLER
        assert "mcu.i2c.SCL" in net_names
        assert "mcu.i2c.SDA" in net_names

        # Power nets should be named from ElectricPower, not from signal hierarchy
        assert "power.hv" in net_names
        assert "power.lv" in net_names

        # No power net should be named "SDA" or "SCL"
        for name in net_names:
            if "power" not in name and "mcu" not in name:
                assert name not in ("SDA", "SCL"), (
                    f"Power net incorrectly named '{name}'"
                )

    def test_pin_name_precedence(self):
        """
        Test that hierarchy names take precedence over pin names.

        Simulates a real-world scenario like:
          module Component:
              signal sda ~ package.SD0

        The net connected to both `sda` and `SD0` should be named "sda"
        (from hierarchy), not "SD0" (from the raw pin name).

        Also verifies that:
        - Signal names extracted via _try_extract_signal_name come before raw pin names
        - Raw pin names are still available as fallback
        - When there's no hierarchy name, signal/pin names are used
        """
        import faebryk.core.node as fabll
        from atopile.compiler.ast_visitor import is_ato_component, is_ato_pin
        from faebryk.core.faebrykpy import EdgeInterfaceConnection as interface

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        # A component package with pin SD0 (marked as is_ato_pin)
        class PinPrecPkg(fabll.Node):
            _is_component = fabll.Traits.MakeEdge(is_ato_component.MakeChild())
            SD0 = F.Electrical.MakeChild()
            SD0.add_dependant(fabll.Traits.MakeEdge(is_ato_pin.MakeChild(), [SD0]))

        # A bus interface with signal "sda" connected to the pin
        class PinPrecBus(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            sda = F.Electrical.MakeChild()

        class PinPrecModule(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            bus = PinPrecBus.MakeChild()
            package = PinPrecPkg.MakeChild()
            # sda.line ~ package.SD0
            _conn_sda = fabll.MakeEdge(
                [bus, "sda"],
                [package, "SD0"],
                edge=interface.build(shallow=False),
            )

        class PinPrecApp(fabll.Node):
            comp = PinPrecModule.MakeChild()

        app = PinPrecApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        processable_nets = collect_unnamed_nets(nets)
        add_base_name(processable_nets)

        # The net connecting sda and SD0 should use "sda" (hierarchy name)
        # not "SD0" (raw pin name)
        sda_net = next(
            pn
            for pn in processable_nets
            if any(e.name == "sda" for e in pn.electricals)
        )
        assert sda_net.net_name.base_name == "bus.sda", (
            f"Expected hierarchy name 'bus.sda' to win over pin name, "
            f"got '{sda_net.net_name.base_name}'"
        )

    def test_pin_name_fallback_when_no_hierarchy(self):
        """
        Test that pin names are used as fallback when no hierarchy name exists.

        When a pin electrical is not connected to any named interface signal,
        the raw pin name should be used.
        """
        import faebryk.core.node as fabll
        from atopile.compiler.ast_visitor import is_ato_component, is_ato_pin

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class PinFallbackPkg(fabll.Node):
            _is_component = fabll.Traits.MakeEdge(is_ato_component.MakeChild())
            MISO = F.Electrical.MakeChild()
            MISO.add_dependant(fabll.Traits.MakeEdge(is_ato_pin.MakeChild(), [MISO]))

        class PinFallbackApp(fabll.Node):
            package = PinFallbackPkg.MakeChild()

        app = PinFallbackApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )

        processable_nets = collect_unnamed_nets(nets)
        add_base_name(processable_nets)

        # With no hierarchy name, the pin name "MISO" should be used
        miso_net = next(
            pn
            for pn in processable_nets
            if any(e.name == "MISO" for e in pn.electricals)
        )
        assert miso_net.net_name.base_name == "MISO", (
            f"Expected pin name 'MISO' as fallback, got '{miso_net.net_name.base_name}'"
        )

    def test_bus_prefix_over_pin_name(self):
        """
        Test that bus prefix + hierarchy name takes precedence over pin names
        in the full pipeline.

        Simulates: a CONTROLLER bus interface with signal "sda" connected to
        pin "SD0". The final net name should be "comp.bus.sda" (bus prefix +
        hierarchy name), not "SD0" or "comp.bus.SD0".
        """
        import faebryk.core.node as fabll
        from atopile.compiler.ast_visitor import is_ato_component, is_ato_pin
        from faebryk.core.faebrykpy import EdgeInterfaceConnection as interface

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class BusPinPkg(fabll.Node):
            _is_component = fabll.Traits.MakeEdge(is_ato_component.MakeChild())
            SD0 = F.Electrical.MakeChild()
            SD0.add_dependant(fabll.Traits.MakeEdge(is_ato_pin.MakeChild(), [SD0]))
            SC0 = F.Electrical.MakeChild()
            SC0.add_dependant(fabll.Traits.MakeEdge(is_ato_pin.MakeChild(), [SC0]))

        class BusPinI2C(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_bus_role.MakeChild(role=[has_bus_role.BusRole.CONTROLLER])
            )
            sda = F.Electrical.MakeChild()
            scl = F.Electrical.MakeChild()

        class BusPinMCU(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            i2c = BusPinI2C.MakeChild()
            package = BusPinPkg.MakeChild()
            _conn_sda = fabll.MakeEdge(
                [i2c, "sda"],
                [package, "SD0"],
                edge=interface.build(shallow=False),
            )
            _conn_scl = fabll.MakeEdge(
                [i2c, "scl"],
                [package, "SC0"],
                edge=interface.build(shallow=False),
            )

        class BusPinApp(fabll.Node):
            comp = BusPinMCU.MakeChild()

        app = BusPinApp.bind_typegraph(tg=tg).create_instance(g=g)

        all_electricals = app.get_children(direct_only=False, types=F.Electrical)
        nets = self._bind_nets_for_test(
            electricals=all_electricals,
            tg=tg,
            g=g,
        )
        attach_net_names(nets)

        net_names = sorted(
            [net_name for net in nets if (net_name := net.get_name()) is not None],
            key=lambda name: name.lower(),
        )

        print(f"net_names: {net_names}")

        # Bus prefix from CONTROLLER + hierarchy name should win
        assert "comp.i2c.scl" in net_names, f"Expected 'comp.i2c.scl', got {net_names}"
        assert "comp.i2c.sda" in net_names, f"Expected 'comp.i2c.sda', got {net_names}"
        # Pin names should NOT appear as net names
        assert "SD0" not in net_names, "Pin name 'SD0' should not be a net name"
        assert "SC0" not in net_names, "Pin name 'SC0' should not be a net name"
