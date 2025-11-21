# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.graph.graph import GraphView, Node


def test_is_connected_to_returns_bfs_path():
    """Ensure the Python binding exposes Zig BFSPath objects."""
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n2, bn2=n3)

    path = EdgeInterfaceConnection.is_connected_to(source=n1, target=n3)
    assert path.get_length() == 2
    assert path.get_end_node().node().is_same(other=n3.node())


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
    path = EdgeInterfaceConnection.is_connected_to(source=n1, target=n2)
    assert path.get_length() == 1
    assert path.get_end_node().node().is_same(other=n2.node())


def test_get_connected_returns_path_objects():
    """Test that get_connected returns BFSPath objects with correct properties."""
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())
    n4 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n2, bn2=n3)
    EdgeInterfaceConnection.connect(bn1=n3, bn2=n4)

    # Get paths with include_self=True to include the self-path
    paths = EdgeInterfaceConnection.get_connected(source=n1, include_self=True)

    assert len(paths) == 4

    assert paths[n1].get_length() == 0  # Path to self has length 0
    assert paths[n2].get_length() == 1
    assert paths[n3].get_length() == 2
    assert paths[n4].get_length() == 3

    for bound_node, path in paths.items():
        assert path.get_start_node().node().is_same(other=n1.node())
        assert path.get_end_node().node().is_same(other=bound_node.node())


def test_get_connected_with_branching_topology():
    """Test get_connected with a more complex graph topology."""
    g = GraphView.create()

    # Create a branching topology:
    #     n2
    #    /
    #  n1 -- n3
    #    \
    #     n4
    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())
    n4 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n1, bn2=n3)
    EdgeInterfaceConnection.connect(bn1=n1, bn2=n4)

    # Get all paths from n1 (including self)
    paths = EdgeInterfaceConnection.get_connected(source=n1, include_self=True)

    # Should get paths to all 4 nodes (including n1 itself)
    assert len(paths) == 4
    
    # Find paths by comparing nodes
    found_nodes = {n1: None, n2: None, n3: None, n4: None}
    for bound_node, path in paths.items():
        for target_node in found_nodes.keys():
            if bound_node.node().is_same(other=target_node.node()):
                found_nodes[target_node] = path
                break
    
    # Verify all nodes were found
    for target_node, path in found_nodes.items():
        assert path is not None, f"Path to node not found"
        assert path.get_start_node().node().is_same(other=n1.node())
        assert path.get_end_node().node().is_same(other=target_node.node())
    
    # Path to self has length 0
    assert found_nodes[n1].get_length() == 0
    
    # All other paths from n1 should have length 1
    for node in [n2, n3, n4]:
        assert found_nodes[node].get_length() == 1


def test_get_connected_include_self_parameter():
    """Test that include_self parameter correctly controls whether self-path is included."""
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n2, bn2=n3)

    # Test with include_self=True (default behavior)
    paths_with_self = EdgeInterfaceConnection.get_connected(source=n1, include_self=True)
    assert len(paths_with_self) == 3  # n1, n2, n3
    assert n1 in paths_with_self
    assert paths_with_self[n1].get_length() == 0

    # Test with include_self=False
    paths_without_self = EdgeInterfaceConnection.get_connected(source=n1, include_self=False)
    assert len(paths_without_self) == 2  # n2, n3 (no n1)
    assert n1 not in paths_without_self
    assert n2 in paths_without_self
    assert n3 in paths_without_self
    assert paths_without_self[n2].get_length() == 1
    assert paths_without_self[n3].get_length() == 2


def test_get_connected_path_objects_cleanup():
    """Test that BFSPath objects are properly managed and accessed correctly."""
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n2, bn2=n3)

    # Get paths multiple times - should work correctly each time
    paths1 = EdgeInterfaceConnection.get_connected(source=n1, include_self=True)
    assert len(paths1) == 3  # n1, n2, n3
    
    # Find path to n3 in first result
    path_to_n3_v1 = None
    for bound_node, path in paths1.items():
        if bound_node.node().is_same(other=n3.node()):
            path_to_n3_v1 = path
            break
    
    assert path_to_n3_v1 is not None
    assert path_to_n3_v1.get_length() == 2
    
    # Verify we can access edges
    edges = path_to_n3_v1.get_edges()
    assert len(edges) == 2
    
    # Delete the first paths dictionary
    del paths1
    
    # Get paths again - should create new BFSPath objects
    paths2 = EdgeInterfaceConnection.get_connected(source=n1, include_self=True)
    assert len(paths2) == 3
    
    # Find path to n3 in second result
    path_to_n3_v2 = None
    for bound_node, path in paths2.items():
        if bound_node.node().is_same(other=n3.node()):
            path_to_n3_v2 = path
            break
    
    assert path_to_n3_v2 is not None
    assert path_to_n3_v2.get_length() == 2
    
    # Both path objects should have the same properties
    # (even though they're different Python objects wrapping different Zig BFSPath instances)
    assert path_to_n3_v1.get_length() == path_to_n3_v2.get_length()
    assert path_to_n3_v1.get_start_node().node().is_same(other=path_to_n3_v2.get_start_node().node())
    assert path_to_n3_v1.get_end_node().node().is_same(other=path_to_n3_v2.get_end_node().node())
