"""Tests for the is_multiboard marker trait."""

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


def _make_graph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


def test_is_multiboard_trait_attachment():
    """Test that is_multiboard can be attached to a module at runtime."""
    g, tg = _make_graph()

    node = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    assert not node.has_trait(F.is_multiboard)

    fabll.Traits.create_and_add_instance_to(node, F.is_multiboard)
    assert node.has_trait(F.is_multiboard)


def test_is_multiboard_type_level():
    """Test that is_multiboard can be declared at the type level."""
    g, tg = _make_graph()

    class _SystemModule(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _is_multiboard = fabll.Traits.MakeEdge(F.is_multiboard.MakeChild())

    system = _SystemModule.bind_typegraph(tg).create_instance(g=g)
    assert system.has_trait(F.is_multiboard)


def test_is_multiboard_not_present_by_default():
    """Test that a plain Node does not have is_multiboard."""
    g, tg = _make_graph()

    node = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    assert not node.has_trait(F.is_multiboard)
