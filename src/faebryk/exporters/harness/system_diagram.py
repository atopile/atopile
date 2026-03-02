"""
Export harness data as a Mermaid system diagram.

Produces a high-level block diagram showing boards and the cables/harnesses
connecting them.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from faebryk.exporters.harness.harness_data import HarnessData

logger = logging.getLogger(__name__)


def _sanitize_id(name: str) -> str:
    """Sanitize a name for use as a Mermaid node ID."""
    return name.replace(".", "_").replace("[", "_").replace("]", "").replace(" ", "_")


def _build_connector_graph(
    data: HarnessData,
) -> dict[str, set[str]]:
    """Build an adjacency map of connector-to-connector connections."""
    adj: dict[str, set[str]] = defaultdict(set)
    for conn_info in data.connections:
        adj[conn_info.from_connector].add(conn_info.to_connector)
        adj[conn_info.to_connector].add(conn_info.from_connector)
    return adj


def _find_reachable_boards(
    start: str,
    adj: dict[str, set[str]],
    connector_to_board: dict[str, str | None],
) -> set[str]:
    """BFS from a connector to find all reachable boards."""
    visited: set[str] = set()
    queue = [start]
    boards: set[str] = set()

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        board = connector_to_board.get(current)
        if board:
            boards.add(board)

        for neighbor in adj.get(current, set()):
            if neighbor not in visited:
                queue.append(neighbor)

    return boards


def _find_cables_between(
    data: HarnessData,
    adj: dict[str, set[str]],
    connector_to_board: dict[str, str | None],
) -> dict[tuple[str, str], list[tuple[str | None, int]]]:
    """
    Find board-to-board connections by tracing through the connector graph.
    Returns {(board_a, board_b): [(cable_name, wire_count), ...]}.
    """
    board_connections: dict[
        tuple[str, str], list[tuple[str | None, int]]
    ] = defaultdict(list)

    # Count wires per connector pair
    pair_wires: dict[tuple[str, str], tuple[str | None, int]] = {}
    for conn_info in data.connections:
        key = (conn_info.from_connector, conn_info.to_connector)
        if key in pair_wires:
            cable, count = pair_wires[key]
            pair_wires[key] = (conn_info.via_cable or cable, count + 1)
        else:
            pair_wires[key] = (conn_info.via_cable, 1)

    # For each board connector, trace to find connected boards
    board_connectors = [
        name for name, board in connector_to_board.items() if board is not None
    ]

    seen_board_pairs: set[tuple[str, str]] = set()
    for conn_name in board_connectors:
        from_board = connector_to_board[conn_name]
        assert from_board is not None
        reachable = _find_reachable_boards(conn_name, adj, connector_to_board)
        reachable.discard(from_board)

        for to_board in reachable:
            pair = tuple(sorted([from_board, to_board]))
            if pair in seen_board_pairs:
                continue
            seen_board_pairs.add(pair)

            # Find cables along the path
            total_wires = 0
            cable_name: str | None = None
            for (fc, tc), (cn, wc) in pair_wires.items():
                # Check if this connection is on a path between the two boards
                fc_boards = _find_reachable_boards(fc, adj, connector_to_board)
                tc_boards = _find_reachable_boards(tc, adj, connector_to_board)
                if from_board in fc_boards and to_board in tc_boards:
                    if cn:
                        cable_name = cn
                    total_wires = max(total_wires, wc)

            board_connections[pair].append((cable_name, total_wires))

    return board_connections


def export_system_diagram(data: HarnessData, output_path: Path) -> None:
    """
    Export HarnessData as a Mermaid system diagram.

    Produces a graph showing boards as nodes and cables/connections as edges.

    Args:
        data: The extracted harness data.
        output_path: Path to write the Mermaid markdown file.
    """
    lines: list[str] = [
        "graph LR",
        '  classDef board fill:#1b3a4b,stroke:#5fa8d0,stroke-width:2px,color:#d7eaf5;',
        '  classDef cable fill:#4a3b1b,stroke:#d0a05f,stroke-width:2px,color:#f5ecd7;',
    ]

    # Add board nodes
    for board_name in data.boards:
        node_id = _sanitize_id(board_name)
        lines.append(f'  {node_id}["{board_name}"]')
        lines.append(f"  class {node_id} board")

    # Map connector names to board names
    connector_to_board: dict[str, str | None] = {}
    for conn in data.connectors:
        connector_to_board[conn.name] = conn.board_name

    # Build connector adjacency graph and trace board-to-board connections
    adj = _build_connector_graph(data)
    board_connections = _find_cables_between(data, adj, connector_to_board)

    # Add edges between boards
    for (board_a, board_b), cables in board_connections.items():
        id_a = _sanitize_id(board_a)
        id_b = _sanitize_id(board_b)

        for cable_name, wire_count in cables:
            if cable_name:
                label = f"{cable_name} ({wire_count} wires)"
            else:
                label = f"{wire_count} wires"
            lines.append(f'  {id_a} -- "{label}" --- {id_b}')

    # If no board connections found, show standalone boards
    if not board_connections and data.boards:
        lines.append("  %% No inter-board connections found")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "```mermaid\n" + "\n".join(lines) + "\n```\n", encoding="utf-8"
    )
    logger.info("Wrote system diagram to %s", output_path)
