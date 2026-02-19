# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Pinout exporter: generates pinout reports (JSON, CSV, Markdown) for components
marked with the `generate_pinout_details` trait.

Traverses the graph to extract pin names, signal types, interface assignments,
external connections, voltage levels, and net names.
"""

import csv
import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.nets import get_named_net
from faebryk.libs.util import unique

logger = logging.getLogger(__name__)

# Known interface types and their pin-to-function mappings
KNOWN_INTERFACES: dict[type, str] = {
    F.I2C: "I2C",
    F.SPI: "SPI",
    F.UART: "UART",
    F.UART_Base: "UART",
    F.JTAG: "JTAG",
    F.USB2_0: "USB",
    F.CAN: "CAN",
    F.I2S: "I2S",
}


# ---------------------------------------------------------------------------
#  Data model
# ---------------------------------------------------------------------------


@dataclass
class FootprintPadGeometry:
    pad_number: str  # matches PinInfo.pin_number
    x: float  # center x in mm
    y: float  # center y in mm
    width: float  # mm
    height: float  # mm
    shape: str  # "rect", "circle", "roundrect", "oval"
    rotation: float  # degrees
    pad_type: str  # "smd", "thru_hole"
    layers: list[str] = field(default_factory=list)
    roundrect_ratio: float | None = None


@dataclass
class FootprintDrawing:
    type: str  # "line", "arc", "circle", "rect"
    layer: str
    width: float
    start_x: float | None = None
    start_y: float | None = None
    end_x: float | None = None
    end_y: float | None = None
    mid_x: float | None = None
    mid_y: float | None = None
    center_x: float | None = None
    center_y: float | None = None


@dataclass
class PinInfo:
    pin_name: str  # e.g., "gpio[0]", "i2c.scl"
    pin_number: str | None = None  # Physical pin/pad number if available
    net_name: str | None = None  # Net name if assigned
    signal_type: str = "digital"  # "digital", "analog", "power", "ground", "nc"
    direction: str = "bidirectional"  # "input", "output", "bidirectional", "power"
    interfaces: list[str] = field(default_factory=list)  # ["I2C (SDA)", "ADC1[0]"]
    connected_to: list[str] = field(default_factory=list)  # External connections
    is_connected: bool = False  # True if lead connects to another pad/lead
    voltage: str | None = None  # Logic level, e.g., "3.3V"
    notes: list[str] = field(default_factory=list)  # Warnings, capability notes


@dataclass
class PinoutComponent:
    name: str  # Component instance name (e.g., "micro")
    type_name: str  # Type name (e.g., "ESP32_C3_MINI_1")
    pins: list[PinInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    footprint_pads: list[FootprintPadGeometry] = field(default_factory=list)
    footprint_drawings: list[FootprintDrawing] = field(default_factory=list)


@dataclass
class PinoutReport:
    version: str = "1.0"
    build_id: str | None = None
    components: list[PinoutComponent] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
#  Extraction helpers
# ---------------------------------------------------------------------------


def _get_iface_connected(
    node: fabll.Node, include_self: bool = False
) -> dict[fabll.Node, object]:
    """Get electrically connected nodes from an interface node.

    Works with both typed wrapper objects (which have ``._is_interface``)
    and raw ``Node`` objects (which need the trait system).
    """
    try:
        return node._is_interface.get().get_connected(include_self=include_self)
    except AttributeError:
        iface_trait = node.try_get_trait(fabll.is_interface)
        if iface_trait is not None:
            return iface_trait.get_connected(include_self=include_self)
        return {}


def _get_pin_name_relative_to(pin: fabll.Node, component: fabll.Node) -> str:
    """Get the pin's name relative to the component (e.g., 'gpio[0]' or 'i2c.scl')."""
    pin_full = pin.get_full_name()
    comp_full = component.get_full_name()
    if pin_full.startswith(comp_full + "."):
        return pin_full[len(comp_full) + 1 :]
    return pin.get_name()


def _detect_signal_type(pin: fabll.Node) -> str:
    """Determine signal type based on the pin's class."""
    if pin.isinstance(F.ElectricPower):
        return "power"
    elif pin.isinstance(F.ElectricLogic):
        return "digital"
    elif pin.isinstance(F.ElectricSignal):
        return "analog"
    return "digital"


def _detect_direction(pin: fabll.Node) -> str:
    """Infer direction from signal type."""
    if pin.isinstance(F.ElectricPower):
        return "power"
    return "bidirectional"


def _find_interface_assignments(pin: fabll.Node, component: fabll.Node) -> list[str]:
    """
    Walk the parent hierarchy of a pin to find which known interface types
    it belongs to within the same component.
    """
    interfaces: list[str] = []
    current = pin
    comp_full = component.get_full_name()

    while True:
        parent_info = current.get_parent()
        if parent_info is None:
            break
        parent_node, child_name = parent_info

        # Stop if we've left the component
        parent_full = parent_node.get_full_name()
        if not parent_full.startswith(comp_full):
            break

        # Check if the parent is a known interface type
        for iface_type, iface_label in KNOWN_INTERFACES.items():
            if parent_node.isinstance(iface_type):
                # child_name is the pin's role within the interface
                # (e.g., "scl", "mosi")
                interfaces.append(f"{iface_label} ({child_name.upper()})")
                break

        current = parent_node

    return interfaces


def _find_interface_assignments_via_connections(
    pin: fabll.Node, component: fabll.Node
) -> list[str]:
    """Detect interface assignments through internal connections.

    When ``io[19]`` is connected to ``usb.usb_if.d.n`` within the same
    component, this detects that ``io[19]`` has a ``USB (D.N)`` interface
    assignment.  Works for any known interface type (I2C, SPI, UART, USB …).

    Also detects capabilities from connected ``ElectricSignal`` pins
    (e.g. ``touch[1] ~ io[1]`` → ``TOUCH (1)``).
    """
    interfaces: list[str] = []
    comp_full = component.get_full_name()

    try:
        if not (pin.isinstance(F.ElectricLogic) or pin.isinstance(F.ElectricSignal)):
            return interfaces

        connected = _get_iface_connected(pin.line.get())

        for conn_node, _ in connected.items():
            conn_full = conn_node.get_full_name()
            # Only interested in connections WITHIN the component
            if not conn_full.startswith(comp_full + "."):
                continue

            # conn_node is a line node; get its parent (the pin)
            parent_info = conn_node.get_parent()
            if parent_info is None:
                continue
            connected_pin = parent_info[0]

            # Walk from connected_pin upward to find known interfaces
            current = connected_pin
            path_parts: list[str] = []
            found_known = False

            while True:
                pi = current.get_parent()
                if pi is None:
                    break
                parent_node, child_name = pi
                parent_full = parent_node.get_full_name()
                if not parent_full.startswith(comp_full):
                    break

                path_parts.append(child_name)

                for iface_type, iface_label in KNOWN_INTERFACES.items():
                    if parent_node.isinstance(iface_type):
                        # Build a role label from the accumulated path.
                        # For shallow matches (I2C → sda) → "SDA".
                        # For deep matches (USB2_0 → usb_if → d → n)
                        #   drop the topmost wrapper segment → "D.N".
                        if len(path_parts) <= 1:
                            role = path_parts[0] if path_parts else child_name
                        else:
                            role = ".".join(reversed(path_parts[:-1]))
                        interfaces.append(f"{iface_label} ({role.upper()})")
                        found_known = True
                        break

                current = parent_node

            # If no known interface was found but the connected pin is an
            # ElectricSignal, use its parent group name as a capability
            # label (e.g. touch[1] → "TOUCH (1)", adc[5] → "ADC (5)").
            if not found_known and connected_pin.isinstance(F.ElectricSignal):
                rel = _get_pin_name_relative_to(connected_pin, component)
                m = re.match(r"^(\w+)\[(\d+)\]$", rel)
                if m:
                    interfaces.append(f"{m.group(1).upper()} ({m.group(2)})")

    except Exception:
        logger.debug("Could not find connected interfaces for %s", pin.get_full_name())

    return interfaces


def _find_external_connections(
    pin: fabll.Node, component: fabll.Node, app_prefix: str = ""
) -> list[str]:
    """
    Find all nodes electrically connected to this pin that are outside
    the current component.
    """
    external: list[str] = []
    comp_full = component.get_full_name()

    def _clean_name(full_name: str) -> str:
        """Strip the app root prefix (e.g., '0x6E347.') for readability."""
        if app_prefix and full_name.startswith(app_prefix + "."):
            return full_name[len(app_prefix) + 1 :]
        return full_name

    def _is_graph_artifact(name: str) -> bool:
        """Detect internal graph references (hex node IDs) that are not
        meaningful user-visible connections."""
        return bool(re.match(r"^0x[0-9a-fA-F]+", name))

    def _collect(connected: dict) -> None:
        for connected_node, _path in connected.items():
            connected_full = connected_node.get_full_name()
            if connected_full.startswith(comp_full + "."):
                continue  # internal to the component
            clean = _clean_name(connected_full)
            if _is_graph_artifact(clean):
                continue  # graph-internal plumbing, not a real connection
            external.append(clean)

    # For ElectricLogic/ElectricSignal, check the line's connections
    if pin.isinstance(F.ElectricLogic) or pin.isinstance(F.ElectricSignal):
        try:
            _collect(_get_iface_connected(pin.line.get()))
        except Exception:
            logger.debug("Could not get connections for %s", pin.get_full_name())
    elif pin.isinstance(F.ElectricPower):
        try:
            _collect(_get_iface_connected(pin))
        except Exception:
            logger.debug("Could not get power connections for %s", pin.get_full_name())

    return external


def _find_internal_connections(
    pin: fabll.Node,
    component: fabll.Node,
    ic_module_full: str | None = None,
) -> list[str]:
    """Find connections to internal sub-modules (buttons, resistors, etc.).

    Walks from each connected node upward to find the direct child sub-module
    of *component* that owns it.  Excludes the IC package (identified by
    *ic_module_full*) since those are physical pad mappings, not meaningful
    hardware connections.
    """
    comp_full = component.get_full_name()
    submodules: set[str] = set()

    def _find_submodule_of(node: fabll.Node) -> str | None:
        """Walk up from *node* to find the direct child module of *component*."""
        current = node
        while True:
            parent_info = current.get_parent()
            if parent_info is None:
                return None
            parent_node, child_name = parent_info
            parent_full = parent_node.get_full_name()
            if parent_full == comp_full:
                if current.try_get_trait(fabll.is_module):
                    return child_name
                return None
            if not parent_full.startswith(comp_full + "."):
                return None
            current = parent_node

    def _collect(connected: dict) -> None:
        for connected_node, _path in connected.items():
            connected_full = connected_node.get_full_name()
            if not connected_full.startswith(comp_full + "."):
                continue  # external — handled by _find_external_connections
            if ic_module_full and connected_full.startswith(ic_module_full + "."):
                continue  # IC package lead — not a meaningful connection
            submod = _find_submodule_of(connected_node)
            if submod:
                submodules.add(submod)

    if pin.isinstance(F.ElectricLogic) or pin.isinstance(F.ElectricSignal):
        try:
            _collect(_get_iface_connected(pin.line.get()))
        except Exception:
            pass
    elif pin.isinstance(F.ElectricPower):
        try:
            _collect(_get_iface_connected(pin))
        except Exception:
            pass

    return sorted(submodules)


def _extract_voltage(pin: fabll.Node) -> str | None:
    """Extract the voltage/logic level from the pin's reference.

    Returns ``None`` for unconstrained values (e.g. ``{ℝ+}V``) so that
    only concrete numbers or intervals are shown.
    """
    try:
        superset = None
        if pin.isinstance(F.ElectricLogic) or pin.isinstance(F.ElectricSignal):
            ref = pin.reference.get()
            voltage_param = ref.voltage.get()
            superset = voltage_param.try_extract_superset()
        elif pin.isinstance(F.ElectricPower):
            voltage_param = pin.voltage.get()
            superset = voltage_param.try_extract_superset()

        if superset is not None:
            text = superset.pretty_str()
            # Discard unconstrained values like "{ℝ+}V" or "{ℝ}V"
            if re.search(r"\d", text):
                return text
    except Exception:
        logger.debug("Could not extract voltage for %s", pin.get_full_name())
    return None


def _find_ic_module(
    component: fabll.Node,
) -> tuple[list[fabll.Node], fabll.Node | None, str | None]:
    """Find IC lead nodes (from the child module with the most leads).

    This identifies the main IC package within a module so that lead tracing
    only picks up physical package pins, not leads from passive components
    like resistors or capacitors.

    Returns ``(ic_leads, ic_module_node, ic_module_full_name)``.
    """
    ic_leads: list[fabll.Node] = []
    ic_module: fabll.Node | None = None
    ic_module_full: str | None = None
    best_count = 0

    for child in component.get_children(
        direct_only=True, types=fabll.Node, required_trait=fabll.is_module
    ):
        leads = child.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Lead.is_lead,
        )
        if len(leads) > best_count:
            best_count = len(leads)
            ic_leads = leads
            ic_module = child
            ic_module_full = child.get_full_name()

    # Fallback: component itself is a bare package (e.g. signal PA0 ~ pin D5)
    if best_count == 0 and component.try_get_trait(F.is_atomic_part):
        leads = component.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Lead.is_lead,
        )
        if leads:
            ic_leads = leads
            ic_module = component
            ic_module_full = component.get_full_name()

    return ic_leads, ic_module, ic_module_full


def _extract_footprint_geometry(
    ic_module: fabll.Node,
) -> tuple[list[FootprintPadGeometry], list[FootprintDrawing]]:
    """Extract pad geometry and silk/fab drawings from the IC's KiCad footprint.

    Returns ``(pads, drawings)``.
    """
    from faebryk.libs.kicad.fileformats import kicad

    pads: list[FootprintPadGeometry] = []
    drawings: list[FootprintDrawing] = []

    try:
        atomic_part = ic_module.try_get_trait(F.is_atomic_part)
        if atomic_part is None:
            return pads, drawings

        fp_path = atomic_part.get_kicad_footprint_file_path()
        if not Path(fp_path).exists():
            logger.debug("Footprint file not found: %s", fp_path)
            return pads, drawings

        fp_file = kicad.loads(kicad.footprint.FootprintFile, Path(fp_path))
        footprint = fp_file.footprint

        # Extract pads (filter to copper layers)
        copper_layers = {"F.Cu", "B.Cu", "*.Cu", "F&B.Cu"}
        for pad in footprint.pads:
            has_copper = any(
                layer in copper_layers or layer.endswith(".Cu") for layer in pad.layers
            )
            if not has_copper:
                continue

            pads.append(
                FootprintPadGeometry(
                    pad_number=pad.name,
                    x=pad.at.x,
                    y=pad.at.y,
                    width=pad.size.w,
                    height=pad.size.h if pad.size.h is not None else pad.size.w,
                    shape=pad.shape,
                    rotation=pad.at.r if pad.at.r is not None else 0.0,
                    pad_type=pad.type,
                    layers=list(pad.layers),
                    roundrect_ratio=pad.roundrect_rratio,
                )
            )

        # Extract drawings from silk screen layers only (Fab layer circles
        # overlap pads and obscure signal-type coloring in the pinout viewer)
        drawing_layers = {"F.SilkS", "B.SilkS"}

        for line in footprint.fp_lines:
            layer = line.layer
            if layer not in drawing_layers:
                continue
            stroke_width = line.stroke.width if line.stroke else 0.12
            drawings.append(
                FootprintDrawing(
                    type="line",
                    layer=layer,
                    width=stroke_width,
                    start_x=line.start.x,
                    start_y=line.start.y,
                    end_x=line.end.x,
                    end_y=line.end.y,
                )
            )

        for arc in footprint.fp_arcs:
            layer = arc.layer
            if layer not in drawing_layers:
                continue
            stroke_width = arc.stroke.width if arc.stroke else 0.12
            drawings.append(
                FootprintDrawing(
                    type="arc",
                    layer=layer,
                    width=stroke_width,
                    start_x=arc.start.x,
                    start_y=arc.start.y,
                    end_x=arc.end.x,
                    end_y=arc.end.y,
                    mid_x=arc.mid.x,
                    mid_y=arc.mid.y,
                )
            )

        for rect in footprint.fp_rects:
            layer = rect.layer
            if layer not in drawing_layers:
                continue
            stroke_width = rect.stroke.width if rect.stroke else 0.12
            drawings.append(
                FootprintDrawing(
                    type="rect",
                    layer=layer,
                    width=stroke_width,
                    start_x=rect.start.x,
                    start_y=rect.start.y,
                    end_x=rect.end.x,
                    end_y=rect.end.y,
                )
            )

        for circle in footprint.fp_circles:
            layer = circle.layer
            if layer not in drawing_layers:
                continue
            stroke_width = circle.stroke.width if circle.stroke else 0.12
            drawings.append(
                FootprintDrawing(
                    type="circle",
                    layer=layer,
                    width=stroke_width,
                    center_x=circle.center.x,
                    center_y=circle.center.y,
                    end_x=circle.end.x,
                    end_y=circle.end.y,
                )
            )

    except Exception:
        logger.debug(
            "Could not extract footprint geometry for %s",
            ic_module.get_full_name(),
            exc_info=True,
        )

    return pads, drawings


def _extract_net_name(pin: fabll.Node, sub_key: str | None = None) -> str | None:
    """Get the net name by finding the F.Net connected to the pin's electrical bus.

    Net names are stored on ``F.Net`` objects (via the ``has_net_name`` trait),
    not directly on pin line nodes.  We use ``get_named_net()`` to traverse
    the electrical bus and locate the net.

    For power pins, *sub_key* (``"hv"`` or ``"lv"``) selects the specific
    sub-interface so that each physical pad gets the correct net name.
    """

    def _net_name_from_electrical(electrical: fabll.Node) -> str | None:
        try:
            net = get_named_net(electrical)
            if net is not None and net.has_trait(F.has_net_name):
                return net.get_trait(F.has_net_name).get_name()
        except Exception:
            pass
        return None

    try:
        if pin.isinstance(F.ElectricLogic) or pin.isinstance(F.ElectricSignal):
            return _net_name_from_electrical(pin.line.get())
        elif pin.isinstance(F.ElectricPower):
            if sub_key:
                # Target the specific sub-interface for this pad
                try:
                    return _net_name_from_electrical(getattr(pin, sub_key).get())
                except Exception:
                    pass
            else:
                # Fallback: check hv first, then lv
                for sub_name in ["hv", "lv"]:
                    try:
                        name = _net_name_from_electrical(getattr(pin, sub_name).get())
                        if name is not None:
                            return name
                    except Exception:
                        pass
    except Exception:
        logger.debug("Could not extract net name for %s", pin.get_full_name())
    return None


def _lead_connects_to_other_lead(
    lead: fabll.Node,
    ic_module_full: str | None,
) -> bool:
    """Check if a lead electrically connects to any other lead outside the IC.

    Walks BFS from the lead and returns True if any connected node has the
    ``is_lead`` trait and is NOT part of the same IC module.
    """
    try:
        iface_trait = lead.try_get_trait(fabll.is_interface)
        if iface_trait is None:
            return False
        connected = iface_trait.get_connected(include_self=False)
    except Exception:
        return False

    for conn_node, _ in connected.items():
        if conn_node.try_get_trait(F.Lead.is_lead) is None:
            continue
        # It's a lead — check it's not in the same IC module
        conn_full = conn_node.get_full_name()
        if ic_module_full and conn_full.startswith(ic_module_full + "."):
            continue  # same IC module's lead
        return True
    return False


def _find_typed_pin_for_lead(
    lead: fabll.Node,
    component: fabll.Node,
    ic_module_full: str | None,
) -> tuple[fabll.Node | None, str | None]:
    """Trace outward from a lead to find the best typed interface it connects to.

    Walks the electrical connections from the lead, skipping other leads and
    nodes internal to the IC module.  For each candidate node, walks up the
    parent chain looking for an ``ElectricLogic``, ``ElectricSignal``, or
    ``ElectricPower`` ancestor.

    When multiple typed pins are found (e.g. ``io[17]`` and ``adc[17]`` for
    the same lead), picks the best one using priority:
      - ElectricLogic > ElectricSignal > ElectricPower
      - Shallower pins (fewer dots in relative name) win ties

    Returns ``(typed_pin, sub_key)`` where *sub_key* is ``"hv"``/``"lv"``
    for power sub-interfaces, or ``None`` otherwise.
    """
    comp_full = component.get_full_name()
    is_bare = ic_module_full == comp_full
    pin_types = (F.ElectricLogic, F.ElectricSignal, F.ElectricPower)
    type_priority = {F.ElectricLogic: 0, F.ElectricSignal: 1, F.ElectricPower: 2}

    try:
        iface_trait = lead.try_get_trait(fabll.is_interface)
        if iface_trait is None:
            return None, None
        connected = iface_trait.get_connected(include_self=False)
    except Exception:
        return None, None

    # Collect all candidate typed pins with their priority scores
    # Key: typed_pin full name → (score, typed_pin, sub_key)
    candidates: dict[str, tuple[tuple[int, int], fabll.Node, str | None]] = {}

    def _is_graph_artifact(name: str) -> bool:
        return bool(re.match(r"^0x[0-9a-fA-F]+", name))

    for conn_node, _ in connected.items():
        conn_full = conn_node.get_full_name()
        is_internal = conn_full.startswith(comp_full + ".")

        # For non-bare packages, only look inside the component
        if not is_bare and not is_internal:
            continue
        # Skip other leads
        if conn_node.try_get_trait(F.Lead.is_lead) is not None:
            continue
        # For non-bare packages, skip nodes inside the IC module
        if (
            not is_bare
            and ic_module_full
            and conn_full.startswith(ic_module_full + ".")
        ):
            continue
        # Skip graph artifacts (hex node IDs)
        if _is_graph_artifact(conn_node.get_name()):
            continue

        # Walk up from conn_node to find the nearest typed interface ancestor
        current = conn_node
        while True:
            parent_info = current.get_parent()
            if parent_info is None:
                break
            parent_node, name = parent_info
            parent_full = parent_node.get_full_name()

            # For non-bare packages, stop at the component boundary
            if not is_bare and not parent_full.startswith(comp_full):
                break

            found = False
            for pt in pin_types:
                if parent_node.isinstance(pt):
                    sub_key = None
                    if parent_node.isinstance(F.ElectricPower):
                        if name in ("hv", "vcc"):
                            sub_key = "hv"
                        elif name in ("lv", "gnd"):
                            sub_key = "lv"

                    dedup = f"{parent_full}:{sub_key or ''}"
                    if dedup not in candidates:
                        rel_name = _get_pin_name_relative_to(parent_node, component)
                        depth = rel_name.count(".")
                        # External typed pins get a depth penalty so internal
                        # ones are preferred when both exist
                        if not parent_full.startswith(comp_full):
                            depth += 100
                        tp = type_priority.get(pt, 99)
                        typed = parent_node.cast(pt)
                        candidates[dedup] = ((depth, tp), typed, sub_key)
                    found = True
                    break
            if found:
                break  # stop walking up once we find the nearest typed ancestor

            current = parent_node

    if not candidates:
        return None, None

    # Pick the candidate with the lowest score (shallowest, best type)
    best = min(candidates.values(), key=lambda x: x[0])
    return best[1], best[2]


def _find_package_pin_name_for_lead(
    lead: fabll.Node,
    ic_module: fabll.Node,
    ic_module_full: str,
) -> str | None:
    """Find the signal name from the package definition for a lead.

    Walks from the lead into the IC module/package to find the signal node
    it connects to.  For example, for an ESP32 lead at pad 4, this returns
    ``"IO4"`` (from ``signal IO4 ~ pin 4`` in the package ``.ato``).
    """
    try:
        iface_trait = lead.try_get_trait(fabll.is_interface)
        if iface_trait is None:
            return None
        connected = iface_trait.get_connected(include_self=False)
    except Exception:
        return None

    for conn_node, _ in connected.items():
        conn_full = conn_node.get_full_name()
        # Must be inside the IC module
        if not conn_full.startswith(ic_module_full + "."):
            continue
        # Skip other leads
        if conn_node.try_get_trait(F.Lead.is_lead) is not None:
            continue

        # Walk up to find the direct child of the IC module
        current = conn_node
        while True:
            parent_info = current.get_parent()
            if parent_info is None:
                break
            parent_node, child_name = parent_info
            parent_full = parent_node.get_full_name()
            if parent_full == ic_module_full:
                return child_name
            if not parent_full.startswith(ic_module_full + "."):
                break
            current = parent_node

    return None


# ---------------------------------------------------------------------------
#  Main extraction
# ---------------------------------------------------------------------------


def extract_pinout(
    app: fabll.Node,
    build_id: str | None = None,
) -> PinoutReport:
    """
    Extract pinout data for all components marked with `generate_pinout_details`.

    NOTE: Parameters must already be simplified by the solver before calling this
    (e.g. via the build pipeline). This function only reads solved values.
    """
    # Find all nodes with the generate_pinout_details trait
    implementors = fabll.Traits.get_implementors(
        F.generate_pinout_details.bind_typegraph(tg=app.tg), g=app.g
    )
    components_with_trait = unique(
        [fabll.Traits(impl).get_obj_raw() for impl in implementors],
        key=lambda node: node,
        custom_eq=lambda left, right: left.is_same(right),
    )

    if not components_with_trait:
        logger.info("No components with generate_pinout_details trait found")
        return PinoutReport(build_id=build_id)

    report = PinoutReport(build_id=build_id)
    app_prefix = app.get_full_name()

    for comp in components_with_trait:
        comp_full = comp.get_full_name()
        # Strip app root prefix for readability
        comp_name = (
            comp_full[len(app_prefix) + 1 :]
            if comp_full.startswith(app_prefix + ".")
            else comp_full
        )
        comp_type = type(comp).__name__

        # Try to get a better type name from the module trait
        if module_trait := comp.try_get_trait(fabll.is_module):
            try:
                comp_type = module_trait.get_module_locator()
            except Exception:
                pass

        pinout_comp = PinoutComponent(name=comp_name, type_name=comp_type)

        # Identify IC package leads for pad number extraction
        ic_leads, ic_module, ic_module_full = _find_ic_module(comp)

        # Extract footprint geometry if IC module found
        if ic_module is not None:
            pinout_comp.footprint_pads, pinout_comp.footprint_drawings = (
                _extract_footprint_geometry(ic_module)
            )

        # ----- Lead-first discovery -----
        # Each physical pad/lead is one row. From each lead we explore
        # outward to discover whatever metadata the graph provides.
        seen_typed_pins: set[str] = set()  # dedup: only first lead per typed pin

        for lead in ic_leads:
            lead_t = lead.try_get_trait(F.Lead.is_lead)
            if lead_t is None or not lead_t.has_trait(F.Lead.has_associated_pads):
                continue

            # --- Get the package-level signal name (e.g. "IO4", "EN", "GND") ---
            package_pin_name = (
                _find_package_pin_name_for_lead(lead, ic_module, ic_module_full)
                if ic_module is not None and ic_module_full is not None
                else None
            )

            # --- Try to find a typed interface connected to this lead ---
            typed_pin, sub_key = _find_typed_pin_for_lead(lead, comp, ic_module_full)

            if typed_pin is not None:
                typed_full = typed_pin.get_full_name()
                # Dedup key: skip alias typed pins that another lead
                # already resolved to.  For power pins, include sub_key
                # so hv and lv are treated separately.
                dedup_key = f"{typed_full}:{sub_key or ''}"
                if dedup_key in seen_typed_pins:
                    # Still emit the pad row, just reuse the metadata
                    pass
                seen_typed_pins.add(dedup_key)

                pin_name = package_pin_name
                signal_type = _detect_signal_type(typed_pin)
                direction = _detect_direction(typed_pin)
                interfaces = _find_interface_assignments(typed_pin, comp)
                interfaces.extend(
                    _find_interface_assignments_via_connections(typed_pin, comp)
                )
                interfaces = list(dict.fromkeys(interfaces))
                connected_to = _find_external_connections(typed_pin, comp, app_prefix)
                connected_to.extend(
                    _find_internal_connections(typed_pin, comp, ic_module_full)
                )
                voltage = _extract_voltage(typed_pin)

                # Power polarity
                if signal_type == "power" and sub_key:
                    polarity = "Power (VCC)" if sub_key == "hv" else "Power (GND)"
                    interfaces.insert(0, polarity)

            else:
                pin_name = package_pin_name
                signal_type = ""
                direction = "bidirectional"
                interfaces = []
                connected_to = []
                voltage = None
                sub_key = None

            # Check if this lead connects to another pad/lead in the design
            is_connected = _lead_connects_to_other_lead(lead, ic_module_full)

            # One row per physical pad on this lead
            for pad in lead_t.get_trait(F.Lead.has_associated_pads).get_pads():
                pad_number = pad.pad_number
                net_name = (
                    _extract_net_name(typed_pin, sub_key)
                    if typed_pin is not None
                    else None
                )
                notes: list[str] = []
                if not is_connected:
                    notes.append("Unconnected pin")

                pinout_comp.pins.append(
                    PinInfo(
                        pin_name=pin_name,
                        pin_number=pad_number,
                        net_name=net_name,
                        signal_type=signal_type,
                        direction=direction,
                        interfaces=list(interfaces),
                        connected_to=list(connected_to),
                        is_connected=is_connected,
                        voltage=voltage,
                        notes=notes,
                    )
                )

        # Sort pins by pad number (numerically) when available, then by name
        def _pin_sort_key(p: PinInfo) -> tuple[int, str, int, str]:
            if p.pin_number:
                try:
                    return (0, "", int(p.pin_number), p.pin_name)
                except ValueError:
                    pass
                # BGA-style alphanumeric (e.g. A1, D5, K10)
                m = re.match(r"^([A-Za-z]+)(\d+)$", p.pin_number)
                if m:
                    return (1, m.group(1).upper(), int(m.group(2)), p.pin_name)
                return (2, p.pin_number, 0, p.pin_name)
            return (3, "", 0, p.pin_name)

        pinout_comp.pins.sort(key=_pin_sort_key)

        # Component-level warnings
        unconnected_count = sum(
            1 for p in pinout_comp.pins if "Unconnected pin" in p.notes
        )
        if unconnected_count > 0:
            pinout_comp.warnings.append(f"{unconnected_count} unconnected pin(s)")

        report.components.append(pinout_comp)

    return report


# ---------------------------------------------------------------------------
#  Output writers
# ---------------------------------------------------------------------------


def export_pinout_json(
    app: fabll.Node,
    output_path: Path,
    build_id: str | None = None,
) -> PinoutReport:
    """Export pinout data as JSON."""
    report = extract_pinout(app, build_id=build_id)

    if not report.components:
        logger.info("No pinout data to export")
        return report

    if not output_path.parent.exists():
        os.makedirs(output_path.parent)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report.to_json())

    logger.info("Wrote pinout JSON to %s", output_path)
    return report


def export_pinout_csv(
    report: PinoutReport,
    output_path: Path,
) -> None:
    """Export pinout data as CSV."""
    if not report.components:
        return

    if not output_path.parent.exists():
        os.makedirs(output_path.parent)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Component",
                "Pin Name",
                "Pin Number",
                "Net Name",
                "Signal Type",
                "Direction",
                "Interfaces",
                "Connected To",
                "Voltage",
                "Notes",
            ]
        )

        for comp in report.components:
            for pin in comp.pins:
                writer.writerow(
                    [
                        comp.name,
                        pin.pin_name,
                        pin.pin_number or "",
                        pin.net_name or "",
                        pin.signal_type,
                        pin.direction,
                        "; ".join(pin.interfaces),
                        "; ".join(pin.connected_to),
                        pin.voltage or "",
                        "; ".join(pin.notes),
                    ]
                )

    logger.info("Wrote pinout CSV to %s", output_path)


def export_pinout_markdown(
    report: PinoutReport,
    output_path: Path,
) -> None:
    """Export pinout data as Markdown."""
    if not report.components:
        return

    if not output_path.parent.exists():
        os.makedirs(output_path.parent)

    lines: list[str] = ["# Pinout Report", ""]

    for comp in report.components:
        lines.append(f"## {comp.name}")
        lines.append(f"**Type:** {comp.type_name}")
        lines.append(f"**Total pins:** {len(comp.pins)}")
        lines.append("")

        if comp.warnings:
            lines.append("### Warnings")
            for w in comp.warnings:
                lines.append(f"- {w}")
            lines.append("")

        # Table header
        header = (
            "| Pin Name | Pin Number | Net Name | Signal Type"
            " | Interfaces | Connected To | Voltage | Notes |"
        )
        lines.append(header)
        lines.append(
            "|----------|------------|----------|-------------|"
            "------------|--------------|---------|-------|"
        )

        for pin in comp.pins:
            pin_number = pin.pin_number or "-"
            net_name = pin.net_name or "-"
            interfaces = ", ".join(pin.interfaces) if pin.interfaces else "-"
            connected = ", ".join(pin.connected_to) if pin.connected_to else "-"
            voltage = pin.voltage or "-"
            notes = ", ".join(pin.notes) if pin.notes else "-"

            lines.append(
                f"| {pin.pin_name} | {pin_number} | {net_name}"
                f" | {pin.signal_type} | {interfaces}"
                f" | {connected} | {voltage} | {notes} |"
            )

        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote pinout Markdown to %s", output_path)
