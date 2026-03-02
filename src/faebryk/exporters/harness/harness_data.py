"""
Extract harness data from the design graph.

Walks the graph to find boards, connectors, cables, and their connections,
producing a HarnessData structure for export to WireViz or Mermaid.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


@dataclass
class ConnectorInfo:
    name: str
    board_name: str | None = None
    gender: str | None = None  # "plug" | "receptacle"
    pin_names: list[str] = field(default_factory=list)


@dataclass
class CableInfo:
    name: str
    wire_count: int = 0
    length_m: float | None = None


@dataclass
class ConnectionInfo:
    from_connector: str
    from_pin: str
    to_connector: str
    to_pin: str
    via_cable: str | None = None


@dataclass
class HarnessData:
    boards: list[str] = field(default_factory=list)
    connectors: list[ConnectorInfo] = field(default_factory=list)
    cables: list[CableInfo] = field(default_factory=list)
    connections: list[ConnectionInfo] = field(default_factory=list)


def _get_node_short_name(node: fabll.Node) -> str:
    """Get a short display name for a node."""
    return node.get_full_name(include_uuid=False, types=False)


def _find_trait_owners(
    app: fabll.Node,
    trait_type: type[fabll.Node],
) -> list[fabll.Node]:
    """Find all nodes that have the given trait."""
    implementors = fabll.Traits.get_implementors(
        trait_type.bind_typegraph(app.tg), g=app.g
    )
    return [fabll.Traits(impl).get_obj_raw() for impl in implementors]


def _get_connector_gender(connector: fabll.Node) -> str | None:
    """Determine connector gender from traits."""
    if connector.has_trait(F.is_connector_plug):
        return "plug"
    if connector.has_trait(F.is_connector_receptacle):
        return "receptacle"
    return None


def _find_owner_board(
    node: fabll.Node,
    boards: list[fabll.Node],
) -> fabll.Node | None:
    """Find which board a node belongs to."""
    for board in boards:
        if node.is_same(board) or node.is_descendant_of(board):
            return board
    return None


def _collect_electrical_children(node: fabll.Node) -> list[fabll.Node]:
    """Collect Electrical interface children from a node."""
    return node.get_children(direct_only=True, types=F.Electrical)


def extract_harness_data(app: fabll.Node) -> HarnessData:
    """
    Extract harness information from a multi-board design.

    Args:
        app: The top-level application node (should have is_multiboard trait).

    Returns:
        HarnessData with boards, connectors, cables, and connections.
    """
    data = HarnessData()

    # Find all boards
    boards = _find_trait_owners(app, F.is_board)
    data.boards = [_get_node_short_name(b) for b in boards]
    logger.info(f"Found {len(boards)} boards: {data.boards}")

    # Find all harnesses
    harnesses = _find_trait_owners(app, F.is_harness)
    logger.info(f"Found {len(harnesses)} harnesses")

    # Find all connectors (from Connector4Pin instances)
    connector_modules = F.Connector4Pin.bind_typegraph(tg=app.tg).get_instances(
        g=app.tg.get_graph_view()
    )

    for conn in connector_modules:
        board = _find_owner_board(conn, boards)
        gender = _get_connector_gender(conn)

        # Collect pin names from board_side
        pin_names: list[str] = []
        for i in range(4):
            pin_names.append(f"pin{i + 1}")

        info = ConnectorInfo(
            name=_get_node_short_name(conn),
            board_name=_get_node_short_name(board) if board else None,
            gender=gender,
            pin_names=pin_names,
        )
        data.connectors.append(info)

    logger.info(f"Found {len(data.connectors)} connectors")

    # Find all cables (from Cable4Wire instances)
    cable_modules = F.Cable4Wire.bind_typegraph(tg=app.tg).get_instances(
        g=app.tg.get_graph_view()
    )

    for cable in cable_modules:
        wire_count = len(cable.end_a)
        info = CableInfo(
            name=_get_node_short_name(cable),
            wire_count=wire_count,
            length_m=None,  # Would need solver to extract
        )
        data.cables.append(info)

    logger.info(f"Found {len(data.cables)} cables")

    # Trace connections between connectors via cables
    # Collect all wire_side and end_a/end_b electricals
    all_electricals: set[fabll.Node] = set()

    connector_pin_map: dict[fabll.Node, tuple[str, str]] = {}
    # Map each Electrical to (connector_name, pin_name)
    for conn in connector_modules:
        conn_name = _get_node_short_name(conn)
        for i, pin_field in enumerate(conn.wire_side):
            pin_node = pin_field.get()
            all_electricals.add(pin_node)
            connector_pin_map[pin_node] = (conn_name, f"pin{i + 1}")
        for i, pin_field in enumerate(conn.board_side):
            pin_node = pin_field.get()
            all_electricals.add(pin_node)
            connector_pin_map[pin_node] = (conn_name, f"pin{i + 1}")

    cable_pin_map: dict[fabll.Node, tuple[str, str]] = {}
    for cable in cable_modules:
        cable_name = _get_node_short_name(cable)
        for i, pin_field in enumerate(cable.end_a):
            pin_node = pin_field.get()
            all_electricals.add(pin_node)
            cable_pin_map[pin_node] = (cable_name, f"wire{i + 1}")
        for i, pin_field in enumerate(cable.end_b):
            pin_node = pin_field.get()
            all_electricals.add(pin_node)
            cable_pin_map[pin_node] = (cable_name, f"wire{i + 1}")

    if not all_electricals:
        return data

    # Group into buses
    buses = fabll.is_interface.group_into_buses(all_electricals)

    # For each bus, find connector-to-connector connections (possibly via cable)
    seen_connections: set[tuple[str, str, str, str]] = set()

    for bus_members in buses.values():
        # Find connector pins in this bus
        conn_pins_in_bus: list[tuple[str, str]] = []
        cable_in_bus: str | None = None

        for member in bus_members:
            if member in connector_pin_map:
                conn_pins_in_bus.append(connector_pin_map[member])
            if member in cable_pin_map:
                cable_name, _ = cable_pin_map[member]
                cable_in_bus = cable_name

        # Create connections between all connector pin pairs in this bus
        for i in range(len(conn_pins_in_bus)):
            for j in range(i + 1, len(conn_pins_in_bus)):
                from_conn, from_pin = conn_pins_in_bus[i]
                to_conn, to_pin = conn_pins_in_bus[j]

                key = (from_conn, from_pin, to_conn, to_pin)
                reverse_key = (to_conn, to_pin, from_conn, from_pin)
                if key in seen_connections or reverse_key in seen_connections:
                    continue
                seen_connections.add(key)

                data.connections.append(
                    ConnectionInfo(
                        from_connector=from_conn,
                        from_pin=from_pin,
                        to_connector=to_conn,
                        to_pin=to_pin,
                        via_cable=cable_in_bus,
                    )
                )

    logger.info(f"Found {len(data.connections)} connections")
    return data
