# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Pinout exporter: generates pinout reports (JSON, CSV, Markdown) for components
marked with the `generate_pinout_details` trait.

Traverses the graph to extract pin names, signal types, interface assignments,
external connections, and net names.
"""

import csv
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.nets import get_named_net

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
class PinInfo:
    pin_name: str  # e.g., "gpio[0]", "i2c.scl"
    pin_number: str | None = None  # Physical pin/pad number if available
    net_name: str | None = None  # Net name if assigned
    signal_type: str = "digital"  # "digital", "analog", "power", "ground", "nc"
    interfaces: list[str] = field(default_factory=list)  # ["I2C (SDA)", "ADC1[0]"]
    is_connected: bool = False  # True if lead connects to another pad/lead
    notes: list[str] = field(default_factory=list)  # Warnings, capability notes


@dataclass
class PinoutComponent:
    name: str  # Component instance name (e.g., "micro")
    type_name: str  # Type name (e.g., "ESP32_C3_MINI_1")
    footprint_uuid: str | None = None  # matches layout footprint.uuid
    pins: list[PinInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


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


def _detect_signal_type(pin: fabll.Node) -> str:
    """Determine signal type based on the pin's class."""
    if pin.isinstance(F.ElectricPower):
        return "power"
    if pin.isinstance(F.ElectricLogic):
        return "digital"
    if pin.isinstance(F.ElectricSignal):
        return "analog"
    return "digital"


def _component_node(component_t: F.generate_pinout_details) -> fabll.Node:
    return fabll.Traits(component_t).get_obj_raw()


def _lead_node(lead_t: F.Lead.is_lead) -> fabll.Node:
    return fabll.Traits(lead_t).get_obj_raw()


def _get_scope_root(component: fabll.Node) -> fabll.Node:
    parent_info = component.get_parent()
    return parent_info[0] if parent_info is not None else component


def _is_descendant_or_self(full_name: str, root_full: str) -> bool:
    return full_name == root_full or full_name.startswith(root_full + ".")


def _iter_scoped_parent_edges(node: fabll.Node, scope_full: str):
    current = node
    while True:
        parent_info = current.get_parent()
        if parent_info is None:
            return
        parent_node, child_name = parent_info
        if not _is_descendant_or_self(parent_node.get_full_name(), scope_full):
            return
        yield parent_node, child_name
        current = parent_node


def _populate_interface(
    pin: fabll.Node,
    component_t: F.generate_pinout_details,
    sub_key: str | None = None,
) -> list[str]:
    """Populate interface labels for a typed pin.

    Includes:
    - direct known-interface ancestry (e.g. I2C (SDA))
    - known interfaces found via internal connections
    - capability labels from connected ElectricSignal groups (e.g. TOUCH (1))
    - synthetic power labels for hv/lv power pads

    Returns deduplicated labels in insertion order.
    """
    interfaces: list[str] = []
    component = _component_node(component_t)
    scope_root = _get_scope_root(component)
    scope_full = scope_root.get_full_name()

    # Direct hierarchy labels: e.g. i2c.sda -> I2C (SDA)
    for parent_node, child_name in _iter_scoped_parent_edges(pin, scope_full):
        for iface_type, iface_label in KNOWN_INTERFACES.items():
            if parent_node.isinstance(iface_type):
                interfaces.append(f"{iface_label} ({child_name.upper()})")
                break

    if pin.isinstance(F.ElectricLogic) or pin.isinstance(F.ElectricSignal):
        connected = pin.line.get().get_trait(fabll.is_interface).get_connected()

        for conn_node, _ in connected.items():
            conn_full = conn_node.get_full_name()
            if not _is_descendant_or_self(conn_full, scope_full):
                continue

            parent_info = conn_node.get_parent()
            if parent_info is None:
                continue
            connected_pin = parent_info[0]

            path_parts: list[str] = []
            found_known = False

            for parent_node, child_name in _iter_scoped_parent_edges(
                connected_pin, scope_full
            ):
                path_parts.append(child_name)
                for iface_type, iface_label in KNOWN_INTERFACES.items():
                    if parent_node.isinstance(iface_type):
                        role = (
                            path_parts[0]
                            if len(path_parts) <= 1
                            else ".".join(reversed(path_parts[:-1]))
                        )
                        interfaces.append(f"{iface_label} ({role.upper()})")
                        found_known = True
                        break

            if not found_known and connected_pin.isinstance(F.ElectricSignal):
                rel = connected_pin.relative_address(scope_root)
                m = re.match(r"^(\w+)\[(\d+)\]$", rel)
                if m:
                    interfaces.append(f"{m.group(1).upper()} ({m.group(2)})")

    if pin.isinstance(F.ElectricPower) and sub_key:
        interfaces.insert(0, "Power (VCC)" if sub_key == "hv" else "Power (GND)")

    return list(dict.fromkeys(interfaces))


def _get_footprint_uuid(component_t: F.generate_pinout_details) -> str | None:
    """Get the PCB footprint UUID for the IC module."""
    component = _component_node(component_t)
    if footprint_trait := component.try_get_trait(
        F.Footprints.has_associated_footprint
    ):
        graph_fp = footprint_trait.get_footprint()
        kicad_footprint = graph_fp.try_get_trait(
            F.KiCadFootprints.has_associated_kicad_pcb_footprint
        )
        if kicad_footprint is None:
            return None
        footprint = kicad_footprint.get_footprint()
        return str(footprint.uuid) if footprint.uuid is not None else None
    return None


def _lead_connects_to_other_lead(
    lead_t: F.Lead.is_lead,
    component_t: F.generate_pinout_details,
) -> bool:
    """Check if a lead electrically connects to any other lead outside the IC"""
    lead = _lead_node(lead_t)
    component = _component_node(component_t)
    connected = lead.get_trait(fabll.is_interface).get_connected(include_self=False)
    return any(
        conn_node.try_get_trait(F.Lead.is_lead) is not None
        and not conn_node.is_descendant_of(component)
        for conn_node in connected
    )


def _find_typed_pin_for_lead(
    lead_t: F.Lead.is_lead,
    component_t: F.generate_pinout_details,
) -> tuple[fabll.Node | None, str | None]:
    """Trace outward from a lead to find the best typed interface it connects to.

    Walks the electrical connections from the lead, skipping other leads and
    nodes outside the package context (the package node and its direct owner
    scope). For each candidate node, walks up the parent chain looking for an
    ``ElectricLogic``, ``ElectricSignal``, or ``ElectricPower`` ancestor.

    When multiple typed pins are found (e.g. ``io[17]`` and ``adc[17]`` for
    the same lead), picks the best one using priority:
      - ElectricLogic > ElectricSignal > ElectricPower
      - Shallower pins (fewer dots in relative name) win ties

    Returns ``(typed_pin, sub_key)`` where *sub_key* is ``"hv"``/``"lv"`` for
    power sub-interfaces, or ``None`` otherwise.
    """
    lead = _lead_node(lead_t)
    component = _component_node(component_t)
    comp_full = component.get_full_name()
    scope_root = _get_scope_root(component)
    scope_full = scope_root.get_full_name()
    pin_types = (F.ElectricLogic, F.ElectricSignal, F.ElectricPower)
    type_priority = {F.ElectricLogic: 0, F.ElectricSignal: 1, F.ElectricPower: 2}

    connected = lead.get_trait(fabll.is_interface).get_connected(include_self=False)

    # Collect all candidate typed pins with their priority scores
    # Key: typed_pin full name → (score, typed_pin, sub_key)
    candidates: dict[str, tuple[tuple[int, int, int], fabll.Node, str | None]] = {}

    def _is_graph_artifact(name: str) -> bool:
        return bool(re.match(r"^0x[0-9a-fA-F]+", name))

    for conn_node, _ in connected.items():
        conn_full = conn_node.get_full_name()
        if not _is_descendant_or_self(conn_full, scope_full):
            continue
        # Skip other leads
        if conn_node.try_get_trait(F.Lead.is_lead) is not None:
            continue
        # Skip graph artifacts (hex node IDs)
        if _is_graph_artifact(conn_node.get_name()):
            continue
        # Net extraction only works for electrical interfaces.
        if not conn_node.isinstance(F.Electrical):
            continue

        # Walk up from conn_node to find the nearest typed interface ancestor
        found = False
        for parent_node, name in _iter_scoped_parent_edges(conn_node, scope_full):
            parent_full = parent_node.get_full_name()
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
                        scope_penalty = (
                            0 if _is_descendant_or_self(parent_full, comp_full) else 1
                        )
                        rel_root = component if scope_penalty == 0 else scope_root
                        rel_name = parent_node.relative_address(rel_root)
                        depth = rel_name.count(".")
                        tp = type_priority.get(pt, 99)
                        candidates[dedup] = (
                            (scope_penalty, depth, tp),
                            parent_node.cast(pt),
                            sub_key,
                        )
                    found = True
                    break
            if found:
                break  # stop walking up once we find the nearest typed ancestor

    if not candidates:
        return None, None

    # Pick the candidate with the lowest score (shallowest, best type)
    best = min(candidates.values(), key=lambda x: x[0])
    return best[1], best[2]


def _find_package_pin_name_for_lead(
    lead_t: F.Lead.is_lead,
    component_t: F.generate_pinout_details,
) -> str | None:
    """Find the signal name from the component definition for a lead.

    Walks from the lead into the component to find the signal node
    it connects to.  For example, for an ESP32 lead at pad 4, this returns
    ``"IO4"`` (from ``signal IO4 ~ pin 4`` in the package ``.ato``).
    """
    lead = _lead_node(lead_t)
    component = _component_node(component_t)
    connected = lead.get_trait(fabll.is_interface).get_connected(include_self=False)

    for conn_node in connected:
        if conn_node.try_get_trait(
            F.Lead.is_lead
        ) is not None or not conn_node.is_descendant_of(component):
            continue
        return conn_node.relative_address(component).split(".", 1)[0]

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
    # Find all generate_pinout_details trait instances
    component_traits = sorted(
        fabll.Traits.get_implementors(
            F.generate_pinout_details.bind_typegraph(tg=app.tg), g=app.g
        ),
        key=lambda trait: _component_node(trait).get_full_name(include_uuid=False),
    )

    if not component_traits:
        logger.info("No components with generate_pinout_details trait found")
        return PinoutReport(build_id=build_id)

    report = PinoutReport(build_id=build_id)
    for component_t in component_traits:
        comp = _component_node(component_t)
        comp_full = comp.get_full_name()
        comp_name = comp.relative_address(app)
        comp_type = comp.get_trait(fabll.is_module).get_module_locator()

        pinout_comp = PinoutComponent(name=comp_name, type_name=comp_type)

        leads = comp.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Lead.is_lead,
        )
        if not leads:
            raise ValueError(f"{comp_full} has no leads for pinout export")
        lead_traits = [lead.get_trait(F.Lead.is_lead) for lead in leads]
        pinout_comp.footprint_uuid = _get_footprint_uuid(component_t)

        # ----- Lead-first discovery -----
        # Each physical pad/lead is one row. From each lead we explore
        # outward to discover whatever metadata the graph provides.
        for lead_t in lead_traits:
            lead = _lead_node(lead_t)
            pads_t = lead_t.get_trait(F.Lead.has_associated_pads)

            # --- Get the package-level signal name (e.g. "IO4", "EN", "GND") ---
            package_pin_name = _find_package_pin_name_for_lead(lead_t, component_t)
            pin_name = package_pin_name or lead.get_name()

            # --- Try to find a typed interface connected to this lead ---
            typed_pin, sub_key = _find_typed_pin_for_lead(lead_t, component_t)
            signal_type = (
                _detect_signal_type(typed_pin) if typed_pin is not None else "digital"
            )
            interfaces = (
                _populate_interface(typed_pin, component_t, sub_key)
                if typed_pin is not None
                else []
            )

            # Check if this lead connects to another pad/lead in the design
            is_connected = _lead_connects_to_other_lead(lead_t, component_t)
            net = get_named_net(lead.cast(F.Electrical))
            net_name = net.get_name() if net is not None else None

            # One row per physical pad on this lead
            for pad in pads_t.get_pads():
                pad_number = pad.pad_number
                notes = [] if is_connected else ["Unconnected pin"]

                pinout_comp.pins.append(
                    PinInfo(
                        pin_name=pin_name,
                        pin_number=pad_number,
                        net_name=net_name,
                        signal_type=signal_type,
                        interfaces=list(interfaces),
                        is_connected=is_connected,
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

    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Component",
                "Pin Name",
                "Pin Number",
                "Net Name",
                "Signal Type",
                "Interfaces",
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
                        "; ".join(pin.interfaces),
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

    output_path.parent.mkdir(parents=True, exist_ok=True)

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
            "| Pin Name | Pin Number | Net Name | Signal Type | Interfaces | Notes |"
        )
        lines.append(header)
        lines.append(
            "|----------|------------|----------|-------------|------------|-------|"
        )

        for pin in comp.pins:
            pin_number = pin.pin_number or "-"
            net_name = pin.net_name or "-"
            interfaces = ", ".join(pin.interfaces) if pin.interfaces else "-"
            notes = ", ".join(pin.notes) if pin.notes else "-"

            lines.append(
                f"| {pin.pin_name} | {pin_number} | {net_name}"
                f" | {pin.signal_type} | {interfaces}"
                f" | {notes} |"
            )

        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote pinout Markdown to %s", output_path)
