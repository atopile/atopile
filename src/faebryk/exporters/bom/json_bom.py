# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
JSON BOM exporter for the VSCode extension.

Generates a rich JSON BOM with all the data needed by the extension's BOM panel,
including pricing, stock, parameters, and usage locations (as atopile addresses).
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


@dataclass
class BOMParameter:
    """A parameter with its resolved value."""

    name: str
    value: str
    unit: str | None = None


@dataclass
class BOMUsage:
    """Where a component is used in the design."""

    address: str  # Atopile address e.g., "App.power_supply.decoupling[0]"
    designator: str  # e.g., "C3"


@dataclass
class BOMComponent:
    """A component in the BOM, grouped by LCSC part number."""

    id: str  # Unique ID (typically LCSC number lowercase)
    lcsc: str | None  # LCSC Part Number e.g., "C25744"
    manufacturer: str | None
    mpn: str | None  # Manufacturer Part Number
    type: str  # Component type: resistor, capacitor, inductor, ic, etc.
    value: str  # Human-readable value e.g., "10kΩ ±1%"
    package: str  # Package/footprint e.g., "0402"
    description: str | None
    quantity: int
    unitCost: float | None  # Unit price in USD
    stock: int | None  # Stock quantity
    isBasic: bool | None  # JLCPCB basic part
    isPreferred: bool | None  # JLCPCB preferred part
    source: str  # How the part was selected: "picked", "specified", "manual"
    parameters: list[BOMParameter] = field(default_factory=list)
    usages: list[BOMUsage] = field(default_factory=list)


@dataclass
class JSONBOMOutput:
    """The full JSON BOM output."""

    version: str = "1.0"
    components: list[BOMComponent] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def _get_component_type_from_prefix(prefix: str) -> str:
    """Map designator prefix to component type."""
    prefix_map = {
        "R": "resistor",
        "C": "capacitor",
        "L": "inductor",
        "U": "ic",
        "IC": "ic",
        "J": "connector",
        "P": "connector",
        "D": "diode",
        "LED": "led",
        "Q": "transistor",
        "T": "transistor",
        "Y": "crystal",
        "XTAL": "crystal",
        "F": "fuse",
        "FB": "inductor",  # Ferrite bead
        "SW": "switch",
        "S": "switch",
        "TP": "testpoint",
        "MOD": "module",
    }
    return prefix_map.get(prefix.upper(), "other")


def _get_component_type_from_endpoint(
    endpoint: F.Pickable.is_pickable_by_type.Endpoint,
) -> str:
    """Map picker endpoint to component type."""
    endpoint_map = {
        F.Pickable.is_pickable_by_type.Endpoint.RESISTORS: "resistor",
        F.Pickable.is_pickable_by_type.Endpoint.CAPACITORS: "capacitor",
        F.Pickable.is_pickable_by_type.Endpoint.INDUCTORS: "inductor",
    }
    return endpoint_map.get(endpoint, "other")


def _get_component_type(module: fabll.Node) -> str:
    """Determine the component type from the module."""
    # Try to get from is_pickable_by_type endpoint first
    if pbt := module.try_get_trait(F.Pickable.is_pickable_by_type):
        try:
            endpoint = pbt.endpoint
            if endpoint:
                return _get_component_type_from_endpoint(
                    F.Pickable.is_pickable_by_type.Endpoint(endpoint)
                )
        except Exception:
            pass

    # Fall back to designator prefix
    if prefix_trait := module.try_get_trait(F.has_designator_prefix):
        prefix = prefix_trait.get_prefix()
        return _get_component_type_from_prefix(prefix)

    # Fall back to designator itself
    if designator_trait := module.try_get_trait(F.has_designator):
        designator = designator_trait.get_designator()
        if designator:
            # Extract prefix (letters before numbers)
            prefix = "".join(c for c in designator if c.isalpha())
            return _get_component_type_from_prefix(prefix)

    return "other"


def _get_source_type(module: fabll.Node) -> str:
    """Determine how the part was selected."""
    if module.has_trait(F.Pickable.is_pickable_by_supplier_id):
        return "specified"  # User explicitly specified LCSC ID
    elif module.has_trait(F.Pickable.is_pickable_by_part_number):
        return "specified"  # User specified manufacturer + part number
    elif module.has_trait(F.Pickable.is_pickable_by_type):
        return "picked"  # Part was picked parametrically
    else:
        return "manual"


def _get_parameters(
    module: fabll.Node, part_trait: F.Pickable.has_part_picked
) -> list[BOMParameter]:
    """Extract parameters from the module."""
    parameters: list[BOMParameter] = []

    # Get parameters from is_pickable_by_type if available
    if pbt := module.try_get_trait(F.Pickable.is_pickable_by_type):
        for param in pbt.get_params():
            try:
                param_node = fabll.Traits(param).get_obj_raw()
                param_name = param_node.get_name()

                # Try to get the picked attribute value first
                value_str = None
                if attr_lit := part_trait.get_attribute(param_name):
                    try:
                        value_str = attr_lit.pretty_str()
                    except Exception:
                        pass

                # If no picked attribute, try to get from the parameter itself
                if not value_str:
                    try:
                        # Try to get a concrete value from the parameter
                        if hasattr(param, "try_extract_singleton"):
                            singleton = param.try_extract_singleton()
                            if singleton is not None:
                                value_str = str(singleton)
                    except Exception:
                        pass

                # Skip parameters without concrete values
                if not value_str:
                    continue

                # Try to extract unit from the parameter
                unit = None
                try:
                    if hasattr(param, "get_unit"):
                        unit_obj = param.get_unit()
                        if unit_obj:
                            unit = str(unit_obj)
                except Exception:
                    pass

                parameters.append(
                    BOMParameter(
                        name=param_name,
                        value=value_str,
                        unit=unit,
                    )
                )
            except Exception as e:
                logger.debug(f"Could not extract parameter: {e}")

    return parameters


def _get_footprint_name(part: F.Pickable.has_part_picked) -> str:
    """Get the footprint/package name."""
    if footprint_trait := part.try_get_sibling_trait(
        F.Footprints.has_associated_footprint
    ):
        if kicad_footprint := footprint_trait.get_footprint().try_get_trait(
            F.KiCadFootprints.has_associated_kicad_pcb_footprint
        ):
            return kicad_footprint.get_footprint().name
        elif kicad_library_footprint := footprint_trait.get_footprint().try_get_trait(
            F.KiCadFootprints.has_associated_kicad_library_footprint
        ):
            # Extract just the package name from the library name
            lib_name = kicad_library_footprint.get_library_name()
            # Try to extract package from name like "R0402" or "C0603"
            return lib_name.split(":")[-1] if ":" in lib_name else lib_name
    return ""


def make_json_bom(
    components: Iterable[F.Pickable.has_part_picked],
) -> JSONBOMOutput:
    """
    Generate a JSON BOM from picked components.

    Components are grouped by their LCSC part number (or MPN if no LCSC).
    """
    # Group components by part identifier
    grouped: dict[str, BOMComponent] = {}

    for part_trait in components:
        try:
            picked_part = part_trait.try_get_part()
            if picked_part is None:
                continue

            module = fabll.Traits(part_trait).get_obj_raw()
            module_trait = module.try_get_trait(fabll.is_module)

            if not module_trait:
                continue

            # Get designator
            designator = ""
            if designator_trait := part_trait.try_get_sibling_trait(F.has_designator):
                designator = designator_trait.get_designator() or ""

            # Get module address
            address = module_trait.get_module_locator()

            # Get value representation
            value = ""
            if hsvp := part_trait.try_get_sibling_trait(
                F.has_simple_value_representation
            ):
                value = hsvp.get_value()

            # Get part info
            supplier_partno = picked_part.supplier_partno
            manufacturer = picked_part.manufacturer
            partno = picked_part.partno

            # Create a unique ID for grouping
            part_id = (
                supplier_partno.lower()
                if supplier_partno
                else f"{manufacturer}_{partno}".lower()
            )

            # Get additional info if available (from PickedPartLCSC)
            stock = None
            unit_cost = None
            description = None
            is_basic = None
            is_preferred = None

            # Try to get extended info from PickedPartLCSC
            from faebryk.libs.picker.lcsc import PickedPartLCSC

            if isinstance(picked_part, PickedPartLCSC) and picked_part.info:
                stock = picked_part.info.stock
                unit_cost = picked_part.info.price
                description = picked_part.info.description
                is_basic = picked_part.info.basic
                is_preferred = picked_part.info.preferred

            # Also try to get description from has_datasheet trait
            if description is None:
                if module.try_get_trait(F.has_datasheet):
                    # Description comes from picked part info
                    pass

            # Get package/footprint
            package = _get_footprint_name(part_trait)

            # Get component type
            comp_type = _get_component_type(module)

            # Get source type
            source = _get_source_type(module)

            # Get parameters
            parameters = _get_parameters(module, part_trait)

            # Create usage entry
            usage = BOMUsage(address=address, designator=designator)

            if part_id in grouped:
                # Add to existing component
                grouped[part_id].quantity += 1
                grouped[part_id].usages.append(usage)
            else:
                # Create new component entry
                grouped[part_id] = BOMComponent(
                    id=part_id,
                    lcsc=supplier_partno
                    if supplier_partno.upper().startswith("C")
                    else None,
                    manufacturer=manufacturer,
                    mpn=partno,
                    type=comp_type,
                    value=value,
                    package=package,
                    description=description,
                    quantity=1,
                    unitCost=unit_cost,
                    stock=stock,
                    isBasic=is_basic,
                    isPreferred=is_preferred,
                    source=source,
                    parameters=parameters,
                    usages=[usage],
                )

        except Exception as e:
            logger.warning(f"Could not process component for JSON BOM: {e}")
            continue

    # Sort by quantity (highest first), then by ID
    sorted_components = sorted(
        grouped.values(),
        key=lambda c: (-c.quantity, c.id),
    )

    return JSONBOMOutput(components=sorted_components)


def write_json_bom(
    components: Iterable[F.Pickable.has_part_picked],
    path: Path,
) -> None:
    """Write a JSON BOM to a file."""
    if not path.parent.exists():
        os.makedirs(path.parent)

    bom = make_json_bom(components)

    with open(path, "w", encoding="utf-8") as f:
        f.write(bom.to_json())

    logger.info(f"Wrote JSON BOM to {path}")
