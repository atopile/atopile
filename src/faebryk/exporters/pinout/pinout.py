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


def _is_from_child_module(pin: fabll.Node, component: fabll.Node) -> bool:
    """Check if a pin belongs to an internal sub-module (e.g., capacitor, resistor).

    Walks from the pin up toward the component. If any intermediate node in
    the path has the ``is_module`` trait, the pin is internal implementation
    detail and should not appear in the pinout.
    """
    comp_full = component.get_full_name()
    current = pin
    while True:
        parent_info = current.get_parent()
        if parent_info is None:
            return False
        parent_node, _ = parent_info
        parent_full = parent_node.get_full_name()
        # Reached the component itself – no intermediate module found
        if parent_full == comp_full:
            return False
        # Left the component's namespace
        if not parent_full.startswith(comp_full + "."):
            return False
        # Intermediate node is a module → pin is internal
        if parent_node.try_get_trait(fabll.is_module):
            return True
        current = parent_node


def _has_connections(pin: fabll.Node) -> bool:
    """Check if a pin has any electrical connections (is not floating).

    For ElectricLogic / ElectricSignal, checks the signal *line*.
    For ElectricPower, checks the top-level interface.
    """
    try:
        if pin.isinstance(F.ElectricLogic) or pin.isinstance(F.ElectricSignal):
            line_iface = pin.line.get()._is_interface.get()
            connected = line_iface.get_connected(include_self=False)
            return bool(connected)
        elif pin.isinstance(F.ElectricPower):
            iface = pin._is_interface.get()
            connected = iface.get_connected(include_self=False)
            return bool(connected)
    except Exception:
        pass
    return False


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

        line_iface = pin.line.get()._is_interface.get()
        connected = line_iface.get_connected(include_self=False)

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
            line_iface = pin.line.get()._is_interface.get()
            _collect(line_iface.get_connected(include_self=False))
        except Exception:
            logger.debug("Could not get connections for %s", pin.get_full_name())
    elif pin.isinstance(F.ElectricPower):
        try:
            iface = pin._is_interface.get()
            _collect(iface.get_connected(include_self=False))
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
            line_iface = pin.line.get()._is_interface.get()
            _collect(line_iface.get_connected(include_self=False))
        except Exception:
            pass
    elif pin.isinstance(F.ElectricPower):
        try:
            iface = pin._is_interface.get()
            _collect(iface.get_connected(include_self=False))
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

        # Extract drawings from silk screen and fabrication layers
        drawing_layers = {"F.SilkS", "B.SilkS", "F.Fab", "B.Fab"}

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


def _extract_pin_numbers(
    pin: fabll.Node,
    component: fabll.Node,
    ic_leads: list[fabll.Node],
) -> list[tuple[str, str | None]]:
    """Extract physical pad numbers by tracing to IC package leads.

    Returns a list of ``(pad_number, sub_key)`` tuples.  *sub_key* is
    ``"hv"`` or ``"lv"`` for ``ElectricPower`` pins (needed to resolve the
    correct net name per pad), or ``None`` for signal pins.

    Each physical pad gets its own entry (1 pad = 1 row).
    """
    comp_full = component.get_full_name()
    results: list[tuple[str, str | None]] = []

    def _is_ic_lead(node: fabll.Node) -> bool:
        return any(node.is_same(lead) for lead in ic_leads)

    def _check_leads_from_interface(iface: fabll.Node, sub_key: str | None) -> None:
        try:
            connected = iface.get_connected(include_self=False)
            for conn_node, _path in connected.items():
                if not _is_ic_lead(conn_node):
                    continue
                conn_full = conn_node.get_full_name()
                if not conn_full.startswith(comp_full + "."):
                    continue
                lead_t = conn_node.get_trait(F.Lead.is_lead)
                if lead_t.has_trait(F.Lead.has_associated_pads):
                    for pad in lead_t.get_trait(F.Lead.has_associated_pads).get_pads():
                        results.append((pad.pad_number, sub_key))
        except Exception:
            pass

    try:
        if pin.isinstance(F.ElectricLogic) or pin.isinstance(F.ElectricSignal):
            _check_leads_from_interface(pin.line.get()._is_interface.get(), None)
        elif pin.isinstance(F.ElectricPower):
            for sub_name in ["hv", "lv"]:
                try:
                    sub = getattr(pin, sub_name).get()
                    _check_leads_from_interface(sub._is_interface.get(), sub_name)
                except Exception:
                    pass
    except Exception:
        logger.debug("Could not extract pin numbers for %s", pin.get_full_name())

    # Deduplicate by pad number, preserving order, then sort numerically
    seen: set[str] = set()
    unique_results: list[tuple[str, str | None]] = []
    for pad_num, sub_key in results:
        if pad_num not in seen:
            seen.add(pad_num)
            unique_results.append((pad_num, sub_key))
    unique_results.sort(
        key=lambda x: int(x[0]) if x[0].isdigit() else float("inf"),
    )
    return unique_results


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

        # Collect all pin-like children (ElectricLogic, ElectricSignal, ElectricPower)
        pin_types = (F.ElectricLogic, F.ElectricSignal, F.ElectricPower)

        all_pins: list[fabll.Node] = []
        for pin_type in pin_types:
            all_pins.extend(
                comp.get_children(
                    direct_only=False,
                    types=pin_type,
                    include_root=False,
                    required_trait=fabll.is_interface,
                )
            )

        # Filter out sub-pins that are children of other pin-like types
        # e.g., gpio[0].reference (ElectricPower) is a child of gpio[0]
        # (ElectricLogic) and should not be a separate entry.
        # Also filter out internal/private nodes (names containing '._').
        pin_full_names = {p.get_full_name() for p in all_pins}
        filtered_pins = []
        for pin in all_pins:
            pin_name = _get_pin_name_relative_to(pin, comp)
            # Skip internal/private nodes
            if "._" in pin_name:
                continue
            parent_info = pin.get_parent()
            if parent_info is not None:
                parent_node, _child_name = parent_info
                if parent_node.get_full_name() in pin_full_names:
                    continue  # Skip: parent is also a pin-type node
            filtered_pins.append(pin)

        # --- Additional filters ---

        # Filter: Remove pins from internal sub-modules (capacitors,
        # resistors, the IC package, etc.).  These are implementation
        # details, not exposed module interfaces.
        filtered_pins = [p for p in filtered_pins if not _is_from_child_module(p, comp)]

        # Filter: Remove floating pins (no electrical connections at all).
        # This catches unmapped GPIO indices (e.g. io[22-34] on the
        # ESP32-WROOM) and unused protocol sub-pins (e.g. uart0.cts).
        filtered_pins = [p for p in filtered_pins if _has_connections(p)]

        # Filter: Remove ElectricSignal aliases that duplicate an
        # ElectricLogic pin they are connected to (e.g. touch[1] and
        # adc[1] are aliases of io[1]).
        logic_line_names: set[str] = set()
        for pin in filtered_pins:
            if pin.isinstance(F.ElectricLogic):
                try:
                    logic_line_names.add(pin.line.get().get_full_name())
                except Exception:
                    pass

        deduped_pins: list[fabll.Node] = []
        for pin in filtered_pins:
            # Skip ElectricSignal aliases (e.g. touch[1] → io[1])
            if pin.isinstance(F.ElectricSignal):
                try:
                    line_iface = pin.line.get()._is_interface.get()
                    connected = line_iface.get_connected(include_self=False)
                    is_alias = any(
                        cn.get_full_name() in logic_line_names
                        for cn, _ in connected.items()
                    )
                    if is_alias:
                        continue
                except Exception:
                    pass

            # Skip ElectricLogic pins that are aliases of another
            # ElectricLogic already in the list.  This catches:
            #   - Known interface aliases (i2c.sda → io[8], spi.mosi → io[11])
            #   - Standalone aliases  (spi_cs → io[10])
            # We only skip non-array pins (e.g. "spi_cs") when they're
            # connected to an array pin (e.g. "io[10]") to avoid removing
            # the canonical io[] entries.
            if pin.isinstance(F.ElectricLogic):
                rel = _get_pin_name_relative_to(pin, comp)
                is_array_pin = bool(re.match(r"^(\w+)\[\d+\]$", rel))
                if not is_array_pin:
                    try:
                        own_line = pin.line.get().get_full_name()
                        line_iface = pin.line.get()._is_interface.get()
                        connected = line_iface.get_connected(include_self=False)
                        is_alias = any(
                            cn.get_full_name() in logic_line_names
                            and cn.get_full_name() != own_line
                            for cn, _ in connected.items()
                        )
                        if is_alias:
                            continue
                    except Exception:
                        pass

            deduped_pins.append(pin)
        filtered_pins = deduped_pins

        for pin in filtered_pins:
            pad_entries = _extract_pin_numbers(pin, comp, ic_leads)
            base_signal_type = _detect_signal_type(pin)
            direction = _detect_direction(pin)
            interfaces = _find_interface_assignments(pin, comp)
            interfaces.extend(_find_interface_assignments_via_connections(pin, comp))
            # Deduplicate while preserving order
            interfaces = list(dict.fromkeys(interfaces))
            connected_to = _find_external_connections(pin, comp, app_prefix)
            connected_to.extend(_find_internal_connections(pin, comp, ic_module_full))
            voltage = _extract_voltage(pin)

            # Emit one row per physical pad (1 pin = 1 row)
            if not pad_entries:
                pad_entries = [(None, None)]

            for pad_number, sub_key in pad_entries:
                net_name = _extract_net_name(pin, sub_key)
                signal_type = base_signal_type

                # Add power polarity to interfaces for power pads
                pad_interfaces = list(interfaces)
                if base_signal_type == "power" and sub_key:
                    polarity = "Power (VCC)" if sub_key == "hv" else "Power (GND)"
                    pad_interfaces.insert(0, polarity)

                notes: list[str] = []
                if not connected_to:
                    notes.append("Unconnected pin")
                pin_name = (
                    pad_number if pad_number else _get_pin_name_relative_to(pin, comp)
                )

                pin_info = PinInfo(
                    pin_name=pin_name,
                    pin_number=pad_number,
                    net_name=net_name,
                    signal_type=signal_type,
                    direction=direction,
                    interfaces=pad_interfaces,
                    connected_to=connected_to,
                    voltage=voltage,
                    notes=notes,
                )
                pinout_comp.pins.append(pin_info)

        # Sort pins by pad number (numerically) when available, then by name
        def _pin_sort_key(p: PinInfo) -> tuple[int, str]:
            if p.pin_number:
                try:
                    return (int(p.pin_number), p.pin_name)
                except ValueError:
                    pass
            return (9999, p.pin_name)

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
