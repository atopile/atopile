# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
JSON Variables/Parameters exporter for the VSCode extension.

Generates a rich JSON output with hierarchical module/parameter data
for the extension's VariablesPanel.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver

logger = logging.getLogger(__name__)


# Variable types matching the VariablesPanel.tsx types
VariableType = Literal[
    "voltage",
    "current",
    "resistance",
    "capacitance",
    "ratio",
    "frequency",
    "power",
    "percentage",
    "dimensionless",
]

# Source of the variable value
VariableSource = Literal["user", "derived", "picked", "datasheet"]


@dataclass
class Variable:
    """A single variable/parameter with its spec and actual values."""

    name: str
    spec: str | None = None
    specTolerance: str | None = None
    actual: str | None = None
    actualTolerance: str | None = None
    unit: str | None = None
    type: VariableType = "dimensionless"
    meetsSpec: bool | None = None
    source: VariableSource = "derived"


@dataclass
class VariableNode:
    """A node in the hierarchical variable tree."""

    name: str
    type: Literal["module", "interface", "component"]
    path: str  # Atopile address (hierarchical from app root)
    typeName: str | None = None  # The type name (e.g., "I2C", "SPI", "Resistor")
    variables: list[Variable] = field(default_factory=list)
    children: list["VariableNode"] = field(default_factory=list)


@dataclass
class JSONVariablesOutput:
    """The full JSON variables output."""

    version: str = "1.0"
    nodes: list[VariableNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def _get_variable_type_from_unit(unit_str: str | None) -> VariableType:
    """Map unit symbol to variable type."""
    if not unit_str:
        return "dimensionless"

    unit_lower = unit_str.lower()

    # Voltage
    if unit_lower in ("v", "mv", "µv", "uv", "kv"):
        return "voltage"
    # Current
    if unit_lower in ("a", "ma", "µa", "ua", "na", "pa"):
        return "current"
    # Resistance (ohm symbol variants)
    if any(r in unit_lower for r in ("ω", "ohm", "kohm", "kω", "mω", "mohm")):
        return "resistance"
    # Capacitance
    if unit_lower in ("f", "pf", "nf", "µf", "uf", "mf"):
        return "capacitance"
    # Frequency
    if unit_lower in ("hz", "khz", "mhz", "ghz"):
        return "frequency"
    # Power
    if unit_lower in ("w", "mw", "µw", "uw", "kw"):
        return "power"
    # Percentage
    if unit_lower in ("%", "percent"):
        return "percentage"

    # Check for SI base unit patterns
    if "s⁻³·m²·kg" in unit_str and "a⁻²" in unit_str.lower():
        return "resistance"
    if "s⁻³·m²·kg" in unit_str and "a⁻¹" in unit_str.lower():
        return "voltage"
    if "s⁴·m⁻²·kg⁻¹" in unit_str:
        return "capacitance"

    return "dimensionless"


def _get_node_type(module: fabll.Node) -> Literal["module", "interface", "component"]:
    """Determine the type of node for display."""
    # Check if it's pickable (component)
    if module.has_trait(F.Pickable.is_pickable):
        return "component"

    # Check if it has the is_interface trait
    if module.has_trait(fabll.is_interface):
        return "interface"

    # Check type name for interface patterns
    try:
        type_node = module.get_type_node()
        if type_node:
            # Handle both Node and BoundNodeReference
            if hasattr(type_node, "get_name"):
                type_name = type_node.get_name()
            elif hasattr(type_node, "name"):
                type_name = type_node.name
            else:
                type_name = str(type_node)

            if type_name:
                type_lower = type_name.lower()
                if "interface" in type_lower or type_name.endswith("Power"):
                    return "interface"
                # Common interface names
                if type_name in (
                    "I2C",
                    "SPI",
                    "UART",
                    "GPIO",
                    "ElectricPower",
                    "Electrical",
                ):
                    return "interface"
    except Exception:
        pass

    return "module"


def _get_source_type(module: fabll.Node) -> VariableSource:
    """Determine how the parameter value was set for this module."""
    # Check if there's a has_part_picked trait (means part was picked)
    if module.has_trait(F.Pickable.has_part_picked):
        return "picked"

    # Check if the module was parametrically picked
    if module.has_trait(F.Pickable.is_pickable_by_type):
        return "picked"

    # Check if explicitly specified by supplier ID
    if module.has_trait(F.Pickable.is_pickable_by_supplier_id):
        return "datasheet"

    return "derived"


def _extract_tolerance_from_value(value_str: str) -> tuple[str, str | None, str | None]:
    """
    Extract the base value, tolerance, and unit from a value string.

    Examples:
        "10 ± 1%" -> ("10", "±1%", None)
        "10kohm +/- 5%" -> ("10", "±5%", "kohm")
        "1±20.0%F" -> ("1", "±20.0%", "F")
        "5V" -> ("5", None, "V")
        "{8000..12000}Ω" -> ("{8000..12000}", None, "Ω")

    Returns:
        (base_value, tolerance, unit)
    """
    import re

    if not value_str:
        return value_str, None, None

    # Common unit symbols to extract from the end
    unit_pattern = (
        r"([VAFΩΩΩΩS W Hz J N Pa C T H]|"
        r"[kKmMµunpfGT][VAFΩΩS W Hz J N Pa C T H]|"
        r"ohm|kohm|Mohm|mol|rad|sr|kg|cd)$"
    )

    # First extract unit from the end (if present)
    unit_match = re.search(unit_pattern, value_str)
    unit = None
    value_without_unit = value_str
    if unit_match:
        unit = unit_match.group(1)
        value_without_unit = value_str[: unit_match.start()]

    # Look for ± or +/- patterns
    for sep in ("±", " ± ", " +/- ", "+/-"):
        if sep in value_without_unit:
            parts = value_without_unit.split(sep, 1)
            base = parts[0].strip()
            tol_part = parts[1].strip()
            # Re-extract unit from tolerance part if not already found
            if not unit:
                tol_unit_match = re.search(unit_pattern, tol_part)
                if tol_unit_match:
                    unit = tol_unit_match.group(1)
                    tol_part = tol_part[: tol_unit_match.start()]
            tol = "±" + tol_part
            # Append unit to base if found
            if unit:
                base = base + unit
            return base, tol, unit

    # No tolerance found, return base with unit
    if unit:
        return value_without_unit + unit, None, unit
    return value_str, None, None


def _is_unconstrained_value(value_str: str) -> bool:
    """
    Check if a value represents an unconstrained/any value.

    These patterns indicate the parameter wasn't constrained to a specific value:
    - "any of N" (enum with all options available)
    - "any" (unconstrained number)
    - "any ≥0" (unconstrained positive number)
    - "{any}" or "{any ...}" (unconstrained with units)
    """
    if not value_str:
        return True

    value_lower = value_str.lower().strip()

    # Check for "any of N" pattern (unconstrained enum)
    if value_lower.startswith("any of "):
        return True

    # Check for "any" patterns (unconstrained numbers)
    if value_lower in ("any", "{any}"):
        return True

    # Check for "any ≥0" or similar
    if value_lower.startswith("any "):
        return True

    # Check for "{any ...}" patterns with units
    if value_lower.startswith("{any"):
        return True

    return False


def _extract_module_data(
    module: fabll.Node,
    solver: Solver,
    app_root: fabll.Node,
) -> tuple[
    str, str, str | None, Literal["module", "interface", "component"], list[Variable]
]:
    """
    Extract data from a single module.

    Returns: (name, path, typeName, nodeType, variables)
    """
    # Get the instance name (last component of hierarchy)
    name = module.get_name(accept_no_parent=True)

    # Get full hierarchical path from root using get_full_name
    # This gives paths like "app.ad1938_driver.i2c_ins[0]"
    full_path = module.get_full_name(types=False, include_uuid=False)

    # Make path relative to app root by removing the app root prefix
    app_prefix = app_root.get_full_name(types=False, include_uuid=False)
    if full_path.startswith(app_prefix + "."):
        path = full_path[len(app_prefix) + 1 :]
    elif full_path == app_prefix:
        # This is the app root itself
        path = name
    else:
        path = full_path

    # Get the type name (e.g., "I2C", "SPI", "Resistor", "AD1938_driver")
    type_name = module.get_type_name()
    # Clean up type name - remove file prefix if present
    if type_name and "::" in type_name:
        type_name = type_name.split("::")[-1]

    node_type = _get_node_type(module)
    module_source = _get_source_type(module)

    # Extract parameters
    variables: list[Variable] = []
    param_nodes = module.get_children(
        direct_only=True,
        types=fabll.Node,
        include_root=True,
        required_trait=F.Parameters.is_parameter,
    )

    for param in param_nodes:
        try:
            param_name = param.get_full_name().split(".")[-1]

            # Skip anonymous parameters
            if param_name.startswith("anon"):
                continue

            param_trait = param.get_trait(F.Parameters.is_parameter)

            # Get the solved value
            value_set = solver.extract_superset(param_trait)
            value_str = value_set.pretty_str()

            # Extract tolerance and unit from the value string
            base_value, tolerance, extracted_unit = _extract_tolerance_from_value(
                value_str
            )

            # Get unit - prefer the one from the parameter trait, fall back to extracted
            unit_str = None
            try:
                unit = param_trait.try_get_units()
                if unit:
                    unit_str = F.Units.is_unit.compact_repr(unit)
            except Exception:
                pass

            # Use extracted unit if we couldn't get one from the trait
            if not unit_str and extracted_unit:
                unit_str = extracted_unit

            # Determine variable type from unit
            var_type = _get_variable_type_from_unit(unit_str)

            # For picked/datasheet params, check if value is actually constrained
            if module_source in ("picked", "datasheet"):
                # Check if the value is still unconstrained after picking
                # If so, the picked component doesn't specify this attribute
                is_constrained = not _is_unconstrained_value(base_value)

                if is_constrained:
                    # Component specifies this attribute - show as actual
                    variables.append(
                        Variable(
                            name=param_name,
                            spec=base_value,
                            specTolerance=tolerance,
                            actual=base_value,
                            actualTolerance=tolerance,
                            unit=unit_str,
                            type=var_type,
                            meetsSpec=True,
                            source=module_source,
                        )
                    )
                else:
                    # Component doesn't specify this attribute - no actual value
                    variables.append(
                        Variable(
                            name=param_name,
                            spec=base_value,
                            specTolerance=tolerance,
                            actual=None,
                            actualTolerance=None,
                            unit=unit_str,
                            type=var_type,
                            meetsSpec=None,
                            source=module_source,
                        )
                    )
            else:
                # For derived params, we only have the spec
                variables.append(
                    Variable(
                        name=param_name,
                        spec=base_value,
                        specTolerance=tolerance,
                        unit=unit_str,
                        type=var_type,
                        source="derived",
                    )
                )

        except Exception as e:
            logger.debug(f"Could not extract parameter {param}: {e}")
            continue

    return name, path, type_name, node_type, variables


def _parse_module_locator(locator: str) -> list[str]:
    """
    Parse a module locator into its hierarchical path components.

    Handles formats like:
    - "adi-adxl375.ato::ADI_ADXL375.decoupling_capacitors[0]|Capacitor"
        -> ["ADI_ADXL375", "decoupling_capacitors", "[0]"]
    - "power" -> ["power"]
    - "i2c" -> ["i2c"]
    - "App.i2c_ins[0].scl" -> ["App", "i2c_ins", "[0]", "scl"]

    Array indices are split into separate path components so that
    array elements are nested under their container.
    """
    import re

    # Remove type suffix if present (after |)
    if "|" in locator:
        locator = locator.split("|")[0]

    # Extract the path after :: if present
    if "::" in locator:
        locator = locator.split("::")[1]

    # Split by . to get hierarchy
    parts = locator.split(".")

    # Further split array indices into separate components
    # e.g., "i2c_ins[0]" -> ["i2c_ins", "[0]"]
    expanded_parts = []
    for part in parts:
        # Check if part contains array indices
        if "[" in part and "]" in part:
            # Split "name[0][1]" into ["name", "[0]", "[1]"]
            match = re.match(r"^([^\[]+)((?:\[\d+\])+)$", part)
            if match:
                base_name = match.group(1)
                indices_str = match.group(2)
                # Extract all indices
                indices = re.findall(r"\[\d+\]", indices_str)
                expanded_parts.append(base_name)
                expanded_parts.extend(indices)
            else:
                # Fallback - just add the part as-is
                expanded_parts.append(part)
        else:
            expanded_parts.append(part)

    return expanded_parts


def _build_tree(flat_nodes: dict[str, VariableNode]) -> list[VariableNode]:
    """
    Build a tree structure from flat nodes based on path hierarchy.

    Creates intermediate placeholder nodes when a container (like i2c_ins)
    doesn't have its own entry but its children (like i2c_ins[0]) do.
    """
    # Parse all paths into their hierarchical components
    parsed_paths: dict[str, list[str]] = {}
    for path in flat_nodes:
        parsed_paths[path] = _parse_module_locator(path)

    # Collect all unique hierarchy prefixes that we need nodes for
    # This ensures containers exist even if they don't have parameters
    all_keys: set[str] = set()
    for parts in parsed_paths.values():
        for i in range(1, len(parts) + 1):
            all_keys.add(".".join(parts[:i]))

    # Create a mapping from hierarchy key to original path (if it exists)
    hierarchy_key_to_path: dict[str, str] = {}
    for path, parts in parsed_paths.items():
        key = ".".join(parts)
        hierarchy_key_to_path[key] = path

    # Sort keys by length (shorter = parent) then alphabetically
    sorted_keys = sorted(all_keys, key=lambda x: (len(x.split(".")), x))

    root_nodes: list[VariableNode] = []
    key_to_node: dict[str, VariableNode] = {}

    for key in sorted_keys:
        parts = key.split(".")

        # Check if we have an actual node for this key
        if key in hierarchy_key_to_path:
            path = hierarchy_key_to_path[key]
            node = flat_nodes[path]
        else:
            # Create a placeholder node for this intermediate container
            # The name is the last part of the key
            name = parts[-1]
            # Determine type: if name looks like [N], it's likely an array element
            if name.startswith("[") and name.endswith("]"):
                node_type = "module"  # Array elements inherit parent type conceptually
            else:
                node_type = "interface"  # Containers are typically interfaces
            node = VariableNode(
                name=name,
                type=node_type,
                path=key,  # Use hierarchy key as path for placeholders
                typeName=None,  # No type info for placeholders
                variables=[],
                children=[],
            )

        key_to_node[key] = node

        # Try to find a parent by removing the last component
        if len(parts) > 1:
            parent_key = ".".join(parts[:-1])
            if parent_key in key_to_node:
                key_to_node[parent_key].children.append(node)
            else:
                # Shouldn't happen since we process in order, but fallback to root
                root_nodes.append(node)
        else:
            root_nodes.append(node)

    return root_nodes


def make_json_variables(
    app: fabll.Node,
    solver: Solver,
) -> JSONVariablesOutput:
    """
    Generate a JSON variables report from the application module tree.

    Walks the module hierarchy and extracts parameters with their
    spec values, actual values (from picked parts), units, and sources.
    """
    # Get all modules
    modules = list(
        app.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=fabll.is_module,
            include_root=True,
        )
    )

    # Also get interfaces (which can have parameters like voltage, current, etc.)
    interfaces = list(
        app.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=fabll.is_interface,
            include_root=False,
        )
    )

    # Combine and deduplicate (some nodes might have both traits)
    all_nodes = {id(n): n for n in modules + interfaces}

    logger.info(
        f"JSON Variables: Found {len(modules)} modules, {len(interfaces)} interfaces"
    )

    # Extract data from each node (module or interface)
    # We need ALL nodes for tree building, even those without parameters
    flat_nodes: dict[str, VariableNode] = {}
    nodes_with_params: set[str] = set()
    total_params = 0

    for module in all_nodes.values():
        try:
            name, path, type_name, node_type, variables = _extract_module_data(
                module, solver, app
            )
            total_params += len(variables)

            # Store all nodes for tree building
            flat_nodes[path] = VariableNode(
                name=name,
                type=node_type,
                path=path,
                typeName=type_name,
                variables=variables,
                children=[],
            )

            if variables:
                nodes_with_params.add(path)
        except Exception as e:
            logger.debug(f"Could not process module {module}: {e}")
            continue

    logger.info(
        f"JSON Variables: {len(flat_nodes)} total nodes, "
        f"{len(nodes_with_params)} with params, {total_params} total params"
    )

    # Build tree structure
    root_nodes = _build_tree(flat_nodes)

    # Prune nodes without parameters (unless they have children with params)
    def prune_empty_nodes(nodes: list[VariableNode]) -> list[VariableNode]:
        result = []
        for node in nodes:
            # Recursively prune children first
            node.children = prune_empty_nodes(node.children)

            # Keep node if it has parameters or has children
            if node.variables or node.children:
                result.append(node)

        return result

    pruned_roots = prune_empty_nodes(root_nodes)

    logger.info(f"JSON Variables: Built tree with {len(pruned_roots)} root nodes")

    return JSONVariablesOutput(nodes=pruned_roots)


def write_json_variables(
    app: fabll.Node,
    solver: Solver,
    path: Path,
) -> None:
    """Write a JSON variables report to a file."""
    if not path.parent.exists():
        os.makedirs(path.parent)

    output = make_json_variables(app, solver)

    with open(path, "w", encoding="utf-8") as f:
        f.write(output.to_json())

    logger.info(f"Wrote JSON variables to {path}")
