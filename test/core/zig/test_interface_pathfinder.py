# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.graph.graph import GraphView, Node


def test_is_connected_to_returns_path_length_sequence():
    """Ensure the Python binding exposes Zig path results as Python lists."""
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n2, bn2=n3)

    lengths = EdgeInterfaceConnection.is_connected_to(source=n1, target=n3)
    assert lengths == [2]


def test_get_other_connected_node():
    """Confirm the wrapper returns bound nodes or None for non-adjacent queries."""
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    edge_ref = EdgeInterfaceConnection.connect(bn1=n1, bn2=n2).edge()

    other_from_1 = EdgeInterfaceConnection.get_other_connected_node(
        edge=edge_ref, node=n1.node()
    )
    assert other_from_1 is not None
    assert other_from_1.is_same(other=n2.node())

    other_from_2 = EdgeInterfaceConnection.get_other_connected_node(
        edge=edge_ref, node=n2.node()
    )
    assert other_from_2 is not None
    assert other_from_2.is_same(other=n1.node())

    assert (
        EdgeInterfaceConnection.get_other_connected_node(edge=edge_ref, node=n3.node())
        is None
    )


def test_edge_type_consistency():
    """Edge type IDs should round-trip through the Python wrapper."""
    g = GraphView.create()

    nodes = [g.insert_node(node=Node.create()) for _ in range(4)]
    tid = EdgeInterfaceConnection.get_tid()
    assert isinstance(tid, int)
    assert tid > 0

    normal = EdgeInterfaceConnection.connect(bn1=nodes[0], bn2=nodes[1]).edge()
    shallow = EdgeInterfaceConnection.connect_shallow(bn1=nodes[2], bn2=nodes[3]).edge()

    assert normal.edge_type() == tid
    assert shallow.edge_type() == tid
    assert EdgeInterfaceConnection.is_instance(edge=normal)
    assert EdgeInterfaceConnection.is_instance(edge=shallow)


def test_visit_connected_edges_callback_receives_python_objects():
    """visit_connected_edges should surface bound edge references to Python callbacks."""
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n1, bn2=n3)

    collected = []

    def collect(ctx, bound_edge):
        ctx.append(bound_edge)

    EdgeInterfaceConnection.visit_connected_edges(
        bound_node=n1, ctx=collected, f=collect
    )

    assert len(collected) == 2
    for entry in collected:
        assert EdgeInterfaceConnection.is_instance(edge=entry.edge())


def test_multiple_connections_same_pair():
    """Repeated connect calls should each yield a bound edge reference."""
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())

    first = EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    second = EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)

    assert EdgeInterfaceConnection.is_instance(edge=first.edge())
    assert EdgeInterfaceConnection.is_instance(edge=second.edge())
    assert EdgeInterfaceConnection.is_connected_to(source=n1, target=n2)
