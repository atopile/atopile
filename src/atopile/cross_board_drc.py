"""
Cross-board DRC (Design Rule Check) for multi-board systems.

Validates that:
- Cross-board electrical connections pass through harness connectors
- Mated connectors have compatible genders (plug ↔ receptacle)
- Harness endpoints are connected to boards (no floating endpoints)
"""

from __future__ import annotations

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile import errors
from atopile.errors import accumulate

logger = logging.getLogger(__name__)


class CrossBoardDRCFault(errors.UserException):
    """Base class for cross-board DRC faults."""


class MissingHarnessFault(CrossBoardDRCFault):
    """Cross-board connection without harness path."""


class GenderMismatchFault(CrossBoardDRCFault):
    """Same-gender connectors mated (plug↔plug or receptacle↔receptacle)."""


class FloatingEndpointFault(CrossBoardDRCFault):
    """Harness endpoint not connected to any board."""


def _get_board_owner(
    node: fabll.Node,
    board_children: dict[fabll.Node, fabll.Node],
) -> fabll.Node | None:
    """
    Given a node, find which board it belongs to by checking if it is
    a descendant of any board module.
    """
    for child, board in board_children.items():
        if node.is_same(child) or node.is_descendant_of(child):
            return board
    return None


def _build_board_children_map(
    boards: list[fabll.Node],
) -> dict[fabll.Node, fabll.Node]:
    """
    Build a map of {child_node: board} for all direct children of all boards.
    """
    result: dict[fabll.Node, fabll.Node] = {}
    for board in boards:
        for child in board.get_children(direct_only=False, types=F.Electrical):
            result[child] = board
    return result


def _build_harness_children_map(
    harnesses: list[fabll.Node],
) -> dict[fabll.Node, fabll.Node]:
    """
    Build a map of {child_node: harness} for all descendants of all harnesses.
    """
    result: dict[fabll.Node, fabll.Node] = {}
    for harness in harnesses:
        for child in harness.get_children(direct_only=False, types=F.Electrical):
            result[child] = harness
    return result


class needs_cross_board_drc(fabll.Node):
    """
    Cross-board DRC trait.

    Attached to multi-board system nodes to validate inter-board connections.
    Follows the needs_erc_check pattern from erc.py.
    """

    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    @F.implements_design_check.register_post_instantiation_design_check
    def __check_post_instantiation_design_check__(self):
        logger.info("Running cross-board DRC")
        with accumulate(CrossBoardDRCFault) as accumulator:
            self._check_cross_board_connections(accumulator)
            self._check_connector_genders(accumulator)
            self._check_floating_endpoints(accumulator)

    def _find_boards(self) -> list[fabll.Node]:
        """Find all modules with is_board trait."""
        implementors = fabll.Traits.get_implementors(
            F.is_board.bind_typegraph(self.tg), g=self.g
        )
        return [fabll.Traits(impl).get_obj_raw() for impl in implementors]

    def _find_harnesses(self) -> list[fabll.Node]:
        """Find all modules with is_harness trait."""
        implementors = fabll.Traits.get_implementors(
            F.is_harness.bind_typegraph(self.tg), g=self.g
        )
        return [fabll.Traits(impl).get_obj_raw() for impl in implementors]

    def _find_connectors_with_gender(
        self,
    ) -> list[tuple[fabll.Node, str]]:
        """Find all connectors with gender traits. Returns (owner, gender) pairs."""
        result: list[tuple[fabll.Node, str]] = []

        plug_impls = fabll.Traits.get_implementors(
            F.is_connector_plug.bind_typegraph(self.tg), g=self.g
        )
        for impl in plug_impls:
            result.append((fabll.Traits(impl).get_obj_raw(), "plug"))

        receptacle_impls = fabll.Traits.get_implementors(
            F.is_connector_receptacle.bind_typegraph(self.tg), g=self.g
        )
        for impl in receptacle_impls:
            result.append((fabll.Traits(impl).get_obj_raw(), "receptacle"))

        return result

    def _check_cross_board_connections(self, accumulator: accumulate) -> None:
        """
        Check that all cross-board electrical connections pass through a harness.

        Algorithm:
        1. Find all boards and harnesses
        2. Collect all Electrical interfaces owned by boards
        3. Group them into buses
        4. For each bus spanning 2+ boards, verify a harness node is in the bus
        """
        boards = self._find_boards()
        harnesses = self._find_harnesses()

        if len(boards) < 2:
            return

        logger.info(
            f"Cross-board DRC: {len(boards)} boards, {len(harnesses)} harnesses"
        )

        board_children = _build_board_children_map(boards)
        harness_children = _build_harness_children_map(harnesses)

        # Collect all Electrical interfaces from boards
        all_electricals: set[fabll.Node] = set()
        for board in boards:
            electricals = board.get_children(direct_only=False, types=F.Electrical)
            all_electricals.update(electricals)

        # Also include Electrical interfaces from harnesses
        for harness in harnesses:
            electricals = harness.get_children(direct_only=False, types=F.Electrical)
            all_electricals.update(electricals)

        if not all_electricals:
            return

        # Group into connected buses
        buses = fabll.is_interface.group_into_buses(all_electricals)

        logger.info(
            f"Grouped {len(all_electricals)} electricals into {len(buses)} buses"
        )

        for bus_members in buses.values():
            # Find which boards are represented in this bus
            boards_in_bus: set[fabll.Node] = set()
            has_harness_path = False

            for member in bus_members:
                board = _get_board_owner(member, board_children)
                if board is not None:
                    boards_in_bus.add(board)

                if member in harness_children:
                    has_harness_path = True

            # If bus spans 2+ boards, verify harness path exists
            if len(boards_in_bus) >= 2 and not has_harness_path:
                board_names = ", ".join(
                    b.get_full_name(include_uuid=False) for b in boards_in_bus
                )
                with accumulator.collect():
                    raise MissingHarnessFault(
                        f"Cross-board connection between [{board_names}] "
                        f"does not pass through a harness"
                    )

    def _check_connector_genders(self, accumulator: accumulate) -> None:
        """
        Check that mated connectors have compatible genders.

        Two connectors are "mated" if their wire_side interfaces are on the same bus.
        plug ↔ receptacle is valid; same-gender mating is invalid.
        """
        connectors = self._find_connectors_with_gender()
        if len(connectors) < 2:
            return

        # Collect wire_side Electricals from each gendered connector
        connector_wire_electricals: list[
            tuple[fabll.Node, str, set[fabll.Node]]
        ] = []

        for connector, gender in connectors:
            wire_electricals: set[fabll.Node] = set()
            # Look for wire_side children
            for child in connector.get_children(direct_only=True, types=F.Electrical):
                child_name = child.get_full_name(include_uuid=False)
                if "wire_side" in child_name:
                    wire_electricals.add(child)
            if wire_electricals:
                connector_wire_electricals.append(
                    (connector, gender, wire_electricals)
                )

        if len(connector_wire_electricals) < 2:
            return

        # Group wire electricals into buses to find mated pairs
        all_wire_electricals: set[fabll.Node] = set()
        for _, _, electricals in connector_wire_electricals:
            all_wire_electricals.update(electricals)

        buses = fabll.is_interface.group_into_buses(all_wire_electricals)

        # For each bus, check that mated connectors have compatible genders
        for bus_members in buses.values():
            genders_in_bus: list[tuple[fabll.Node, str]] = []
            for connector, gender, electricals in connector_wire_electricals:
                if electricals & bus_members:
                    genders_in_bus.append((connector, gender))

            if len(genders_in_bus) >= 2:
                genders = {g for _, g in genders_in_bus}
                if len(genders) == 1:
                    # Same gender mated
                    gender = genders.pop()
                    names = ", ".join(
                        c.get_full_name(include_uuid=False)
                        for c, _ in genders_in_bus
                    )
                    with accumulator.collect():
                        raise GenderMismatchFault(
                            f"Same-gender ({gender}) connectors mated: [{names}]"
                        )

    def _check_floating_endpoints(self, accumulator: accumulate) -> None:
        """
        Check that harness connector endpoints are connected to boards.
        """
        harnesses = self._find_harnesses()
        boards = self._find_boards()

        if not harnesses or not boards:
            return

        board_children = _build_board_children_map(boards)

        for harness in harnesses:
            # Get all Electrical interfaces in the harness
            harness_electricals = set(
                harness.get_children(direct_only=False, types=F.Electrical)
            )

            if not harness_electricals:
                continue

            # Group into buses including board electricals
            all_board_electricals: set[fabll.Node] = set()
            for board in boards:
                all_board_electricals.update(
                    board.get_children(direct_only=False, types=F.Electrical)
                )

            all_electricals = harness_electricals | all_board_electricals
            buses = fabll.is_interface.group_into_buses(all_electricals)

            # Check each harness electrical is in a bus that touches a board
            for harness_elec in harness_electricals:
                # Find its bus
                for bus_members in buses.values():
                    if harness_elec not in bus_members:
                        continue
                    touches_board = any(
                        m in board_children for m in bus_members
                    )
                    if not touches_board:
                        with accumulator.collect():
                            raise FloatingEndpointFault(
                                f"Harness endpoint "
                                f"{harness_elec.get_full_name(include_uuid=False)}"
                                f" in {harness.get_full_name(include_uuid=False)}"
                                f" is not connected to any board"
                            )
                    break
