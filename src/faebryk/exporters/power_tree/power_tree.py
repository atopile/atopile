# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
import re
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver

logger = logging.getLogger(__name__)


def _strip_root_hex(name: str) -> str:
    """Strip leading hex node ID prefix like '0xF8C9.' from names."""
    stripped = re.sub(r"^0x[0-9A-Fa-f]+\.", "", name)
    return stripped if stripped else name


def _param_str(param_node: fabll.Node, solver: Solver) -> str:
    """Extract a parameter's solved value as a string."""
    try:
        param_trait = param_node.get_trait(F.Parameters.is_parameter)
        lit = solver.extract_superset(param_trait)
        if lit is not None:
            s = lit.pretty_str()
            if s and "\u211d" not in s and s != "?":
                return s
    except Exception:
        pass
    try:
        direct = param_node.try_extract_superset()
        if direct is not None:
            s = direct.pretty_str()
            if s and "\u211d" not in s and s != "?":
                return s
    except Exception:
        pass
    return "?"


def export_power_tree(
    app: fabll.Node,
    solver: Solver,
    *,
    mermaid_path: Path,
) -> None:
    """Generate Mermaid power tree (placeholder, kept for compatibility)."""
    mermaid_path.parent.mkdir(parents=True, exist_ok=True)
    mermaid_path.write_text("```mermaid\ngraph TD\n```\n", encoding="utf-8")


def export_power_tree_json(
    app: fabll.Node,
    solver: Solver,
    *,
    json_path: Path,
) -> None:
    """
    Export the power tree as a hierarchical JSON showing power flow.

    The tree shows:
    - Source nodes (power origins like USB connectors)
    - Converter nodes (regulators/LDOs that bridge two rails)
    - Sink nodes (power consumers like MCUs, sensors)

    A converter has a source on one bus and a sink on another.
    The tree flows: source -> converter -> sinks.
    """
    all_power = list(F.ElectricPower.bind_typegraph(tg=app.tg).get_instances())

    if not all_power:
        _write_json({"version": "1.0", "nodes": [], "edges": []}, json_path)
        return

    # Group ElectricPower interfaces by bus connectivity
    buses = fabll.is_interface.group_into_buses(all_power)
    buses = {
        root: members
        for root, members in buses.items()
        if len(members) > 1
    }

    # Cast and filter to shallow members only (skip cap.power etc.)
    bus_typed: dict[int, list[F.ElectricPower]] = {}
    ep_to_bus: dict[int, int] = {}  # ep id -> bus index

    for bus_idx, (bus_root, bus_members) in enumerate(buses.items()):
        members = []
        for raw in bus_members:
            try:
                ep = F.ElectricPower.bind_instance(raw.instance)
                name = _strip_root_hex(ep.get_full_name())
                if len(name.split(".")) <= 2:
                    members.append(ep)
                    ep_to_bus[id(ep)] = bus_idx
            except Exception:
                continue
        if members:
            bus_typed[bus_idx] = members

    # Classify each ElectricPower by trait
    all_sources: list[F.ElectricPower] = []
    all_sinks: list[F.ElectricPower] = []

    for members in bus_typed.values():
        for ep in members:
            if ep.has_trait(F.is_source):
                all_sources.append(ep)
            elif ep.has_trait(F.is_sink):
                all_sinks.append(ep)

    # Detect converters: modules that have BOTH a source and sink on
    # DIFFERENT buses. Group by parent module.
    def get_parent_module_id(ep: F.ElectricPower) -> str | None:
        parent = ep.get_parent()
        if not parent:
            return None
        return _strip_root_hex(parent[0].get_full_name())

    # Group sources and sinks by their parent module
    source_by_parent: dict[str, list[F.ElectricPower]] = {}
    sink_by_parent: dict[str, list[F.ElectricPower]] = {}

    for src in all_sources:
        pid = get_parent_module_id(src)
        if pid:
            source_by_parent.setdefault(pid, []).append(src)

    for snk in all_sinks:
        pid = get_parent_module_id(snk)
        if pid:
            sink_by_parent.setdefault(pid, []).append(snk)

    # A converter is a parent that has both sources and sinks on different buses
    converter_parents: set[str] = set()
    for pid in source_by_parent:
        if pid in sink_by_parent:
            # Check they're on different buses
            src_buses = {ep_to_bus.get(id(ep)) for ep in source_by_parent[pid]}
            snk_buses = {ep_to_bus.get(id(ep)) for ep in sink_by_parent[pid]}
            if src_buses != snk_buses:
                converter_parents.add(pid)

    # Build the tree nodes and edges
    json_nodes = []
    json_edges = []
    node_id_map: dict[int, str] = {}  # python id(ep) -> json node id
    counter = 0

    def make_node_id() -> str:
        nonlocal counter
        nid = f"n{counter}"
        counter += 1
        return nid

    # 1. Pure sources (not part of converters)
    for src in all_sources:
        pid = get_parent_module_id(src)
        if pid in converter_parents:
            continue
        nid = make_node_id()
        node_id_map[id(src)] = nid
        name = _strip_root_hex(src.get_full_name())
        json_nodes.append({
            "id": nid,
            "type": "source",
            "name": name,
            "voltage": _param_str(src.voltage.get(), solver),
            "max_current": _param_str(src.max_current.get(), solver),
        })

    # 2. Converters
    for pid in converter_parents:
        conv_sources = source_by_parent[pid]
        conv_sinks = sink_by_parent[pid]

        nid = make_node_id()

        # Get voltage in/out from the sink (input) and source (output)
        input_ep = conv_sinks[0] if conv_sinks else None
        output_ep = conv_sources[0] if conv_sources else None

        voltage_in = _param_str(input_ep.voltage.get(), solver) if input_ep else "?"
        voltage_out = _param_str(output_ep.voltage.get(), solver) if output_ep else "?"

        max_current_out = _param_str(output_ep.max_current.get(), solver) if output_ep else "?"

        json_nodes.append({
            "id": nid,
            "type": "converter",
            "name": pid,
            "voltage_in": voltage_in,
            "voltage_out": voltage_out,
            "max_current": max_current_out,
        })

        # Map all the converter's EPs to this node ID
        for ep in conv_sources + conv_sinks:
            node_id_map[id(ep)] = nid

    # 3. Pure sinks (not part of converters, not top-level rail aliases)
    for snk in all_sinks:
        pid = get_parent_module_id(snk)
        if pid in converter_parents:
            continue
        nid = make_node_id()
        node_id_map[id(snk)] = nid
        name = _strip_root_hex(snk.get_full_name())
        parent = snk.get_parent()
        parent_module_raw = parent[0].get_full_name() if parent else None
        parent_module = _strip_root_hex(parent_module_raw) if parent_module_raw else None
        if parent_module and re.match(r"^0x[0-9A-Fa-f]+$", parent_module):
            parent_module = None
        max_current = _param_str(snk.max_current.get(), solver)
        json_nodes.append({
            "id": nid,
            "type": "sink",
            "name": name,
            "parent_module": parent_module,
            "max_current": max_current,
        })

    # 4. Unclassified shallow EPs (no source/sink trait, not in converter)
    # These are typically the top-level rail aliases like power_3v3, power_5v
    # Skip them from the node list -- they're just connection intermediaries

    # 5. Build edges based on bus membership
    # For each bus, find the source(s) and connect to sinks + converter inputs
    for bus_idx, members in bus_typed.items():
        bus_source_nids = set()
        bus_sink_nids = set()

        for ep in members:
            ep_nid = node_id_map.get(id(ep))
            if ep_nid is None:
                continue

            # Find the node type
            node_data = next((n for n in json_nodes if n["id"] == ep_nid), None)
            if not node_data:
                continue

            if ep.has_trait(F.is_source):
                bus_source_nids.add(ep_nid)
            elif ep.has_trait(F.is_sink):
                bus_sink_nids.add(ep_nid)

        # Connect sources to sinks on the same bus
        for src_nid in bus_source_nids:
            for snk_nid in bus_sink_nids:
                if src_nid != snk_nid:
                    json_edges.append({
                        "from": src_nid,
                        "to": snk_nid,
                    })

    _write_json({
        "version": "1.0",
        "nodes": json_nodes,
        "edges": json_edges,
    }, json_path)
    logger.info("Wrote power tree JSON to %s", json_path)


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
