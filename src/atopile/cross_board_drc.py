# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Cross-board DRC: detects electrical connections that span multiple boards
without passing through a harness/cable module, and validates connector
gender compatibility.

Implemented as a design check trait following the same pattern as
needs_erc_check — attached to the app during prepare_build and
discovered/run by check_design() at POST_INSTANTIATION_DESIGN_CHECK.
"""

from dataclasses import dataclass

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import accumulate
from atopile.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CrossBoardViolation:
    """A cross-board connection that doesn't pass through a harness."""

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


def _get_harness_descendants(app: fabll.Node) -> set[int]:
    """
    Build a set of Electrical UUIDs that are descendants of harness modules.
    """
    harness_electrical_uuids: set[int] = set()

    harnesses = list(
        app.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Harness.is_harness,
        )
    )
    for harness in harnesses:
        for child in harness.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=fabll.is_interface,
        ):
            harness_electrical_uuids.add(child.instance.node().get_uuid())

    return harness_electrical_uuids


def _check_connector_gender(
    app: fabll.Node,
    boards: list[fabll.Node],
) -> list[CrossBoardViolation]:
    """
    For each mating connector pair (one on a board, one on a harness),
    validate that one has is_connector_plug and the other has is_connector_receptacle.

    Only checks pairs where one connector is on a harness and the other
    is on a board — these are the physically mating connectors. Connectors
    on the same harness (internal wiring) or same board are skipped.
    """
    violations: list[CrossBoardViolation] = []

    board_uuids: set[int] = set()
    for board in boards:
        board_uuids.add(board.instance.node().get_uuid())

    harness_uuids: set[int] = set()
    for harness in app.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=F.Harness.is_harness,
    ):
        harness_uuids.add(harness.instance.node().get_uuid())

    def _get_ancestor_in(node: fabll.Node, uuid_set: set[int]) -> fabll.Node | None:
        current = node
        while True:
            parent_result = current.get_parent()
            if parent_result is None:
                return None
            parent_node = parent_result[0]
            uid = parent_node.instance.node().get_uuid()
            if uid in uuid_set:
                return parent_node
            current = parent_node

    # Classify connectors by their parent context (board or harness)
    all_connectors = list(
        app.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Harness.is_connector_plug,
        )
    ) + list(
        app.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Harness.is_connector_receptacle,
        )
    )

    harness_connectors: list[tuple[fabll.Node, fabll.Node]] = []  # (connector, harness)
    board_connectors: list[tuple[fabll.Node, fabll.Node]] = []  # (connector, board)

    for connector in all_connectors:
        harness_parent = _get_ancestor_in(connector, harness_uuids)
        if harness_parent is not None:
            harness_connectors.append((connector, harness_parent))
            continue
        board_parent = _get_ancestor_in(connector, board_uuids)
        if board_parent is not None:
            board_connectors.append((connector, board_parent))

    # Build a set of interface UUIDs for each board connector for fast lookup
    board_connector_pin_map: dict[int, tuple[fabll.Node, fabll.Node]] = {}
    for bc, board in board_connectors:
        for pin in bc.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=fabll.is_interface,
        ):
            board_connector_pin_map[pin.instance.node().get_uuid()] = (bc, board)

    # For each harness connector, find its mating board connector via shared net
    checked_pairs: set[tuple[int, int]] = set()

    for hc, harness in harness_connectors:
        pins = list(
            hc.get_children(
                direct_only=False,
                types=fabll.Node,
                required_trait=fabll.is_interface,
            )
        )
        if not pins:
            continue

        # Check the first pin to find the mating board connector
        pin = pins[0]
        is_iface = pin.get_trait(fabll.is_interface)
        connected = is_iface.get_connected(include_self=False)

        for peer in connected:
            peer_uid = peer.instance.node().get_uuid()
            if peer_uid in board_connector_pin_map:
                bc, board = board_connector_pin_map[peer_uid]

                hc_uid = hc.instance.node().get_uuid()
                bc_uid = bc.instance.node().get_uuid()
                pair_key = (min(hc_uid, bc_uid), max(hc_uid, bc_uid))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                # Validate gender compatibility
                hc_is_plug = hc.has_trait(F.Harness.is_connector_plug)
                hc_is_receptacle = hc.has_trait(F.Harness.is_connector_receptacle)
                bc_is_plug = bc.has_trait(F.Harness.is_connector_plug)
                bc_is_receptacle = bc.has_trait(F.Harness.is_connector_receptacle)

                if not (hc_is_plug or hc_is_receptacle):
                    continue
                if not (bc_is_plug or bc_is_receptacle):
                    continue

                # Genders must be opposite
                if hc_is_plug == bc_is_plug:
                    hc_name = hc.get_full_name(include_uuid=False)
                    bc_name = bc.get_full_name(include_uuid=False)
                    hc_gender = "plug" if hc_is_plug else "receptacle"
                    bc_gender = "plug" if bc_is_plug else "receptacle"
                    violations.append(
                        CrossBoardViolation(
                            signal_path=f"{hc_name} <-> {bc_name}",
                            boards=[],
                            message=(
                                f"Connector gender mismatch: "
                                f"'{hc_name}' ({hc_gender}) connected to "
                                f"'{bc_name}' ({bc_gender}). "
                                f"Connected connectors must have opposite genders."
                            ),
                        )
                    )
                break  # Found the mating board connector for this harness connector

    return violations


def check_cross_board_connections(
    app: fabll.Node,
    boards: list[fabll.Node],
) -> list[CrossBoardViolation]:
    """
    Check for electrical connections spanning multiple boards
    without going through a harness/cable module, and validate
    connector gender compatibility.

    Algorithm:
    1. Build a set of board node UUIDs for fast ancestry lookup
    2. Build a set of harness/cable descendant Electrical UUIDs
    3. For each Electrical with is_interface, find its connected bus
    4. Determine which boards participate in that bus
    5. If 2+ boards and no harness electricals in the bus, record a violation
    6. Check connector gender compatibility
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

    # Build harness/cable electrical UUID set
    harness_electrical_uuids = _get_harness_descendants(app)

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
        has_harness_path = False

        for member in bus_members:
            member_uid = member.instance.node().get_uuid()

            # Check if this member is a harness/cable electrical
            if member_uid in harness_electrical_uuids:
                has_harness_path = True

            # Find which board this member belongs to
            board = _get_ancestor_board(member, board_uuids)
            if board is not None:
                board_uid = board.instance.node().get_uuid()
                participating_boards[board_uid] = board

        # If 2+ boards participate and no harness path, it's a violation
        if len(participating_boards) >= 2 and not has_harness_path:
            board_names = [b.get_name() for b in participating_boards.values()]
            signal_name = iface.get_full_name(include_uuid=False)
            violations.append(
                CrossBoardViolation(
                    signal_path=signal_name,
                    boards=board_names,
                    message=(
                        f"Cross-board connection without harness: "
                        f"signal '{signal_name}' spans boards "
                        f"{', '.join(board_names)}"
                    ),
                )
            )

    # Check connector gender compatibility
    gender_violations = _check_connector_gender(app, boards)
    violations.extend(gender_violations)

    return violations


class CrossBoardDRCFault(F.implements_design_check.UnfulfilledCheckException):
    """Cross-board DRC violation."""


class needs_cross_board_drc(fabll.Node):
    """
    Cross-board DRC check trait.

    Checks for:
    - Electrical connections spanning multiple boards without a harness
    - Connector gender compatibility (plug vs receptacle)
    """

    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    @F.implements_design_check.register_post_instantiation_design_check
    def __check_post_instantiation_design_check__(self):
        app = fabll.Traits(self).get_obj_raw()

        boards = list(
            app.get_children(
                direct_only=False,
                types=fabll.Node,
                required_trait=F.is_board,
            )
        )

        violations = check_cross_board_connections(app, boards)

        with accumulate(CrossBoardDRCFault) as acc:
            for v in violations:
                with acc.collect():
                    raise CrossBoardDRCFault(v.message, nodes=[app])

        if not violations:
            logger.info(
                "Cross-board DRC passed: all inter-board connections use harnesses"
            )
