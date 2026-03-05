"""Tests for the is_board marker trait."""

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


def _make_graph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


def test_is_board_trait_attachment():
    """Test that is_board can be attached to a module at runtime."""
    g, tg = _make_graph()

    node = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    assert not node.has_trait(F.is_board)

    fabll.Traits.create_and_add_instance_to(node, F.is_board)
    assert node.has_trait(F.is_board)


def test_is_board_type_level():
    """Test that is_board can be declared at the type level."""
    g, tg = _make_graph()

    class _BoardModule(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_board = fabll.Traits.MakeEdge(F.is_board.MakeChild())

    board = _BoardModule.bind_typegraph(tg).create_instance(g=g)
    assert board.has_trait(F.is_board)


def test_is_board_get_children_detection():
    """Test that get_children with required_trait finds is_board modules."""
    g, tg = _make_graph()

    class _Board(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_board = fabll.Traits.MakeEdge(F.is_board.MakeChild())

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        board1 = _Board.MakeChild()
        board2 = _Board.MakeChild()

    app = _App.bind_typegraph(tg).create_instance(g=g)

    boards = app.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=F.is_board,
    )
    assert len(boards) == 2


def test_is_board_not_present_by_default():
    """Test that a plain Node does not have is_board."""
    g, tg = _make_graph()

    node = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    assert not node.has_trait(F.is_board)
