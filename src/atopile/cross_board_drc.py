# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Cross-board DRC: detects electrical connections that span multiple boards
without passing through a cable module.
"""

from dataclasses import dataclass

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CrossBoardViolation:
    """A cross-board connection that doesn't pass through a cable."""

    signal_path: str
    boards: list[str]
    message: str


def _get_ancestor_board(
    node: fabll.Node,
    board_set: set[int],
) -> fabll.Node | None:
    """Walk up from `node` to find which board (if any) it belongs to."""
    current = node
    while True:
        parent_result = current.get_parent()
        if parent_result is None:
            return None
        parent_node = parent_result[0]
        uid = parent_node.instance.node().get_uuid()
        if uid in board_set:
            return parent_node
        current = parent_node


def check_cross_board_connections(
    app: fabll.Node,
    boards: list[fabll.Node],
) -> list[CrossBoardViolation]:
    """
    Check for electrical connections spanning multiple boards
    without going through a cable module.

    Algorithm:
    1. Build a set of board node UUIDs for fast ancestry lookup
    2. Build a set of cable descendant Electrical UUIDs
    3. For each Electrical with is_interface, find its connected bus
    4. Determine which boards participate in that bus
    5. If 2+ boards and no cable electricals in the bus, record a violation
    """
    if len(boards) < 2:
        return []

    # Build board UUID set
    board_uuids: set[int] = set()
    board_by_uuid: dict[int, fabll.Node] = {}
    for board in boards:
        uid = board.instance.node().get_uuid()
        board_uuids.add(uid)
        board_by_uuid[uid] = board

    # Build cable electrical UUID set
    cables = list(
        app.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.is_cable,
        )
    )
    cable_electrical_uuids: set[int] = set()
    for cable in cables:
        for child in cable.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=fabll.is_interface,
        ):
            cable_electrical_uuids.add(child.instance.node().get_uuid())

    # Collect all Electricals that are interface nodes
    all_interfaces = app.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=fabll.is_interface,
        include_root=False,
    )

    # Track which interfaces we've already checked (via bus grouping)
    checked_uuids: set[int] = set()
    violations: list[CrossBoardViolation] = []

    for iface in all_interfaces:
        iface_uid = iface.instance.node().get_uuid()
        if iface_uid in checked_uuids:
            continue

        # Get the connected bus for this interface
        is_iface_trait = iface.get_trait(fabll.is_interface)
        connected = is_iface_trait.get_connected(include_self=True)
        bus_members = list(connected.keys())

        # Mark all members as checked
        for member in bus_members:
            checked_uuids.add(member.instance.node().get_uuid())

        # Determine which boards participate in this bus
        participating_boards: dict[int, fabll.Node] = {}
        has_cable_path = False

        for member in bus_members:
            member_uid = member.instance.node().get_uuid()

            # Check if this member is a cable electrical
            if member_uid in cable_electrical_uuids:
                has_cable_path = True

            # Find which board this member belongs to
            board = _get_ancestor_board(member, board_uuids)
            if board is not None:
                board_uid = board.instance.node().get_uuid()
                participating_boards[board_uid] = board

        # If 2+ boards participate and no cable path, it's a violation
        if len(participating_boards) >= 2 and not has_cable_path:
            board_names = [b.get_name() for b in participating_boards.values()]
            signal_name = iface.get_full_name(include_uuid=False)
            violations.append(
                CrossBoardViolation(
                    signal_path=signal_name,
                    boards=board_names,
                    message=(
                        f"Cross-board connection without cable: "
                        f"signal '{signal_name}' spans boards "
                        f"{', '.join(board_names)}"
                    ),
                )
            )

    return violations
