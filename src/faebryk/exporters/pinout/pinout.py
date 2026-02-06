# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Pinout exporter - generates a JSON description of IC pinouts for visualization.

For each component with enough pins (>= MIN_PIN_COUNT), exports:
- Pin names/numbers from the footprint pads
- What interface each pin is actively connected to (I2C.scl, power.hv, etc.)
- The bus type classification (I2C, SPI, Power, GPIO, ...)
- Alternate functions available on each pin (from muxed connections)
- Bus groupings so the frontend can highlight related pins together
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver

logger = logging.getLogger(__name__)

MIN_PIN_COUNT = 5

# Known interface types for bus classification, ordered by specificity
_INTERFACE_TYPES: list[tuple[str, str]] = [
    ("I2C", "I2C"),
    ("SPI", "SPI"),
    ("UART", "UART"),
    ("UART_Base", "UART"),
    ("I2S", "I2S"),
    ("USB2_0", "USB"),
    ("USB2_0_IF", "USB"),
    ("JTAG", "JTAG"),
    ("MultiSPI", "SPI"),
    ("XtalIF", "Crystal"),
    ("ElectricPower", "Power"),
    ("ElectricLogic", "GPIO"),
    ("ElectricSignal", "Analog"),
    ("Electrical", "Signal"),
]


def _strip_root_hex(name: str) -> str:
    """Strip leading hex node ID prefix like '0xF8C9.' from names."""
    stripped = re.sub(r"^0x[0-9A-Fa-f]+\.", "", name)
    return stripped if stripped else name


def _classify_interface(name: str) -> str:
    """
    Classify an interface name into a bus type.
    Uses the parent interface hierarchy to determine the type.
    """
    lower = name.lower()

    # Power pins
    if any(
        kw in lower
        for kw in ["power", ".hv", ".lv", "vcc", "vdd", "gnd", "p3v3", "vbus"]
    ):
        return "Power"

    # Specific bus types by keyword
    if "i2c" in lower:
        return "I2C"
    if "spi" in lower or "mspi" in lower:
        return "SPI"
    if "uart" in lower or "rxd" in lower or "txd" in lower:
        return "UART"
    if "i2s" in lower:
        return "I2S"
    if "usb" in lower:
        return "USB"
    if "jtag" in lower:
        return "JTAG"
    if "xtal" in lower or "crystal" in lower:
        return "Crystal"
    if "adc" in lower:
        return "Analog"
    if "gpio" in lower:
        return "GPIO"
    if "enable" in lower or "en" == lower.split(".")[-1]:
        return "Control"

    return "Signal"


def _get_interface_path(node: fabll.Node, component_node: fabll.Node) -> str | None:
    """
    Walk up from a lead's Electrical node to build the interface path
    relative to the component that owns it.

    E.g. for an ESP32, a lead node might trace up to:
      package.IO0 -> gpio[0].line -> i2c.scl.line

    We want the path relative to the component's parent module, like:
      "gpio[0]" or "i2c.scl"
    """
    try:
        full_name = _strip_root_hex(node.get_full_name())
        comp_name = _strip_root_hex(component_node.get_full_name())

        # Try to get the path relative to the component's parent
        parent = component_node.get_parent()
        if parent:
            parent_name = _strip_root_hex(parent[0].get_full_name())
            if full_name.startswith(parent_name + "."):
                return full_name[len(parent_name) + 1 :]

        # Fall back to path relative to the component itself
        if full_name.startswith(comp_name + "."):
            return full_name[len(comp_name) + 1 :]

        return full_name
    except Exception:
        return None


def _trace_lead_interfaces(
    lead_electrical: fabll.Node,
    component_node: fabll.Node,
) -> list[dict]:
    """
    From a lead's Electrical node, trace connected interfaces to find
    all the functions this pin can serve.

    Returns a list of dicts: [{"name": "gpio[0]", "type": "GPIO"}, ...]
    """
    functions: list[dict] = []
    seen_names: set[str] = set()

    # Internal names and patterns to skip
    _SKIP_NAMES = {"part_of", "can_bridge", "reference", "line"}
    _SKIP_PREFIXES = ("_is_", "_has_", "pad_")
    _SKIP_CONTAINS = ("unnamed", ".unnamed", "part_of", "_is_")

    try:
        if not lead_electrical.has_trait(fabll.is_interface):
            return functions

        is_if = lead_electrical.get_trait(fabll.is_interface)
        connected = is_if.get_connected(include_self=False)

        for connected_node, _path in connected.items():
            try:
                iface_path = _get_interface_path(connected_node, component_node)
                if not iface_path:
                    continue

                # Skip internal graph artifacts
                if iface_path in _SKIP_NAMES:
                    continue
                if any(iface_path.startswith(p) for p in _SKIP_PREFIXES):
                    continue
                if any(skip in iface_path for skip in _SKIP_CONTAINS):
                    continue

                # Skip internal paths (pad references, etc.)
                if "pad_" in iface_path or "_is_" in iface_path:
                    continue

                # Skip the component's own package sub-paths
                if iface_path.startswith("package."):
                    continue

                # Skip paths that are just ".line", ".reference", ".hv", ".lv"
                # at the end with no useful prefix
                if iface_path in ("line", "hv", "lv", "gnd", "vcc"):
                    continue

                # Skip very deep paths (likely internal wiring)
                parts = iface_path.split(".")
                if len(parts) > 4:
                    continue

                # Strip trailing ".line" for cleaner display
                display_name = iface_path
                if display_name.endswith(".line"):
                    display_name = display_name[:-5]

                # Deduplicate (check both original and display name)
                if display_name in seen_names:
                    continue
                seen_names.add(display_name)

                bus_type = _classify_interface(iface_path)
                functions.append({"name": display_name, "type": bus_type})

            except Exception:
                continue

    except Exception as e:
        logger.debug(f"Error tracing lead interfaces: {e}")

    # Deduplicate: prefer shorter paths.
    # If we have "mcu.gpio[5]" and "gpio[5]", keep only "gpio[5]".
    # If we have "i2c_bus.sda" and "i2c.sda", keep only "i2c.sda".
    all_names = {fn["name"] for fn in functions}
    cleaned: list[dict] = []

    for fn in functions:
        name = fn["name"]
        parts = name.split(".")
        # Check if a shorter suffix of this path already exists
        is_redundant = False
        if len(parts) >= 2:
            for start in range(1, len(parts)):
                shorter = ".".join(parts[start:])
                if shorter in all_names and shorter != name:
                    is_redundant = True
                    break
        if not is_redundant:
            cleaned.append(fn)

    return cleaned


def _determine_pin_type(pad_name: str, functions: list[dict]) -> str:
    """Determine the primary pin type from its name and functions."""
    lower = pad_name.lower()

    # Ground pins
    if lower in ("gnd", "vss", "ep", "epad", "exposed"):
        return "ground"

    # Power pins
    if any(
        kw in lower for kw in ["vcc", "vdd", "3v3", "p3v3", "5v", "vin", "vbus", "vbat"]
    ):
        return "power"

    # Check from functions
    for fn in functions:
        if fn["type"] == "Power":
            # Distinguish power vs ground from function name
            if ".lv" in fn["name"] or "gnd" in fn["name"].lower():
                return "ground"
            return "power"

    # NC pins
    if lower in ("nc", "n/c", "dnc"):
        return "nc"

    return "signal"


def _get_kicad_pad_geometry(
    component_node: fabll.Node,
) -> dict[str, dict]:
    """
    Extract pad geometry from the KiCad PCB footprint data already
    attached to the graph during the build.

    Returns {pad_name: {"x": float, "y": float, "w": float, "h": float, "rotation": float}}
    in footprint-local coordinates (mm).
    """  # noqa E501
    geometry: dict[str, dict] = {}
    try:
        fp_trait = component_node.get_trait(F.Footprints.has_associated_footprint)
        fp = fp_trait.get_footprint()

        for fpad in fp.get_pads():
            pad_name = fpad.pad_name
            if fpad.has_trait(F.KiCadFootprints.has_associated_kicad_pcb_pad):
                kicad_trait = fpad.get_trait(
                    F.KiCadFootprints.has_associated_kicad_pcb_pad
                )
                pcb_fp, pcb_pads = kicad_trait.get_pads()
                if pcb_pads:
                    pcb_pad = pcb_pads[0]
                    geometry[pad_name] = {
                        "x": round(pcb_pad.at.x - pcb_fp.at.x, 3),
                        "y": round(pcb_pad.at.y - pcb_fp.at.y, 3),
                        "w": round(pcb_pad.size.w, 3),
                        "h": round(pcb_pad.size.h or pcb_pad.size.w, 3),
                        "rotation": pcb_pad.at.r or 0,
                    }
    except Exception as e:
        logger.debug(f"Could not extract KiCad pad geometry: {e}")
    return geometry


def _get_kicad_pad_positions(
    component_node: fabll.Node,
) -> dict[str, tuple[float, float]]:
    """
    Extract pad XY positions (convenience wrapper).
    Returns {pad_name: (x, y)}.
    """
    geo = _get_kicad_pad_geometry(component_node)
    return {name: (g["x"], g["y"]) for name, g in geo.items()}


def _compute_body_geometry(
    positions: dict[str, tuple[float, float]],
    geometry: dict[str, dict],
) -> dict:
    """
    Compute the chip body rectangle from pad positions.
    The body is estimated as the rectangle inset from the outermost pads,
    since pads sit on the edge or outside the package body.
    """
    if not positions:
        return {"x": 0, "y": 0, "width": 10, "height": 10}

    xs = [pos[0] for pos in positions.values()]
    ys = [pos[1] for pos in positions.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Estimate pad inset: use average pad size on the perimeter
    perimeter_pad_sizes: list[float] = []
    width = max_x - min_x or 1.0
    height = max_y - min_y or 1.0
    cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2

    for name, (x, y) in positions.items():
        nx = abs(x - cx) / (width / 2) if width > 0.01 else 0
        ny = abs(y - cy) / (height / 2) if height > 0.01 else 0
        # Only consider perimeter pads (not interior exposed pads)
        if max(nx, ny) > 0.5:
            geo = geometry.get(name, {})
            w = geo.get("w", 0.5)
            h = geo.get("h", 0.5)
            # Pads stick out by half their SHORT dimension from the body
            perimeter_pad_sizes.append(min(w, h))

    inset = (
        sum(perimeter_pad_sizes) / len(perimeter_pad_sizes) / 2
        if perimeter_pad_sizes
        else 0.15
    )

    body_x = min_x + inset
    body_y = min_y + inset
    body_w = max(max_x - min_x - 2 * inset, 1.0)
    body_h = max(max_y - min_y - 2 * inset, 1.0)

    return {
        "x": round(body_x, 3),
        "y": round(body_y, 3),
        "width": round(body_w, 3),
        "height": round(body_h, 3),
        "pad_bbox": {
            "min_x": round(min_x, 3),
            "min_y": round(min_y, 3),
            "max_x": round(max_x, 3),
            "max_y": round(max_y, 3),
        },
    }


def _assign_sides_from_positions(
    pad_names: list[str],
    positions: dict[str, tuple[float, float]],
) -> dict[str, tuple[str, int]]:
    """
    Assign pins to sides based on their physical XY coordinates.
    Uses the pad bounding box to determine which edge each pad is closest to.

    Returns {pad_name: (side, position_on_side)}.
    """
    if not positions or not pad_names:
        return {}

    # Get pads that have positions
    positioned = [(name, positions[name]) for name in pad_names if name in positions]
    if not positioned:
        return {}

    # Compute bounding box of all pads
    xs = [p[1][0] for p in positioned]
    ys = [p[1][1] for p in positioned]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Add small margin to handle single-row cases
    width = max_x - min_x or 1.0
    height = max_y - min_y or 1.0
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2

    # Classify each pad to the nearest edge
    sides: dict[str, list[tuple[str, float]]] = {
        "left": [],
        "right": [],
        "top": [],
        "bottom": [],
    }

    # Threshold: if a pad is within this fraction of the center,
    # it's an interior pad (e.g. exposed ground pad) -> assign to bottom
    interior_threshold = 0.3

    for name, (x, y) in positioned:
        # Normalise to [-1, 1] range relative to bbox center
        nx = (x - cx) / (width / 2) if width > 0.01 else 0
        ny = (y - cy) / (height / 2) if height > 0.01 else 0

        # Interior pads (like exposed GND pads) cluster near center
        if abs(nx) < interior_threshold and abs(ny) < interior_threshold:
            sides["bottom"].append((name, x))  # sort by x for bottom
            continue

        # Determine which edge this pad is closest to
        # Using the normalised distances to each edge
        dist_left = abs(nx - (-1))
        dist_right = abs(nx - 1)
        dist_top = abs(ny - (-1))  # KiCad Y is inverted: top = min Y
        dist_bottom = abs(ny - 1)

        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)

        if min_dist == dist_left:
            sides["left"].append((name, y))  # sort by y (top to bottom)
        elif min_dist == dist_right:
            sides["right"].append((name, y))  # sort by y (top to bottom)
        elif min_dist == dist_top:
            sides["top"].append((name, x))  # sort by x (right to left)
        else:
            sides["bottom"].append((name, x))  # sort by x (left to right)

    # Sort each side by its sorting coordinate
    for side_name in sides:
        sides[side_name].sort(key=lambda t: t[1])

    # Top goes right-to-left in standard IC convention
    sides["top"].reverse()
    # Right goes bottom-to-top in standard IC convention
    sides["right"].reverse()

    # Build result: pad_name -> (side, position_index)
    result: dict[str, tuple[str, int]] = {}
    for side_name, pad_list in sides.items():
        for pos_idx, (name, _) in enumerate(pad_list):
            result[name] = (side_name, pos_idx)

    # Assign fallback for pads without positions
    fallback_pos = 0
    for name in pad_names:
        if name not in result:
            result[name] = ("left", fallback_pos)
            fallback_pos += 1

    return result


def export_pinout_json(
    app: fabll.Node,
    solver: Solver,
    *,
    json_path: Path,
) -> None:
    """
    Export pinout information for all ICs with >= MIN_PIN_COUNT pins.

    Walks all components with is_atomic_part trait, extracts their pads,
    traces lead connections to determine pin functions, and classifies
    pins by bus type.
    """

    # Find all modules with is_atomic_part trait
    atomic_parts = list(
        fabll.Traits.get_implementors(
            F.is_atomic_part.bind_typegraph(app.tg),
            g=app.g,
        )
    )

    if not atomic_parts:
        logger.info("No atomic parts found, writing empty pinout JSON")
        _write_json({"version": "1.0", "components": []}, json_path)
        return

    json_components = []
    comp_counter = 0

    for atomic_part_trait in atomic_parts:
        try:
            component_node = fabll.Traits.bind(atomic_part_trait).get_obj_raw()

            # Get the footprint and its pads
            if not component_node.has_trait(F.Footprints.has_associated_footprint):
                continue

            fp_trait = component_node.get_trait(F.Footprints.has_associated_footprint)
            fp = fp_trait.get_footprint()
            pads = fp.get_pads()

            if len(pads) < MIN_PIN_COUNT:
                continue

            # Get component name and metadata
            comp_name = _strip_root_hex(component_node.get_full_name())
            parent = component_node.get_parent()
            parent_name = None
            if parent:
                parent_name = _strip_root_hex(parent[0].get_full_name())
                # If parent is the app root (bare hex ID), use component name
                if parent_name and re.match(r"^0x[0-9A-Fa-f]+$", parent_name):
                    parent_name = None

            # Get designator if available
            designator = None
            if component_node.has_trait(F.has_designator):
                try:
                    designator = component_node.get_trait(
                        F.has_designator
                    ).get_designator()
                except Exception:
                    pass

            # Try to get module type name
            module_type = None
            try:
                if component_node.has_trait(fabll.is_module):
                    module_type = component_node.get_trait(
                        fabll.is_module
                    ).get_module_locator()
                    # Clean up the type name
                    if "::" in module_type:
                        module_type = module_type.split("::")[-1]
                    module_type = _strip_root_hex(module_type)
            except Exception:
                pass

            # Get package info from footprint
            package = None
            try:
                fp_str = atomic_part_trait.footprint.get().extract_singleton()
                if fp_str:
                    # Extract just the package identifier
                    package = fp_str.split(":")[-1] if ":" in fp_str else fp_str
            except Exception:
                pass

            # Get leads and map them to pads
            lead_nodes = component_node.get_children(
                direct_only=False,
                types=fabll.Node,
                required_trait=F.Lead.is_lead,
            )

            # Build pad_name -> (lead_electrical, lead_display_name) mapping
            # The display name should be the signal name from the .ato code
            # (e.g. "EN", "GND", "IO0", "P3V3") not the raw pad number.
            pad_to_lead: dict[str, fabll.Node] = {}
            pad_to_lead_name: dict[str, str] = {}
            for lead_node in lead_nodes:
                lead_trait = lead_node.get_trait(F.Lead.is_lead)
                # Try multiple approaches to get a meaningful name:
                # 1. The lead's own name (from get_lead_name)
                lead_name = lead_trait.get_lead_name()
                # 2. The node's name in the parent hierarchy
                try:
                    node_name = lead_node.get_name(accept_no_parent=True)
                    if node_name and not node_name.isdigit():
                        lead_name = node_name
                except Exception:
                    pass
                # 3. Walk up to find a named parent that isn't the component
                if lead_name.isdigit():
                    try:
                        parent_info = lead_node.get_parent()
                        if parent_info:
                            parent_node, child_name = parent_info
                            if child_name and not child_name.isdigit():
                                lead_name = child_name
                            elif parent_node:
                                pname = parent_node.get_name(accept_no_parent=True)
                                if pname and not pname.isdigit():
                                    lead_name = pname
                    except Exception:
                        pass

                if lead_trait.has_trait(F.Lead.has_associated_pads):
                    assoc_pads = lead_trait.get_trait(
                        F.Lead.has_associated_pads
                    ).get_pads()
                    for pad in assoc_pads:
                        try:
                            pad_to_lead[pad.pad_name] = lead_node
                            pad_to_lead_name[pad.pad_name] = lead_name
                        except Exception:
                            continue

            # Sort pads by number for consistent ordering
            sorted_pads = sorted(pads, key=lambda p: _natural_sort_key(p.pad_number))

            # Collapse duplicate pads that share the same lead (e.g. exposed
            # GND pads on QFN packages that are all connected together).
            # Keep only unique lead mappings.
            seen_leads: dict[str, list[str]] = {}  # lead_name -> [pad_numbers]
            unique_pads: list[F.Footprints.is_pad] = []
            for pad in sorted_pads:
                try:
                    pad_name = pad.pad_name
                    lead_name = pad_to_lead_name.get(pad_name, pad_name)
                    if lead_name in seen_leads:
                        seen_leads[lead_name].append(pad.pad_number)
                    else:
                        seen_leads[lead_name] = [pad.pad_number]
                        unique_pads.append(pad)
                except Exception:
                    unique_pads.append(pad)

            # Get physical pad geometry from KiCad footprint
            kicad_geometry = _get_kicad_pad_geometry(component_node)
            kicad_positions = {
                name: (g["x"], g["y"]) for name, g in kicad_geometry.items()
            }

            # Assign sides using physical positions
            unique_pad_names = [p.pad_name for p in unique_pads]
            side_map = _assign_sides_from_positions(unique_pad_names, kicad_positions)

            # Compute chip body bounding box from pad positions
            # The body is inset from the outermost pads
            body_geometry = _compute_body_geometry(kicad_positions, kicad_geometry)

            # Build pin data
            json_pins = []
            all_buses: dict[str, dict] = {}  # bus_id -> bus info

            for pin_idx, pad in enumerate(unique_pads):
                try:
                    pad_name = pad.pad_name
                    pad_number = pad.pad_number
                except Exception:
                    continue

                # Use lead name as display name (e.g. "IO0", "GND", "P3V3")
                # instead of the raw pad number
                lead_name = pad_to_lead_name.get(pad_name, pad_name)
                display_name = lead_name

                # If multiple pads share this lead, note them
                all_pad_numbers = seen_leads.get(lead_name, [pad_number])

                # Get the side assignment from physical positions
                side, position = side_map.get(pad_name, ("left", pin_idx))

                # Trace interfaces from the lead
                functions: list[dict] = []
                active_function = None
                lead_node = pad_to_lead.get(pad_name)

                if lead_node is not None:
                    # The lead_node IS the Electrical that connects to the pad
                    # Trace its interface connections
                    functions = _trace_lead_interfaces(lead_node, component_node)

                    # The "active" function is the most specific non-GPIO function
                    # that indicates actual use in the design
                    active_function = _pick_active_function(functions)

                # Classify pin type
                pin_type = _determine_pin_type(display_name, functions)

                # Track bus memberships
                if active_function:
                    bus_id = _make_bus_id(active_function, comp_name)
                    if bus_id not in all_buses:
                        all_buses[bus_id] = {
                            "id": bus_id,
                            "type": active_function["type"],
                            "name": _extract_bus_name(active_function["name"]),
                            "pin_numbers": [],
                        }
                    all_buses[bus_id]["pin_numbers"].append(pad_number)

                # Physical pad geometry
                pad_geo = kicad_geometry.get(pad_name)

                json_pins.append(
                    {
                        "number": pad_number,
                        "name": display_name,
                        "side": side,
                        "position": position,
                        "type": pin_type,
                        "active_function": active_function,
                        "alternate_functions": functions,
                        "pad_count": len(all_pad_numbers)
                        if len(all_pad_numbers) > 1
                        else None,
                        "x": pad_geo["x"] if pad_geo else None,
                        "y": pad_geo["y"] if pad_geo else None,
                        "w": pad_geo["w"] if pad_geo else None,
                        "h": pad_geo["h"] if pad_geo else None,
                    }
                )

            # Use parent_name as display name if available, else comp_name
            display_name = parent_name or comp_name

            json_components.append(
                {
                    "id": f"c{comp_counter}",
                    "name": display_name,
                    "module_type": module_type,
                    "designator": designator,
                    "package": package,
                    "pin_count": len(json_pins),
                    "total_pads": len(sorted_pads),
                    "geometry": body_geometry,
                    "pins": json_pins,
                    "buses": list(all_buses.values()),
                }
            )
            comp_counter += 1

        except Exception as e:
            logger.debug(f"Error processing component: {e}", exc_info=True)
            continue

    _write_json({"version": "1.0", "components": json_components}, json_path)
    logger.info(
        "Wrote pinout JSON with %d components to %s",
        len(json_components),
        json_path,
    )


def _pick_active_function(functions: list[dict]) -> dict | None:
    """
    Pick the most specific active function for a pin.
    Prefers bus-specific functions (I2C, SPI) over generic (GPIO, Signal).
    """
    if not functions:
        return None

    # Priority order: specific buses > analog > GPIO > generic
    priority = {
        "I2C": 10,
        "SPI": 10,
        "UART": 10,
        "I2S": 10,
        "USB": 10,
        "JTAG": 9,
        "Crystal": 8,
        "Power": 7,
        "Control": 6,
        "Analog": 5,
        "GPIO": 3,
        "Signal": 1,
    }

    best = max(functions, key=lambda f: priority.get(f["type"], 0))
    return best


def _make_bus_id(function: dict, comp_name: str) -> str:
    """Create a unique bus ID from a function."""
    bus_name = _extract_bus_name(function["name"])
    return f"{comp_name}_{function['type']}_{bus_name}".replace(".", "_")


def _extract_bus_name(interface_name: str) -> str:
    """Extract the bus name from an interface path like 'i2c.scl' -> 'i2c'."""
    parts = interface_name.split(".")
    if len(parts) >= 2:
        return parts[0]
    return interface_name


def _natural_sort_key(s: str) -> list:
    """Sort key that handles mixed alpha-numeric strings naturally."""
    parts = re.split(r"(\d+)", s)
    result = []
    for part in parts:
        if part.isdigit():
            result.append(int(part))
        else:
            result.append(part.lower())
    return result


def _write_json(data: dict, path: Path) -> None:
    """Write JSON atomically via temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
