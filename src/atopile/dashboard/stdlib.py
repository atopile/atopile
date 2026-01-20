"""
Standard library introspection model.

Provides data about the faebryk standard library (modules, interfaces, traits, etc.)
for the dashboard UI.
"""

import inspect
import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel

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
    children: list["StdLibChild"] = []
    enum_values: list[str] = []  # For EnumParameter types, the possible values


class StdLibItem(BaseModel):
    """A standard library item (module, interface, trait, etc.)."""

    id: str
    name: str
    type: StdLibItemType
    description: str
    usage: str | None = None
    children: list[StdLibChild] = []
    parameters: list[dict[str, str]] = []


class StdLibResponse(BaseModel):
    """Response for /api/stdlib endpoint."""

    items: list[StdLibItem]
    total: int


def _get_item_type_from_class(cls: type) -> StdLibItemType | None:
    """
    Determine the item type based on class attributes/traits.

    Returns None if the class is not a user-facing library item.
    """
    # Import here to avoid circular imports
    import faebryk.core.node as fabll

    # Check class attributes for trait markers
    # Note: these can be _EdgeField or _ChildField depending on how they're defined
    for attr_name in dir(cls):
        try:
            attr_value = getattr(cls, attr_name, None)
        except Exception:
            continue

        if attr_value is None:
            continue

        # Check for is_interface trait (usually _is_interface)
        if attr_name == "_is_interface" and isinstance(
            attr_value, (fabll._EdgeField, fabll._ChildField)
        ):
            return StdLibItemType.INTERFACE

        # Check for is_module trait (usually _is_module)
        if attr_name == "_is_module" and isinstance(
            attr_value, (fabll._EdgeField, fabll._ChildField)
        ):
            return StdLibItemType.MODULE

        # Check for is_trait marker (for trait classes)
        if attr_name == "is_trait" and isinstance(
            attr_value, (fabll._EdgeField, fabll._ChildField)
        ):
            return StdLibItemType.TRAIT

    return None


def _get_child_type_name(child_field: Any) -> str:
    """Get the type name from a child field."""
    import faebryk.core.node as fabll

    if isinstance(child_field, fabll._ChildField):
        nodetype = child_field.nodetype
        if isinstance(nodetype, str):
            return nodetype
        elif hasattr(nodetype, "__name__"):
            return nodetype.__name__
    return "Unknown"


def _get_child_item_type(type_name: str) -> StdLibItemType:
    """Determine the item type based on the type name."""
    # Import to check types
    try:
        import faebryk.library._F as F

        if hasattr(F, type_name):
            cls = getattr(F, type_name)
            item_type = _get_item_type_from_class(cls)
            if item_type:
                return item_type
    except Exception:
        pass

    # Fallback: check naming patterns
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


def _extract_children(
    cls: type, depth: int = 0, max_depth: int = 2
) -> list[StdLibChild]:
    """
    Extract children from a class definition.

    Args:
        cls: The class to introspect
        depth: Current recursion depth
        max_depth: Maximum recursion depth for nested children
    """
    import faebryk.core.node as fabll
    import faebryk.library._F as F

    children: list[StdLibChild] = []

    for attr_name, attr_value in vars(cls).items():
        # Skip private/internal attributes
        if attr_name.startswith("_"):
            continue

        # Skip non-child attributes
        if not isinstance(attr_value, (fabll._ChildField, list)):
            continue

        # Handle array children (e.g., unnamed = [F.Electrical.MakeChild()...])
        if isinstance(attr_value, list):
            if attr_value and isinstance(attr_value[0], fabll._ChildField):
                type_name = _get_child_type_name(attr_value[0])
                # Skip internal traits
                if not _is_user_facing_child(attr_name, type_name):
                    continue

                # Try to extract values from trait arrays (like net_name_suffixes)
                array_values = _extract_array_trait_values(attr_value)

                children.append(
                    StdLibChild(
                        name=f"{attr_name}[]",
                        type=f"{type_name}[{len(attr_value)}]",
                        item_type=_get_child_item_type(type_name),
                        children=[],
                        enum_values=array_values,
                    )
                )
            continue

        # Handle single child fields
        if isinstance(attr_value, fabll._ChildField):
            type_name = _get_child_type_name(attr_value)

            # Skip internal traits
            if not _is_user_facing_child(attr_name, type_name):
                continue

            item_type = _get_child_item_type(type_name)

            # Recursively get nested children (but limit depth)
            nested_children: list[StdLibChild] = []
            if depth < max_depth and hasattr(F, type_name):
                try:
                    nested_cls = getattr(F, type_name)
                    nested_children = _extract_children(
                        nested_cls, depth + 1, max_depth
                    )
                except Exception:
                    pass

            # Extract enum values for EnumParameter types
            enum_values: list[str] = []
            if type_name == "EnumParameter":
                enum_values = _extract_enum_values(cls, attr_name)

            children.append(
                StdLibChild(
                    name=attr_name,
                    type=type_name,
                    item_type=item_type,
                    children=nested_children,
                    enum_values=enum_values,
                )
            )

    return children


def _extract_usage_example(cls: type) -> str | None:
    """
    Extract usage example from has_usage_example trait if present.

    The usage example is stored in the class's usage_example trait, which is defined
    using fabll.Traits.MakeEdge with F.has_usage_example.MakeChild(example=...).

    We extract the example by parsing the source code of the class definition,
    as the runtime structure is complex and hard to introspect directly.
    """
    import re

    try:
        source = inspect.getsource(cls)
    except (OSError, TypeError):
        return None

    # First check if this class has has_usage_example at all
    if "has_usage_example" not in source:
        return None

    # Look for usage_example definition with the example string
    # The format is: F.has_usage_example.MakeChild(\n    example="""...""",
    # We use a two-step approach:
    # 1. Find the has_usage_example.MakeChild section
    # 2. Extract the example= argument value

    # Pattern to find MakeChild section and capture everything until the closing paren
    makechild_pattern = r"has_usage_example\.MakeChild\(([\s\S]*?)\)\.put_on_type\(\)"
    makechild_match = re.search(makechild_pattern, source)

    if not makechild_match:
        # Try without .put_on_type()
        makechild_pattern = r"has_usage_example\.MakeChild\(([\s\S]*?)\)"
        makechild_match = re.search(makechild_pattern, source)

    if makechild_match:
        args_content = makechild_match.group(1)

        # Now extract the example= value from the args
        # Pattern for triple-quoted strings
        example_patterns = [
            r'example\s*=\s*"""([\s\S]*?)"""',
            r"example\s*=\s*'''([\s\S]*?)'''",
            r'example\s*=\s*"([^"]*)"',
            r"example\s*=\s*'([^']*)'",
        ]

        for pattern in example_patterns:
            example_match = re.search(pattern, args_content)
            if example_match:
                example = example_match.group(1)
                # Clean up the example text
                lines = example.strip().split("\n")
                # Remove common leading whitespace (dedent)
                if lines:
                    # Find minimum indentation (excluding empty lines)
                    min_indent = float("inf")
                    for line in lines:
                        if line.strip():
                            indent = len(line) - len(line.lstrip())
                            min_indent = min(min_indent, indent)
                    if min_indent < float("inf"):
                        lines = [
                            line[int(min_indent) :] if len(line) >= min_indent else line
                            for line in lines
                        ]
                    return "\n".join(lines).strip()

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
    Introspect the faebryk standard library and return structured data.

    Returns a list of StdLibItem objects representing all user-facing
    modules, interfaces, and traits in the library.
    """
    import faebryk.library._F as F

    items: list[StdLibItem] = []

    # Get all exported names
    all_names = F.__all__

    for name in all_names:
        try:
            obj = getattr(F, name, None)
            if obj is None:
                continue

            # Skip modules (like Collections, Units, etc.) - we want classes
            if inspect.ismodule(obj):
                continue

            # Skip if not a class
            if not inspect.isclass(obj):
                continue

            # Determine item type
            item_type = _get_item_type_from_class(obj)
            if item_type is None:
                # Check if it looks like a trait by naming convention
                if (
                    name.startswith("has_")
                    or name.startswith("is_")
                    or name.startswith("can_")
                ):
                    item_type = StdLibItemType.TRAIT
                else:
                    continue  # Skip unknown types

            # Extract children (using configurable depth)
            max_depth = STDLIB_CONFIG.get("max_children_depth", 2)
            children = _extract_children(obj, depth=0, max_depth=max_depth)

            # Extract usage example
            usage = _extract_usage_example(obj)

            # Build the item
            item = StdLibItem(
                id=name,
                name=name,
                type=item_type,
                description=_get_docstring(obj, item_type),
                usage=usage,
                children=children,
            )

            items.append(item)

        except Exception as e:
            log.warning(f"Failed to introspect {name}: {e}")
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
    global _library_cache

    # Update config if max_depth is provided
    if max_depth is not None:
        current_depth = STDLIB_CONFIG.get("max_children_depth", 2)
        if max_depth != current_depth:
            STDLIB_CONFIG["max_children_depth"] = max_depth
            force_refresh = True  # Force refresh when depth changes

    if _library_cache is None or force_refresh:
        log.info("Loading standard library data...")
        _library_cache = introspect_library()
        log.info(f"Loaded {len(_library_cache)} standard library items")

    return _library_cache
