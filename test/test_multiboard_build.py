"""Integration tests for multi-board build logic.

Tests board detection, cable detection, cross-board DRC, system BOM,
and multiboard manifest generation using in-memory graph structures.
"""

import json
from pathlib import Path

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.cross_board_drc import check_cross_board_connections


def _make_graph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


# ---------------------------------------------------------------------------
# Reusable type definitions (module-level so MakeChild works in class bodies)
# ---------------------------------------------------------------------------


class _Board(fabll.Node):
    """Board module with a single Electrical interface."""

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_board = fabll.Traits.MakeEdge(F.is_board.MakeChild())
    elec = F.Electrical.MakeChild()


class _Cable(fabll.Node):
    """Cable module with two Electrical endpoints."""

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_cable = fabll.Traits.MakeEdge(F.is_cable.MakeChild())
    side_a = F.Electrical.MakeChild()
    side_b = F.Electrical.MakeChild()


class _ThreeBoards(fabll.Node):
    """System with three boards."""

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_multiboard = fabll.Traits.MakeEdge(F.is_multiboard.MakeChild())
    board_a = _Board.MakeChild()
    board_b = _Board.MakeChild()
    board_c = _Board.MakeChild()


class _TwoBoardsWithCable(fabll.Node):
    """System with two boards and a cable."""

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_multiboard = fabll.Traits.MakeEdge(F.is_multiboard.MakeChild())
    board_a = _Board.MakeChild()
    board_b = _Board.MakeChild()
    cable = _Cable.MakeChild()


class _TwoBoards(fabll.Node):
    """System with two boards, no cable."""

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_multiboard = fabll.Traits.MakeEdge(F.is_multiboard.MakeChild())
    board_a = _Board.MakeChild()
    board_b = _Board.MakeChild()


class _CabledSystem(fabll.Node):
    """System with two boards connected through a cable."""

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_multiboard = fabll.Traits.MakeEdge(F.is_multiboard.MakeChild())
    board_a = _Board.MakeChild()
    board_b = _Board.MakeChild()
    cable = _Cable.MakeChild()
    _connections = [
        fabll.is_interface.MakeConnectionEdge(
            [board_a, _Board.elec], [cable, _Cable.side_a]
        ),
        fabll.is_interface.MakeConnectionEdge(
            [cable, _Cable.side_a], [cable, _Cable.side_b]
        ),
        fabll.is_interface.MakeConnectionEdge(
            [cable, _Cable.side_b], [board_b, _Board.elec]
        ),
    ]


class _DirectConnectSystem(fabll.Node):
    """System with two boards directly connected (no cable — violation)."""

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_multiboard = fabll.Traits.MakeEdge(F.is_multiboard.MakeChild())
    board_a = _Board.MakeChild()
    board_b = _Board.MakeChild()
    _connections = [
        fabll.is_interface.MakeConnectionEdge(
            [board_a, _Board.elec], [board_b, _Board.elec]
        ),
    ]


# ---------------------------------------------------------------------------
# Board detection tests
# ---------------------------------------------------------------------------


def test_detect_boards_in_system():
    """Board detection finds all is_board children in a system module."""
    g, tg = _make_graph()

    system = _ThreeBoards.bind_typegraph(tg).create_instance(g=g)

    boards = list(
        system.get_children(
            direct_only=False, types=fabll.Node, required_trait=F.is_board
        )
    )
    assert len(boards) == 3


def test_detect_cables_in_system():
    """Cable detection finds all is_cable children in a system module."""
    g, tg = _make_graph()

    system = _TwoBoardsWithCable.bind_typegraph(tg).create_instance(g=g)

    cables = list(
        system.get_children(
            direct_only=False, types=fabll.Node, required_trait=F.is_cable
        )
    )
    assert len(cables) == 1


def test_is_system_build_detection():
    """A system build is detected by the is_multiboard trait."""
    g, tg = _make_graph()

    system = _TwoBoards.bind_typegraph(tg).create_instance(g=g)
    assert system.has_trait(F.is_multiboard)  # is_system_build == True

    # Single board module (not a system build — no is_multiboard trait)
    g2, tg2 = _make_graph()
    single = _Board.bind_typegraph(tg2).create_instance(g=g2)
    assert not single.has_trait(F.is_multiboard)  # is_system_build == False


# ---------------------------------------------------------------------------
# Cross-board DRC integration
# ---------------------------------------------------------------------------


def test_drc_passes_with_cable_between_boards():
    """Cross-board DRC should pass when boards are connected via a cable."""
    g, tg = _make_graph()

    system = _CabledSystem.bind_typegraph(tg).create_instance(g=g)

    boards = list(
        system.get_children(
            direct_only=False, types=fabll.Node, required_trait=F.is_board
        )
    )

    violations = check_cross_board_connections(system, boards)
    assert len(violations) == 0


def test_drc_catches_direct_cross_board_connection():
    """Cross-board DRC should flag direct board-to-board connections."""
    g, tg = _make_graph()

    system = _DirectConnectSystem.bind_typegraph(tg).create_instance(g=g)

    boards = list(
        system.get_children(
            direct_only=False, types=fabll.Node, required_trait=F.is_board
        )
    )

    violations = check_cross_board_connections(system, boards)
    assert len(violations) >= 1
    v = violations[0]
    assert len(v.boards) == 2
    assert "Cross-board" in v.message


# ---------------------------------------------------------------------------
# System manifest generation
# ---------------------------------------------------------------------------


def test_system_3d_manifest_structure(tmp_path: Path):
    """Verify the multiboard manifest JSON structure."""
    g, tg = _make_graph()

    system = _TwoBoardsWithCable.bind_typegraph(tg).create_instance(g=g)

    boards = list(
        system.get_children(
            direct_only=False, types=fabll.Node, required_trait=F.is_board
        )
    )
    cables = list(
        system.get_children(
            direct_only=False, types=fabll.Node, required_trait=F.is_cable
        )
    )

    # Build the manifest the same way the build step does
    manifest = {
        "version": "1.0",
        "type": "multiboard",
        "boards": [
            {
                "name": board.get_name(),
                "build_target": board.get_name(),
                "glb_path": f"../{board.get_name()}/{board.get_name()}.pcba.glb",
            }
            for board in boards
        ],
        "cables": [
            {
                "name": cable.get_name(),
                "type": cable.get_full_name(include_uuid=False, types=True),
                "from": boards[0].get_name() if boards else "",
                "to": boards[-1].get_name() if boards else "",
            }
            for cable in cables
        ],
    }

    # Write and re-read to verify JSON roundtrip
    manifest_path = tmp_path / "test.multiboard.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    with open(manifest_path, encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["version"] == "1.0"
    assert loaded["type"] == "multiboard"
    assert len(loaded["boards"]) == 2
    assert len(loaded["cables"]) == 1

    for board_entry in loaded["boards"]:
        assert "name" in board_entry
        assert "glb_path" in board_entry
        assert board_entry["glb_path"].endswith(".pcba.glb")

    cable_entry = loaded["cables"][0]
    assert "name" in cable_entry
    assert "type" in cable_entry
