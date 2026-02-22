"""Tests for the is_harness marker trait."""

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


def _make_graph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


def test_is_harness_trait_attachment():
    """Test that is_harness can be attached to a module at runtime."""
    g, tg = _make_graph()

    node = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    assert not node.has_trait(F.Harness.is_harness)

    fabll.Traits.create_and_add_instance_to(node, F.Harness.is_harness)
    assert node.has_trait(F.Harness.is_harness)


def test_is_harness_type_level():
    """Test that is_harness can be declared at the type level."""
    g, tg = _make_graph()

    class _HarnessModule(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_harness = fabll.Traits.MakeEdge(F.Harness.is_harness.MakeChild())

    harness = _HarnessModule.bind_typegraph(tg).create_instance(g=g)
    assert harness.has_trait(F.Harness.is_harness)


def test_is_harness_get_children_detection():
    """Test that get_children with required_trait finds is_harness modules."""
    g, tg = _make_graph()

    class _Harness(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_harness = fabll.Traits.MakeEdge(F.Harness.is_harness.MakeChild())

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        harness1 = _Harness.MakeChild()

    app = _App.bind_typegraph(tg).create_instance(g=g)

    harnesses = app.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=F.Harness.is_harness,
    )
    assert len(harnesses) == 1


def test_is_harness_and_is_board_coexist():
    """Test that a system module can have both board and harness children."""
    g, tg = _make_graph()

    class _Board(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_board = fabll.Traits.MakeEdge(F.is_board.MakeChild())

    class _Harness(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_harness = fabll.Traits.MakeEdge(F.Harness.is_harness.MakeChild())

    class _System(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        board = _Board.MakeChild()
        harness = _Harness.MakeChild()

    system = _System.bind_typegraph(tg).create_instance(g=g)

    boards = system.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=F.is_board,
    )
    harnesses = system.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=F.Harness.is_harness,
    )
    assert len(boards) == 1
    assert len(harnesses) == 1
