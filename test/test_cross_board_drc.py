"""Tests for the cross-board DRC module."""

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.cross_board_drc import (
    check_cross_board_connections,
    needs_cross_board_drc,
)
from atopile.errors import UserDesignCheckException
from faebryk.libs.app.checks import check_design


def _make_graph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


# Board with a single Electrical interface
class _Board(fabll.Node):
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_board = fabll.Traits.MakeEdge(F.is_board.MakeChild())
    elec = F.Electrical.MakeChild()


# Harness with two Electrical endpoints
class _Harness(fabll.Node):
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _is_harness = fabll.Traits.MakeEdge(F.Harness.is_harness.MakeChild())
    side_a = F.Electrical.MakeChild()
    side_b = F.Electrical.MakeChild()


# App with one board
class _AppOneBoard(fabll.Node):
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    board1 = _Board.MakeChild()


# App with two boards and a harness connecting them
class _AppWithHarness(fabll.Node):
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    board1 = _Board.MakeChild()
    board2 = _Board.MakeChild()
    harness = _Harness.MakeChild()
    _connections = [
        fabll.is_interface.MakeConnectionEdge(
            [board1, _Board.elec], [harness, _Harness.side_a]
        ),
        fabll.is_interface.MakeConnectionEdge(
            [harness, _Harness.side_a], [harness, _Harness.side_b]
        ),
        fabll.is_interface.MakeConnectionEdge(
            [harness, _Harness.side_b], [board2, _Board.elec]
        ),
    ]


# App with two boards directly connected (no harness — violation)
class _AppDirectConnect(fabll.Node):
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    board1 = _Board.MakeChild()
    board2 = _Board.MakeChild()
    _connections = [
        fabll.is_interface.MakeConnectionEdge(
            [board1, _Board.elec], [board2, _Board.elec]
        ),
    ]


# App with two isolated boards (no connections)
class _AppIsolated(fabll.Node):
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    board1 = _Board.MakeChild()
    board2 = _Board.MakeChild()


def test_no_violations_single_board():
    """No violations when there's only one board."""
    g, tg = _make_graph()

    app = _AppOneBoard.bind_typegraph(tg).create_instance(g=g)

    boards = list(
        app.get_children(direct_only=False, types=fabll.Node, required_trait=F.is_board)
    )
    assert len(boards) == 1

    violations = check_cross_board_connections(app, boards)
    assert len(violations) == 0


def test_no_violations_with_harness():
    """No violations when cross-board connection goes through a harness."""
    g, tg = _make_graph()

    app = _AppWithHarness.bind_typegraph(tg).create_instance(g=g)

    boards = list(
        app.get_children(direct_only=False, types=fabll.Node, required_trait=F.is_board)
    )
    assert len(boards) == 2

    violations = check_cross_board_connections(app, boards)
    assert len(violations) == 0


def test_violation_direct_cross_board():
    """Violation when two boards are directly connected without a harness."""
    g, tg = _make_graph()

    app = _AppDirectConnect.bind_typegraph(tg).create_instance(g=g)

    boards = list(
        app.get_children(direct_only=False, types=fabll.Node, required_trait=F.is_board)
    )
    assert len(boards) == 2

    violations = check_cross_board_connections(app, boards)
    assert len(violations) == 1
    assert len(violations[0].boards) == 2


def test_no_violations_isolated_boards():
    """No violations when boards have no cross-board connections."""
    g, tg = _make_graph()

    app = _AppIsolated.bind_typegraph(tg).create_instance(g=g)

    boards = list(
        app.get_children(direct_only=False, types=fabll.Node, required_trait=F.is_board)
    )
    assert len(boards) == 2

    violations = check_cross_board_connections(app, boards)
    assert len(violations) == 0


def test_empty_boards_list():
    """No violations when boards list is empty."""
    g, tg = _make_graph()

    app = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    violations = check_cross_board_connections(app, [])
    assert len(violations) == 0


def test_trait_no_violation():
    """Design check passes when harness is used."""
    g, tg = _make_graph()

    app = _AppWithHarness.bind_typegraph(tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(app, needs_cross_board_drc)

    # Should not raise
    check_design(
        app, F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK
    )


def test_trait_violation():
    """Design check raises when boards are directly connected."""
    g, tg = _make_graph()

    app = _AppDirectConnect.bind_typegraph(tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(app, needs_cross_board_drc)

    with pytest.raises(UserDesignCheckException):
        check_design(
            app, F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK
        )
