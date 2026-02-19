"""Tests for the is_cable marker trait."""

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


def _make_graph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


def test_is_cable_trait_attachment():
    """Test that is_cable can be attached to a module at runtime."""
    g, tg = _make_graph()

    node = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    assert not node.has_trait(F.is_cable)

    fabll.Traits.create_and_add_instance_to(node, F.is_cable)
    assert node.has_trait(F.is_cable)


def test_is_cable_type_level():
    """Test that is_cable can be declared at the type level."""
    g, tg = _make_graph()

    class _CableModule(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_cable = fabll.Traits.MakeEdge(F.is_cable.MakeChild())

    cable = _CableModule.bind_typegraph(tg).create_instance(g=g)
    assert cable.has_trait(F.is_cable)


def test_is_cable_get_children_detection():
    """Test that get_children with required_trait finds is_cable modules."""
    g, tg = _make_graph()

    class _Cable(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_cable = fabll.Traits.MakeEdge(F.is_cable.MakeChild())

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        cable1 = _Cable.MakeChild()

    app = _App.bind_typegraph(tg).create_instance(g=g)

    cables = app.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=F.is_cable,
    )
    assert len(cables) == 1


def test_is_cable_and_is_board_coexist():
    """Test that a system module can have both board and cable children."""
    g, tg = _make_graph()

    class _Board(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_board = fabll.Traits.MakeEdge(F.is_board.MakeChild())

    class _Cable(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_cable = fabll.Traits.MakeEdge(F.is_cable.MakeChild())

    class _System(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        board = _Board.MakeChild()
        cable = _Cable.MakeChild()

    system = _System.bind_typegraph(tg).create_instance(g=g)

    boards = system.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=F.is_board,
    )
    cables = system.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=F.is_cable,
    )
    assert len(boards) == 1
    assert len(cables) == 1
