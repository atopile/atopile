"""
Standard library introspection model.

Provides data about the faebryk standard library (modules, interfaces, traits, etc.)
for the dashboard UI.
"""

import inspect
import logging
import textwrap
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Configuration for library introspection
# Can be modified before calling get_standard_library()
STDLIB_CONFIG = {
    "max_children_depth": 2,  # Maximum depth for nested children (0 = no nesting)
}


class StdLibItemType(str, Enum):
    """Type of standard library item."""

    INTERFACE = "interface"
    MODULE = "module"
    COMPONENT = "component"
    TRAIT = "trait"
    PARAMETER = "parameter"


class StdLibChild(BaseModel):
    """A child field within a standard library item."""

    name: str
    type: str  # The type name (e.g., "Electrical", "ElectricLogic")
    item_type: StdLibItemType  # Whether it's interface, parameter, etc.
    children: list["StdLibChild"] = Field(default_factory=list)
    enum_values: list[str] = Field(default_factory=list)


class StdLibItem(BaseModel):
    """A standard library item (module, interface, trait, etc.)."""

    id: str
    name: str
    type: StdLibItemType
    description: str
    usage: str | None = None
    children: list[StdLibChild] = Field(default_factory=list)
    parameters: list[dict[str, str]] = Field(default_factory=list)


class StdLibResponse(BaseModel):
    """Response for /api/stdlib endpoint."""

    items: list[StdLibItem]
    total: int


_stdlib_typegraph_cache: (
    tuple[
        "graph.GraphView",
        "fbrk.TypeGraph",
        dict[str, type["fabll.Node"]],
        dict[str, "graph.BoundNode"],
    ]
    | None
) = None


def _get_stdlib_typegraph_cache() -> tuple[
    "graph.GraphView",
    "fbrk.TypeGraph",
    dict[str, type["fabll.Node"]],
    dict[str, "graph.BoundNode"],
]:
    """Build and cache a stdlib TypeGraph for introspection."""
    global _stdlib_typegraph_cache
    if _stdlib_typegraph_cache is not None:
        return _stdlib_typegraph_cache

    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.graph as graph
    import faebryk.core.node as fabll
    from atopile.compiler.ast_visitor import STDLIB_ALLOWLIST

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    type_map: dict[str, type[fabll.Node]] = {}
    type_nodes: dict[str, graph.BoundNode] = {}

    for obj in STDLIB_ALLOWLIST:
        name = obj.__name__
        try:
            type_node = fabll.TypeNodeBoundTG.get_or_create_type_in_tg(tg, obj)
        except Exception as exc:
            log.warning("Failed to create typegraph node for %s: %s", name, exc)
            continue
        type_map[name] = obj
        type_nodes[name] = type_node

    _stdlib_typegraph_cache = (g, tg, type_map, type_nodes)
    return _stdlib_typegraph_cache


def get_stdlib_watch_paths() -> list[Path]:
    """Return filesystem paths for stdlib allowlist types."""
    from atopile.compiler.ast_visitor import STDLIB_ALLOWLIST

    paths: set[Path] = set()
    for obj in STDLIB_ALLOWLIST:
        try:
            source = inspect.getsourcefile(obj)
        except Exception:
            source = None
        if source:
            paths.add(Path(source))
    return sorted(paths)


def _get_item_type_from_typegraph(
    tg: "fbrk.TypeGraph",
    type_node: "graph.BoundNode | None",
    type_name: str,
) -> StdLibItemType | None:
    """Determine item type using the TypeGraph when possible."""
    import faebryk.core.node as fabll
    import faebryk.library._F as F

    if type_node is not None:
        if fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
            type_node, fabll.is_interface
        ):
            return StdLibItemType.INTERFACE
        if fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
            type_node, fabll.is_module
        ):
            return StdLibItemType.MODULE
        if fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
            type_node, F.Parameters.is_parameter
        ):
            return StdLibItemType.PARAMETER
        if fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
            type_node, fabll.ImplementsTrait
        ):
            return StdLibItemType.TRAIT

    if type_name.startswith(("has_", "is_", "can_")):
        return StdLibItemType.TRAIT

    return None


def _get_child_item_type(
    tg: "fbrk.TypeGraph",
    type_node: "graph.BoundNode | None",
    type_name: str,
) -> StdLibItemType:
    """Determine child item type with TypeGraph fallback."""
    item_type = _get_item_type_from_typegraph(tg, type_node, type_name)
    if item_type:
        return item_type

    if "Parameter" in type_name or type_name in ("ohm", "V", "A", "F", "H", "Hz", "W"):
        return StdLibItemType.PARAMETER
    return StdLibItemType.INTERFACE


def _extract_enum_values(parent_cls: type, attr_name: str) -> list[str]:
    """
    Extract enum values for an EnumParameter.

    For a parameter like `doping_type` on class `BJT`, the enum is typically
    defined as a nested class like `BJT.DopingType`.
    """
    # Convert snake_case to CamelCase for the enum class name
    # e.g., "doping_type" -> "DopingType"
    parts = attr_name.split("_")
    enum_class_name = "".join(part.capitalize() for part in parts)

    # Try to find the enum class as a nested class of the parent
    enum_cls = getattr(parent_cls, enum_class_name, None)

    if (
        enum_cls is not None
        and isinstance(enum_cls, type)
        and issubclass(enum_cls, Enum)
    ):
        # Return the enum member names
        return [member.name for member in enum_cls]

    return []


def _extract_array_trait_values(items: list) -> list[str]:
    """
    Extract string values from array trait children.

    For arrays like `net_name_suffixes`, the values are stored deep in the
    dependants chain as StringAttributes. This function extracts them.
    """
    values: list[str] = []

    for item in items:
        if not hasattr(item, "_dependants"):
            continue

        # Navigate through the dependant chain to find string values
        for dep in item._dependants:
            if not hasattr(dep, "_prepend_dependants"):
                continue

            for pre_dep in dep._prepend_dependants:
                # Look for Strings literal in prepend_dependants
                if not hasattr(pre_dep, "nodetype"):
                    continue

                nodetype_name = getattr(pre_dep.nodetype, "__name__", "")
                if nodetype_name != "Strings":
                    continue

                # The actual string value is in the Strings' prepend_dependants
                if hasattr(pre_dep, "_prepend_dependants"):
                    for string_dep in pre_dep._prepend_dependants:
                        if hasattr(string_dep, "attributes"):
                            attrs = string_dep.attributes
                            if hasattr(attrs, "value") and attrs.value:
                                values.append(str(attrs.value))

    return values


def _is_user_facing_child(attr_name: str, type_name: str) -> bool:
    """
    Determine if an attribute is a user-facing child (vs internal trait/edge).

    User-facing children are interfaces/parameters users interact with.
    Internal attributes include trait markers, design checks, net names, etc.
    """
    if attr_name.startswith("_"):
        return False

    # Skip common internal/trait attribute names
    internal_names = {
        "can_bridge",
        "net_names",
        "bus_parameters",
        "usage_example",
        "design_check",
        "designator_prefix",
        "lead",
        # Loop variable leaks in class definition
        "e",
        "c",
        "r",
        # Deprecated aliases
        "vcc",
        "gnd",
    }
    if attr_name in internal_names:
        return False

    # Skip common trait types
    trait_types = {
        "can_bridge",
        "has_net_name_suggestion",
        "is_alias_bus_parameter",
        "is_sum_bus_parameter",
        "has_usage_example",
        "implements_design_check",
        "has_designator_prefix",
        "is_lead",
        "can_attach_to_any_pad",
    }
    if type_name in trait_types:
        return False

    return True


def _extract_children_from_typegraph(
    cls: type,
    tg: "fbrk.TypeGraph",
    type_node: "graph.BoundNode",
    depth: int = 0,
    max_depth: int = 2,
) -> list[StdLibChild]:
    """Extract children from the TypeGraph for a given type node."""
    import faebryk.core.faebrykpy as fbrk

    children: list[StdLibChild] = []

    try:
        make_children = tg.collect_make_children(type_node=type_node)
    except Exception as exc:
        log.warning("Failed to collect make children for %s: %s", cls.__name__, exc)
        return children

    for identifier, make_child in make_children:
        if not identifier:
            continue
        if identifier.startswith("anon"):
            continue
        if not _is_user_facing_child(identifier, ""):
            continue

        type_ref = tg.get_make_child_type_reference(make_child=make_child)
        resolved_type = fbrk.Linker.get_resolved_type(type_reference=type_ref)
        if resolved_type is not None:
            type_name = fbrk.TypeGraph.get_type_name(type_node=resolved_type)
        else:
            type_name = fbrk.TypeGraph.get_type_reference_identifier(
                type_reference=type_ref
            )

        # Skip internal traits after resolving type name.
        if not _is_user_facing_child(identifier, type_name):
            continue

        nested_children: list[StdLibChild] = []
        if resolved_type is not None and depth < max_depth:
            nested_children = _extract_children_from_typegraph(
                cls=cls,
                tg=tg,
                type_node=resolved_type,
                depth=depth + 1,
                max_depth=max_depth,
            )

        enum_values: list[str] = []
        if type_name == "EnumParameter":
            enum_values = _extract_enum_values(cls, identifier)

        children.append(
            StdLibChild(
                name=identifier,
                type=type_name,
                item_type=_get_child_item_type(tg, resolved_type, type_name),
                children=nested_children,
                enum_values=enum_values,
            )
        )

    return children


def _extract_usage_example(cls: type, tg: "fbrk.TypeGraph | None") -> str | None:
    """Extract usage example from has_usage_example trait using the TypeGraph."""
    if tg is None:
        return None

    try:
        import faebryk.library._F as F

        type_bound = cls.bind_typegraph(tg)
        usage_trait = type_bound.try_get_type_trait(F.has_usage_example)
        if usage_trait is None:
            return None
        return textwrap.dedent(usage_trait.example).strip()
    except Exception as exc:
        log.debug("Failed to get usage example for %s: %s", cls.__name__, exc)
        return None


def _get_docstring(cls: type, item_type: StdLibItemType | None = None) -> str:
    """
    Get a description for a class, using docstring or generating one.

    Falls back to contextual descriptions based on item type and naming.
    """
    # Get only the directly defined docstring, not inherited ones
    doc = getattr(cls, "__doc__", None)
    if doc and not doc.startswith("Abstract base class"):
        cleaned = doc.strip()
        if cleaned and cleaned.lower() != cls.__name__.lower():
            return cleaned

    # Generate description based on item type and name
    name = cls.__name__

    # Trait descriptions based on naming conventions
    if item_type == StdLibItemType.TRAIT:
        if name.startswith("has_"):
            trait_name = name[4:].replace("_", " ")
            return f"Trait indicating that a module has {trait_name}."
        elif name.startswith("is_"):
            trait_name = name[3:].replace("_", " ")
            return f"Trait marking a node as {trait_name}."
        elif name.startswith("can_"):
            trait_name = name[4:].replace("_", " ")
            return f"Trait enabling {trait_name} capability."

    # Interface descriptions
    if item_type == StdLibItemType.INTERFACE:
        if name == "Electrical":
            return (
                "Base electrical connection point. Represents a single electrical node."
            )
        elif name == "ElectricPower":
            return "Power supply interface with high (hv) and low (lv) voltage rails."
        elif name == "ElectricLogic":
            return "Digital logic signal with line and reference power."
        elif name == "ElectricSignal":
            return "Electrical signal with associated reference."
        elif name in ("I2C", "SPI", "UART", "I2S", "CAN", "USB_C", "SWD", "JTAG"):
            return f"{name} communication interface."
        elif "Pair" in name:
            return (
                f"Differential pair interface for {name.replace('Pair', '')} signals."
            )
        else:
            return f"Interface type for {name.replace('_', ' ')} connections."

    # Module descriptions
    if item_type == StdLibItemType.MODULE:
        # Common passive components
        if name == "Resistor":
            return (
                "Generic resistor with automatic part selection based on constraints."
            )
        elif name == "Capacitor":
            return "Generic capacitor with automatic part selection."
        elif name == "Inductor":
            return "Generic inductor with automatic part selection."
        elif name == "Diode":
            return "Generic diode with forward voltage and current parameters."
        elif name == "LED":
            return "Light-emitting diode with color and forward voltage parameters."
        elif name.startswith("Resistor") or name.endswith("Resistor"):
            suffix = name.replace("Resistor", "").replace("_", " ").strip()
            return f"Specialized resistor: {suffix}."
        elif name.startswith("Capacitor") or name.endswith("Capacitor"):
            suffix = name.replace("Capacitor", "").replace("_", " ").strip()
            return f"Specialized capacitor: {suffix}."
        # Transistors
        elif name == "MOSFET":
            return "Metal-oxide-semiconductor field-effect transistor."
        elif name == "BJT":
            return "Bipolar junction transistor."
        # Others
        elif name == "Crystal":
            return "Crystal oscillator component for clock generation."
        elif name == "Fuse":
            return "Protective fuse with trip current parameter."
        elif name == "Battery":
            return "Battery power source with voltage and capacity parameters."
        elif name == "OpAmp":
            return "Operational amplifier module."
        elif name == "Comparator":
            return "Analog voltage comparator module."
        elif name == "TestPoint":
            return "Test point for debugging and measurement."
        elif name == "MountingHole":
            return "PCB mounting hole for mechanical attachment."
        elif name == "NetTie":
            return "Net tie for connecting separate nets."
        elif "Filter" in name:
            suffix = name.replace("Filter", "").replace("_", " ").strip()
            return f"Signal filter: {suffix}."
        elif "Array" in name:
            base = name.replace("Array", "").replace("_", " ").strip()
            return f"Array of {base}s in a single package."
        elif "Multi" in name:
            base = name.replace("Multi", "").replace("_", " ").strip()
            return f"Multi-channel {base} interface."
        else:
            return f"Module: {name.replace('_', ' ')}."

    # Component descriptions
    if item_type == StdLibItemType.COMPONENT:
        return f"Component: {name.replace('_', ' ')}."

    # Default fallback
    return f"{name} - No description available."


def introspect_library() -> list[StdLibItem]:
    """
    Introspect the faebryk standard library via the TypeGraph.

    Returns a list of StdLibItem objects representing all user-facing
    modules, interfaces, and traits in the library.
    """
    items: list[StdLibItem] = []

    g, tg, type_map, type_nodes = _get_stdlib_typegraph_cache()
    max_depth = STDLIB_CONFIG.get("max_children_depth", 2)

    for name, obj in type_map.items():
        try:
            type_node = type_nodes.get(name)
            item_type = _get_item_type_from_typegraph(tg, type_node, obj.__name__)
            if item_type is None:
                continue

            children = []
            if type_node is not None:
                children = _extract_children_from_typegraph(
                    cls=obj,
                    tg=tg,
                    type_node=type_node,
                    depth=0,
                    max_depth=max_depth,
                )

            usage = _extract_usage_example(obj, tg)

            items.append(
                StdLibItem(
                    id=name,
                    name=name,
                    type=item_type,
                    description=_get_docstring(obj, item_type),
                    usage=usage,
                    children=children,
                )
            )
        except Exception as exc:
            log.warning("Failed to introspect %s: %s", name, exc)
            continue

    return items


# Cache for library data (loaded once on first request)
_library_cache: list[StdLibItem] | None = None


def get_standard_library(
    force_refresh: bool = False,
    max_depth: int | None = None,
) -> list[StdLibItem]:
    """
    Get the standard library data, using cached values when available.

    Args:
        force_refresh: If True, reload the library data even if cached.
        max_depth: Maximum depth for nested children. If provided, updates
            STDLIB_CONFIG and forces a refresh. Use 0 for no nesting,
            1 for one level, 2 (default) for two levels, etc.

    Returns:
        List of standard library items.
    """
    global _library_cache, _stdlib_typegraph_cache

    # Update config if max_depth is provided
    if max_depth is not None:
        current_depth = STDLIB_CONFIG.get("max_children_depth", 2)
        if max_depth != current_depth:
            STDLIB_CONFIG["max_children_depth"] = max_depth
            force_refresh = True  # Force refresh when depth changes

    if _library_cache is None or force_refresh:
        log.info("Loading standard library data...")
        _stdlib_typegraph_cache = None
        _library_cache = introspect_library()
        log.info(f"Loaded {len(_library_cache)} standard library items")

    return _library_cache


def refresh_standard_library(
    max_depth: int | None = None,
) -> list[StdLibItem]:
    """Clear stdlib caches and rebuild."""
    global _library_cache, _stdlib_typegraph_cache
    _library_cache = None
    _stdlib_typegraph_cache = None
    return get_standard_library(force_refresh=True, max_depth=max_depth)
