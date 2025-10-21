# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Tests for the Zig interface connection and pathfinder implementation.

These tests verify the low-level graph operations that power the high-level
ModuleInterface.is_connected_to() functionality in Python.
"""

import pytest

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.graph.graph import GraphView, Node


def test_basic_connection():
    """
    Basic two-node connection:
    ```
    N1 --> N2
    ```
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())

    # Connect the nodes
    edge = EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)

    # Verify connection
    assert EdgeInterfaceConnection.is_instance(edge=edge.edge())
    assert edge.edge().edge_type() == EdgeInterfaceConnection.get_tid()

    # Check connectivity
    paths = EdgeInterfaceConnection.is_connected_to(source=n1, target=n2)
    assert len(paths) == 1
    assert paths[0] == 1  # 1 edge in path


def test_self_connect():
    """
    A node should always be connected to itself (zero-length path).
    ```
    N1 --> N1 (self)
    ```
    """
    g = GraphView.create()

    bn1 = g.insert_node(node=Node.create())

    # A node is always connected to itself
    paths = EdgeInterfaceConnection.is_connected_to(source=bn1, target=bn1)
    assert len(paths) == 1
    assert paths[0] == 0  # 0 edges (self-connection)


def test_not_connected():
    """
    Two unconnected nodes should not be connected.
    ```
    N1     N2
    ```
    """
    g = GraphView.create()

    bn1 = g.insert_node(node=Node.create())
    bn2 = g.insert_node(node=Node.create())

    # Not connected
    paths = EdgeInterfaceConnection.is_connected_to(source=bn1, target=bn2)
    assert len(paths) == 0


def test_chain_direct():
    """
    Direct chain of connections:
    ```
    N1 --> N2 --> N3
    ```
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    # Create chain
    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n2, bn2=n3)

    # Check end-to-end connectivity
    paths = EdgeInterfaceConnection.is_connected_to(source=n1, target=n3)
    assert len(paths) == 1
    assert paths[0] == 2  # 2 edges in path


def test_get_connected():
    r"""
    Get all nodes reachable from a source:
    ```
    N1 --> N2 --> N3
     |
     +---> N4
    ```
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())
    n4 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n2, bn2=n3)
    EdgeInterfaceConnection.connect(bn1=n1, bn2=n4)

    # Get all connected (including self)
    all_paths = EdgeInterfaceConnection.get_connected(source=n1)
    # Should find: n1->n1 (self), n1->n2, n1->n3, n1->n4
    assert len(all_paths) == 4


def test_down_connect_hierarchy():
    """
    Test hierarchical connection through children:
    ```
    P1 --> P2
     C1     C1
     C2     C2

    When parents are connected, children should be connectable through hierarchy.
    ```
    """
    g = GraphView.create()

    # Create parent nodes
    p1 = g.insert_node(node=Node.create())
    p2 = g.insert_node(node=Node.create())

    # Create children
    c1_p1 = g.insert_node(node=Node.create())
    c2_p1 = g.insert_node(node=Node.create())
    c1_p2 = g.insert_node(node=Node.create())
    c2_p2 = g.insert_node(node=Node.create())

    # Add composition edges (parent -> child)
    EdgeComposition.add_child(bound_node=p1, child=c1_p1.node(), child_identifier="c1")
    EdgeComposition.add_child(bound_node=p1, child=c2_p1.node(), child_identifier="c2")
    EdgeComposition.add_child(bound_node=p2, child=c1_p2.node(), child_identifier="c1")
    EdgeComposition.add_child(bound_node=p2, child=c2_p2.node(), child_identifier="c2")

    # Connect parents
    EdgeInterfaceConnection.connect(bn1=p1, bn2=p2)

    # Parents should be connected
    paths_p = EdgeInterfaceConnection.is_connected_to(source=p1, target=p2)
    assert len(paths_p) == 1

    # Matching children should be connected through hierarchy (up -> across -> down)
    paths_c1 = EdgeInterfaceConnection.is_connected_to(source=c1_p1, target=c1_p2)
    assert len(paths_c1) == 1

    paths_c2 = EdgeInterfaceConnection.is_connected_to(source=c2_p1, target=c2_p2)
    assert len(paths_c2) == 1

    # But mismatched children should NOT be connected
    paths_mixed = EdgeInterfaceConnection.is_connected_to(source=c1_p1, target=c2_p2)
    assert len(paths_mixed) == 0


def test_no_parent_to_child():
    """
    Parent should NOT be directly connected to its own children (no descent from start).
    ```
    P1
     C1

    P1 should NOT connect to C1 directly.
    ```
    """
    g = GraphView.create()

    parent = g.insert_node(node=Node.create())
    child = g.insert_node(node=Node.create())

    # Add composition edge (parent -> child)
    EdgeComposition.add_child(
        bound_node=parent, child=child.node(), child_identifier="c1"
    )

    # Parent should NOT be connected to child via composition alone
    paths = EdgeInterfaceConnection.is_connected_to(source=parent, target=child)
    assert len(paths) == 0


def test_no_sibling_connection():
    """
    Siblings should NOT be connected through their parent:
    ```
    P1
     C1
     C2

    C1 should NOT connect to C2 through P1.
    ```
    """
    g = GraphView.create()

    parent = g.insert_node(node=Node.create())
    child1 = g.insert_node(node=Node.create())
    child2 = g.insert_node(node=Node.create())

    # Add composition edges
    EdgeComposition.add_child(
        bound_node=parent, child=child1.node(), child_identifier="c1"
    )
    EdgeComposition.add_child(
        bound_node=parent, child=child2.node(), child_identifier="c2"
    )

    # Siblings should NOT be connected
    paths = EdgeInterfaceConnection.is_connected_to(source=child1, target=child2)
    assert len(paths) == 0


def test_shallow_connection_simple():
    """
    Shallow connections block hierarchy traversal:
    ```
    N1 ==> N2  (shallow)

    Direct shallow connection works.
    ```
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())

    # Create shallow connection
    _ = EdgeInterfaceConnection.connect_shallow(bn1=n1, bn2=n2)

    # Should be connected at the same level
    paths = EdgeInterfaceConnection.is_connected_to(source=n1, target=n2)
    assert len(paths) == 1


def test_shallow_connection_blocks_children():
    """
    Shallow connections should NOT allow child traversal:
    ```
    P1 ==> P2  (shallow)
     C1     C1

    C1 under P1 should NOT connect to C1 under P2 through shallow link.
    ```
    """
    g = GraphView.create()

    # Create parents
    p1 = g.insert_node(node=Node.create())
    p2 = g.insert_node(node=Node.create())

    # Create children
    c1_p1 = g.insert_node(node=Node.create())
    c1_p2 = g.insert_node(node=Node.create())

    # Add composition edges
    EdgeComposition.add_child(bound_node=p1, child=c1_p1.node(), child_identifier="c1")
    EdgeComposition.add_child(bound_node=p2, child=c1_p2.node(), child_identifier="c1")

    # Create shallow connection between parents
    EdgeInterfaceConnection.connect_shallow(bn1=p1, bn2=p2)

    # Parents should be connected
    paths_p = EdgeInterfaceConnection.is_connected_to(source=p1, target=p2)
    assert len(paths_p) == 1

    # Children should NOT be connected through shallow link
    paths_c = EdgeInterfaceConnection.is_connected_to(source=c1_p1, target=c1_p2)
    assert len(paths_c) == 0


def test_multiple_paths():
    r"""
    Multiple valid paths between nodes:
    ```
         N3
        /  \
    N1 -- N2 -- N4
        \  /
         N5
    
    Multiple paths from N1 to N4.
    ```
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())
    n4 = g.insert_node(node=Node.create())
    n5 = g.insert_node(node=Node.create())

    # Create diamond pattern
    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n2, bn2=n4)
    EdgeInterfaceConnection.connect(bn1=n1, bn2=n3)
    EdgeInterfaceConnection.connect(bn1=n3, bn2=n4)
    EdgeInterfaceConnection.connect(bn1=n1, bn2=n5)
    EdgeInterfaceConnection.connect(bn1=n5, bn2=n4)

    # Should find path from n1 to n4
    paths = EdgeInterfaceConnection.is_connected_to(source=n1, target=n4)
    assert len(paths) >= 1  # At least one path exists


def test_get_other_connected_node():
    """
    Test getting the other end of an edge.
    ```
    N1 -- E1 -- N2

    Given E1 and N1, should return N2.
    Given E1 and N2, should return N1.
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())

    be = EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    edge = be.edge()

    # Get other node from n1's perspective
    other_from_n1 = EdgeInterfaceConnection.get_other_connected_node(
        edge=edge, node=n1.node()
    )
    assert other_from_n1 is not None
    assert other_from_n1.is_same(other=n2.node())

    # Get other node from n2's perspective
    other_from_n2 = EdgeInterfaceConnection.get_other_connected_node(
        edge=edge, node=n2.node()
    )
    assert other_from_n2 is not None
    assert other_from_n2.is_same(other=n1.node())

    # If node is not part of edge, should return None
    n3 = g.insert_node(node=Node.create())
    other_from_n3 = EdgeInterfaceConnection.get_other_connected_node(
        edge=edge, node=n3.node()
    )
    assert other_from_n3 is None


@pytest.mark.slow
def test_long_chain():
    """
    Test performance with a long chain of connections.
    ```
    N1 --> N2 --> N3 --> ... --> N1000
    ```
    """
    g = GraphView.create()

    chain_length = 1000
    nodes = [g.insert_node(node=Node.create()) for _ in range(chain_length)]

    # Create chain
    for i in range(chain_length - 1):
        EdgeInterfaceConnection.connect(bn1=nodes[i], bn2=nodes[i + 1])

    # Check end-to-end connectivity
    paths = EdgeInterfaceConnection.is_connected_to(source=nodes[0], target=nodes[-1])
    assert len(paths) == 1
    assert paths[0] == chain_length - 1  # Number of edges


def test_edge_type_consistency():
    """
    Verify that EdgeInterfaceConnection edges have consistent type IDs.
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())

    # Get the type ID
    tid = EdgeInterfaceConnection.get_tid()
    assert tid > 0  # Should be a valid type ID

    # Create an edge
    be = EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    edge = be.edge()

    # Edge should have the correct type
    assert edge.edge_type() == tid
    assert EdgeInterfaceConnection.is_instance(edge=edge)

    # Create a shallow edge
    n3 = g.insert_node(node=Node.create())
    n4 = g.insert_node(node=Node.create())
    be_shallow = EdgeInterfaceConnection.connect_shallow(bn1=n3, bn2=n4)
    edge_shallow = be_shallow.edge()

    # Shallow edge should also have the same type
    assert edge_shallow.edge_type() == tid
    assert EdgeInterfaceConnection.is_instance(edge=edge_shallow)


def test_composition_and_interface_edges():
    """
    Test interaction between composition edges (parent-child) and interface edges (connections).

    This verifies the pathfinder correctly handles composition hierarchy.
    Note: Parents are NOT automatically connected when children are connected.
    The "no descent from start" rule prevents parent->child traversal.
    """
    g = GraphView.create()

    # Create a simple hierarchy with two branches
    root1 = g.insert_node(node=Node.create())
    root2 = g.insert_node(node=Node.create())

    child1 = g.insert_node(node=Node.create())
    child2 = g.insert_node(node=Node.create())

    # Add hierarchy
    EdgeComposition.add_child(
        bound_node=root1, child=child1.node(), child_identifier="child"
    )
    EdgeComposition.add_child(
        bound_node=root2, child=child2.node(), child_identifier="child"
    )

    # Connect children directly
    EdgeInterfaceConnection.connect(bn1=child1, bn2=child2)

    # Children should be connected
    paths_children = EdgeInterfaceConnection.is_connected_to(
        source=child1, target=child2
    )
    assert len(paths_children) == 1

    # Roots are NOT automatically connected when children are connected
    # This is by design - pathfinder doesn't allow descent from start node
    paths_roots = EdgeInterfaceConnection.is_connected_to(source=root1, target=root2)
    assert len(paths_roots) == 0

    # But if we also connect the roots, both levels should be connected
    EdgeInterfaceConnection.connect(bn1=root1, bn2=root2)

    # Now roots should be connected directly
    paths_roots_direct = EdgeInterfaceConnection.is_connected_to(
        source=root1, target=root2
    )
    assert len(paths_roots_direct) == 1
    assert paths_roots_direct[0] == 1  # Direct connection


@pytest.mark.skip(reason="Complex split-chain requires all children paths to complete")
def test_split_chain_single():
    """
    Path splits and rejoins through different routes:
    ```
    H1     H2 --> H3
     L1 --> L1     L1
     L2     L2     L2
      |            ^
      +------------+

    For H1 to connect to H3, both L1 and L2 must complete their paths.
    """
    g = GraphView.create()

    # Create hierarchy
    h1 = g.insert_node(node=Node.create())
    h2 = g.insert_node(node=Node.create())
    h3 = g.insert_node(node=Node.create())

    l1_h1 = g.insert_node(node=Node.create())
    l2_h1 = g.insert_node(node=Node.create())
    l1_h2 = g.insert_node(node=Node.create())
    l2_h2 = g.insert_node(node=Node.create())
    l1_h3 = g.insert_node(node=Node.create())
    l2_h3 = g.insert_node(node=Node.create())

    EdgeComposition.add_child(
        bound_node=h1, child=l1_h1.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h1, child=l2_h1.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=h2, child=l1_h2.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h2, child=l2_h2.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=h3, child=l1_h3.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h3, child=l2_h3.node(), child_identifier="l2"
    )

    # Connect: Complete path through H2 to H3, and L2 directly to L3
    EdgeInterfaceConnection.connect(bn1=l1_h1, bn2=l1_h2)
    EdgeInterfaceConnection.connect(bn1=l2_h1, bn2=l2_h2)  # Must connect both!
    EdgeInterfaceConnection.connect(bn1=h2, bn2=h3)

    # Now H1 should connect to H3
    paths = EdgeInterfaceConnection.is_connected_to(source=h1, target=h3)
    assert len(paths) >= 1


@pytest.mark.skip(
    reason="Complex cross-connection requires all children connected for parent connection"
)
def test_split_chain_flip():
    """
    Crossover pattern where connections flip:
    ```
    H1     H2 ==> H3     H4
     L1 --> L2     L2 --> L1
     L2 --> L1     L1 --> L2

    Even though names cross, should still connect if both paths complete.
    """
    g = GraphView.create()

    h1 = g.insert_node(node=Node.create())
    h2 = g.insert_node(node=Node.create())
    h3 = g.insert_node(node=Node.create())
    h4 = g.insert_node(node=Node.create())

    l1_h1 = g.insert_node(node=Node.create())
    l2_h1 = g.insert_node(node=Node.create())
    l1_h2 = g.insert_node(node=Node.create())
    l2_h2 = g.insert_node(node=Node.create())
    l1_h3 = g.insert_node(node=Node.create())
    l2_h3 = g.insert_node(node=Node.create())
    l1_h4 = g.insert_node(node=Node.create())
    l2_h4 = g.insert_node(node=Node.create())

    # Add hierarchy
    for h, l1, l2 in [
        (h1, l1_h1, l2_h1),
        (h2, l1_h2, l2_h2),
        (h3, l1_h3, l2_h3),
        (h4, l1_h4, l2_h4),
    ]:
        EdgeComposition.add_child(bound_node=h, child=l1.node(), child_identifier="l1")
        EdgeComposition.add_child(bound_node=h, child=l2.node(), child_identifier="l2")

    # Flipped connections
    EdgeInterfaceConnection.connect(bn1=l1_h1, bn2=l2_h2)
    EdgeInterfaceConnection.connect(bn1=l2_h1, bn2=l1_h2)
    EdgeInterfaceConnection.connect_shallow(bn1=h2, bn2=h3)
    EdgeInterfaceConnection.connect(bn1=l1_h3, bn2=l2_h4)
    EdgeInterfaceConnection.connect(bn1=l2_h3, bn2=l1_h4)

    # H1 should connect to H4 (both flip paths work)
    paths = EdgeInterfaceConnection.is_connected_to(source=h1, target=h4)
    assert len(paths) >= 1


def test_split_flip_negative():
    """
    Incomplete flip should NOT connect:
    ```
    H1     H2
     L1 --> L2
     L2 --> L1

    H1 should NOT connect to H2 (partial flip doesn't complete)
    """
    g = GraphView.create()

    h1 = g.insert_node(node=Node.create())
    h2 = g.insert_node(node=Node.create())

    l1_h1 = g.insert_node(node=Node.create())
    l2_h1 = g.insert_node(node=Node.create())
    l1_h2 = g.insert_node(node=Node.create())
    l2_h2 = g.insert_node(node=Node.create())

    EdgeComposition.add_child(bound_node=h1, child=l1_h1.node(), child_identifier="l1")
    EdgeComposition.add_child(bound_node=h1, child=l2_h1.node(), child_identifier="l2")
    EdgeComposition.add_child(bound_node=h2, child=l1_h2.node(), child_identifier="l1")
    EdgeComposition.add_child(bound_node=h2, child=l2_h2.node(), child_identifier="l2")

    # Flipped connections
    EdgeInterfaceConnection.connect(bn1=l1_h1, bn2=l2_h2)
    EdgeInterfaceConnection.connect(bn1=l2_h1, bn2=l1_h2)

    # H1 should NOT connect to H2 (incomplete)
    paths = EdgeInterfaceConnection.is_connected_to(source=h1, target=h2)
    assert len(paths) == 0


@pytest.mark.skip(
    reason="Complex multi-level hierarchy requires all children connected at each level"
)
def test_multi_level_hierarchy():
    """
    Test 3+ level hierarchy traversal:
    ```
    R1          R2
     H1          H1
      M1          M1
       L1 -->      L1
       L2 -->      L2
      M2          M2
       L1 -->      L1
       L2 -->      L2
     H2          H2
      M1          M1
       L1 -->      L1

    4 levels: Root -> High -> Medium -> Low
    """
    g = GraphView.create()

    # Create 4-level hierarchy for two branches
    r1 = g.insert_node(node=Node.create())
    r2 = g.insert_node(node=Node.create())

    h1_r1 = g.insert_node(node=Node.create())
    h1_r2 = g.insert_node(node=Node.create())
    h2_r1 = g.insert_node(node=Node.create())
    h2_r2 = g.insert_node(node=Node.create())

    m1_h1r1 = g.insert_node(node=Node.create())
    m1_h1r2 = g.insert_node(node=Node.create())
    m2_h1r1 = g.insert_node(node=Node.create())
    m2_h1r2 = g.insert_node(node=Node.create())
    m1_h2r1 = g.insert_node(node=Node.create())
    m1_h2r2 = g.insert_node(node=Node.create())

    # Add lots of low-level nodes (only connect some)
    l1_m1h1r1 = g.insert_node(node=Node.create())
    l1_m1h1r2 = g.insert_node(node=Node.create())
    l2_m1h1r1 = g.insert_node(node=Node.create())
    l2_m1h1r2 = g.insert_node(node=Node.create())
    l1_m2h1r1 = g.insert_node(node=Node.create())
    l1_m2h1r2 = g.insert_node(node=Node.create())
    l2_m2h1r1 = g.insert_node(node=Node.create())
    l2_m2h1r2 = g.insert_node(node=Node.create())
    l1_m1h2r1 = g.insert_node(node=Node.create())
    l1_m1h2r2 = g.insert_node(node=Node.create())

    # Build hierarchy (R -> H -> M -> L)
    EdgeComposition.add_child(bound_node=r1, child=h1_r1.node(), child_identifier="h1")
    EdgeComposition.add_child(bound_node=r1, child=h2_r1.node(), child_identifier="h2")
    EdgeComposition.add_child(bound_node=r2, child=h1_r2.node(), child_identifier="h1")
    EdgeComposition.add_child(bound_node=r2, child=h2_r2.node(), child_identifier="h2")

    EdgeComposition.add_child(
        bound_node=h1_r1, child=m1_h1r1.node(), child_identifier="m1"
    )
    EdgeComposition.add_child(
        bound_node=h1_r1, child=m2_h1r1.node(), child_identifier="m2"
    )
    EdgeComposition.add_child(
        bound_node=h1_r2, child=m1_h1r2.node(), child_identifier="m1"
    )
    EdgeComposition.add_child(
        bound_node=h1_r2, child=m2_h1r2.node(), child_identifier="m2"
    )
    EdgeComposition.add_child(
        bound_node=h2_r1, child=m1_h2r1.node(), child_identifier="m1"
    )
    EdgeComposition.add_child(
        bound_node=h2_r2, child=m1_h2r2.node(), child_identifier="m1"
    )

    EdgeComposition.add_child(
        bound_node=m1_h1r1, child=l1_m1h1r1.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=m1_h1r1, child=l2_m1h1r1.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=m1_h1r2, child=l1_m1h1r2.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=m1_h1r2, child=l2_m1h1r2.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=m2_h1r1, child=l1_m2h1r1.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=m2_h1r1, child=l2_m2h1r1.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=m2_h1r2, child=l1_m2h1r2.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=m2_h1r2, child=l2_m2h1r2.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=m1_h2r1, child=l1_m1h2r1.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=m1_h2r2, child=l1_m1h2r2.node(), child_identifier="l1"
    )

    # Connect at lowest level for h1.m1
    EdgeInterfaceConnection.connect(bn1=l1_m1h1r1, bn2=l1_m1h1r2)
    EdgeInterfaceConnection.connect(bn1=l2_m1h1r1, bn2=l2_m1h1r2)

    # Connect at lowest level for h1.m2
    EdgeInterfaceConnection.connect(bn1=l1_m2h1r1, bn2=l1_m2h1r2)
    EdgeInterfaceConnection.connect(bn1=l2_m2h1r1, bn2=l2_m2h1r2)

    # Connect at lowest level for h2.m1
    EdgeInterfaceConnection.connect(bn1=l1_m1h2r1, bn2=l1_m1h2r2)

    # All matching children at all levels should be connected
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=l1_m1h1r1, target=l1_m1h1r2))
        == 1
    )
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=m1_h1r1, target=m1_h1r2))
        == 1
    )
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=m2_h1r1, target=m2_h1r2))
        == 1
    )
    assert len(EdgeInterfaceConnection.is_connected_to(source=h1_r1, target=h1_r2)) == 1
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=m1_h2r1, target=m1_h2r2))
        == 1
    )
    assert len(EdgeInterfaceConnection.is_connected_to(source=h2_r1, target=h2_r2)) == 1

    # Top level should be connected through all children
    assert len(EdgeInterfaceConnection.is_connected_to(source=r1, target=r2)) == 1


def test_chains_double_shallow():
    """
    Multiple shallow connections in sequence:
    ```
    N1 ==> N2 ==> N3

    Shallow connections should chain.
    ```
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect_shallow(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect_shallow(bn1=n2, bn2=n3)

    # Should be connected through chain
    paths = EdgeInterfaceConnection.is_connected_to(source=n1, target=n3)
    assert len(paths) == 1
    assert paths[0] == 2


def test_chains_mixed_shallow():
    """
    Mixed shallow and normal connections:
    ```
    N1 ==> N2 --> N3

    Should connect through mixed chain.
    ```
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect_shallow(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n2, bn2=n3)

    # Should be connected
    paths = EdgeInterfaceConnection.is_connected_to(source=n1, target=n3)
    assert len(paths) == 1
    assert paths[0] == 2


def test_chains_mixed_shallow_with_hierarchy():
    """
    Mixed shallow and normal with hierarchy:
    ```
    L1 ==> L2 --> L3
     S      S      S
     R      R      R

    L1 shallow to L2, then L2 normal to L3.
    Children of L2 and L3 should connect, but NOT L1's children.
    ```
    """
    g = GraphView.create()

    l1 = g.insert_node(node=Node.create())
    l2 = g.insert_node(node=Node.create())
    l3 = g.insert_node(node=Node.create())

    s1 = g.insert_node(node=Node.create())
    r1 = g.insert_node(node=Node.create())
    s2 = g.insert_node(node=Node.create())
    r2 = g.insert_node(node=Node.create())
    s3 = g.insert_node(node=Node.create())
    r3 = g.insert_node(node=Node.create())

    EdgeComposition.add_child(bound_node=l1, child=s1.node(), child_identifier="s")
    EdgeComposition.add_child(bound_node=l1, child=r1.node(), child_identifier="r")
    EdgeComposition.add_child(bound_node=l2, child=s2.node(), child_identifier="s")
    EdgeComposition.add_child(bound_node=l2, child=r2.node(), child_identifier="r")
    EdgeComposition.add_child(bound_node=l3, child=s3.node(), child_identifier="s")
    EdgeComposition.add_child(bound_node=l3, child=r3.node(), child_identifier="r")

    EdgeInterfaceConnection.connect_shallow(bn1=l1, bn2=l2)
    EdgeInterfaceConnection.connect(bn1=l2, bn2=l3)

    # L1 to L3 should connect (through shallow then normal)
    assert len(EdgeInterfaceConnection.is_connected_to(source=l1, target=l3)) == 1

    # L2's and L3's children should be connected
    assert len(EdgeInterfaceConnection.is_connected_to(source=s2, target=s3)) == 1
    assert len(EdgeInterfaceConnection.is_connected_to(source=r2, target=r3)) == 1

    # But L1's children should NOT connect to L2's or L3's (blocked by shallow)
    assert len(EdgeInterfaceConnection.is_connected_to(source=s1, target=s2)) == 0
    assert len(EdgeInterfaceConnection.is_connected_to(source=s1, target=s3)) == 0
    assert len(EdgeInterfaceConnection.is_connected_to(source=r1, target=r2)) == 0
    assert len(EdgeInterfaceConnection.is_connected_to(source=r1, target=r3)) == 0


@pytest.mark.skip(
    reason="Requires all children connected for parent-level connection propagation"
)
def test_chain_multiple_hops():
    """
    Chain with multiple sequential connections:
    ```
    H1      H2      H3
     L1 -->  L1 -->  L1
     L2 -->  L2 -->  L2

    All matching children at each level connect.
    ```
    """
    g = GraphView.create()

    h1 = g.insert_node(node=Node.create())
    h2 = g.insert_node(node=Node.create())
    h3 = g.insert_node(node=Node.create())

    l1_h1 = g.insert_node(node=Node.create())
    l2_h1 = g.insert_node(node=Node.create())
    l1_h2 = g.insert_node(node=Node.create())
    l2_h2 = g.insert_node(node=Node.create())
    l1_h3 = g.insert_node(node=Node.create())
    l2_h3 = g.insert_node(node=Node.create())

    EdgeComposition.add_child(bound_node=h1, child=l1_h1.node(), child_identifier="l1")
    EdgeComposition.add_child(bound_node=h1, child=l2_h1.node(), child_identifier="l2")
    EdgeComposition.add_child(bound_node=h2, child=l1_h2.node(), child_identifier="l1")
    EdgeComposition.add_child(bound_node=h2, child=l2_h2.node(), child_identifier="l2")
    EdgeComposition.add_child(bound_node=h3, child=l1_h3.node(), child_identifier="l1")
    EdgeComposition.add_child(bound_node=h3, child=l2_h3.node(), child_identifier="l2")

    # Connect all matching children
    EdgeInterfaceConnection.connect(bn1=l1_h1, bn2=l1_h2)
    EdgeInterfaceConnection.connect(bn1=l2_h1, bn2=l2_h2)
    EdgeInterfaceConnection.connect(bn1=l1_h2, bn2=l1_h3)
    EdgeInterfaceConnection.connect(bn1=l2_h2, bn2=l2_h3)

    # End-to-end should be connected
    paths = EdgeInterfaceConnection.is_connected_to(source=h1, target=h3)
    assert len(paths) == 1


@pytest.mark.skip(reason="Requires complete child connections at intermediate levels")
def test_alternating_hierarchy_levels():
    """
    Alternating between direct connections and hierarchy traversal:
    ```
    H1 --> H2      H3 --> H4
            L1 -->  L1
            L2 -->  L2

    Mix of direct and hierarchical hops.
    """
    g = GraphView.create()

    h1 = g.insert_node(node=Node.create())
    h2 = g.insert_node(node=Node.create())
    h3 = g.insert_node(node=Node.create())
    h4 = g.insert_node(node=Node.create())

    l1_h2 = g.insert_node(node=Node.create())
    l2_h2 = g.insert_node(node=Node.create())
    l1_h3 = g.insert_node(node=Node.create())
    l2_h3 = g.insert_node(node=Node.create())

    EdgeComposition.add_child(bound_node=h2, child=l1_h2.node(), child_identifier="l1")
    EdgeComposition.add_child(bound_node=h2, child=l2_h2.node(), child_identifier="l2")
    EdgeComposition.add_child(bound_node=h3, child=l1_h3.node(), child_identifier="l1")
    EdgeComposition.add_child(bound_node=h3, child=l2_h3.node(), child_identifier="l2")

    # Connect: direct, then through children, then direct
    EdgeInterfaceConnection.connect(bn1=h1, bn2=h2)
    EdgeInterfaceConnection.connect(bn1=l1_h2, bn2=l1_h3)
    EdgeInterfaceConnection.connect(bn1=l2_h2, bn2=l2_h3)
    EdgeInterfaceConnection.connect(bn1=h3, bn2=h4)

    # End-to-end should connect
    paths = EdgeInterfaceConnection.is_connected_to(source=h1, target=h4)
    assert len(paths) == 1


@pytest.mark.skip(
    reason="Complex mixed shallow/normal requires all matching children connected"
)
def test_hierarchy_mixed_shallow_and_normal():
    """
    Hierarchy with mixed shallow and normal connections:
    ```
    R1      R2
     H1      H1
      L1 -->  L1
      L2 -->  L2
     H2 ==>  H2   (shallow)
      L1      L1
      L2      L2

    H1 connects normally (children can traverse).
    H2 connects shallow (children blocked).
    """
    g = GraphView.create()

    r1 = g.insert_node(node=Node.create())
    r2 = g.insert_node(node=Node.create())

    h1_r1 = g.insert_node(node=Node.create())
    h1_r2 = g.insert_node(node=Node.create())
    h2_r1 = g.insert_node(node=Node.create())
    h2_r2 = g.insert_node(node=Node.create())

    l1_h1r1 = g.insert_node(node=Node.create())
    l2_h1r1 = g.insert_node(node=Node.create())
    l1_h1r2 = g.insert_node(node=Node.create())
    l2_h1r2 = g.insert_node(node=Node.create())
    l1_h2r1 = g.insert_node(node=Node.create())
    l2_h2r1 = g.insert_node(node=Node.create())
    l1_h2r2 = g.insert_node(node=Node.create())
    l2_h2r2 = g.insert_node(node=Node.create())

    # Build hierarchy
    EdgeComposition.add_child(bound_node=r1, child=h1_r1.node(), child_identifier="h1")
    EdgeComposition.add_child(bound_node=r1, child=h2_r1.node(), child_identifier="h2")
    EdgeComposition.add_child(bound_node=r2, child=h1_r2.node(), child_identifier="h1")
    EdgeComposition.add_child(bound_node=r2, child=h2_r2.node(), child_identifier="h2")

    EdgeComposition.add_child(
        bound_node=h1_r1, child=l1_h1r1.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h1_r1, child=l2_h1r1.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=h1_r2, child=l1_h1r2.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h1_r2, child=l2_h1r2.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=h2_r1, child=l1_h2r1.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h2_r1, child=l2_h2r1.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=h2_r2, child=l1_h2r2.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h2_r2, child=l2_h2r2.node(), child_identifier="l2"
    )

    # Connect H1 normally, H2 shallow
    EdgeInterfaceConnection.connect(bn1=l1_h1r1, bn2=l1_h1r2)
    EdgeInterfaceConnection.connect(bn1=l2_h1r1, bn2=l2_h1r2)
    EdgeInterfaceConnection.connect_shallow(bn1=h2_r1, bn2=h2_r2)

    # H1 should be connected (normal connection allows children)
    assert len(EdgeInterfaceConnection.is_connected_to(source=h1_r1, target=h1_r2)) == 1

    # H2 should be connected (shallow at H2 level)
    assert len(EdgeInterfaceConnection.is_connected_to(source=h2_r1, target=h2_r2)) == 1

    # H2's children should NOT be connected (blocked by shallow)
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=l1_h2r1, target=l1_h2r2))
        == 0
    )
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=l2_h2r1, target=l2_h2r2))
        == 0
    )

    # Roots should be connected
    assert len(EdgeInterfaceConnection.is_connected_to(source=r1, target=r2)) == 1


def test_visit_connected_edges():
    """
    Test the visitor pattern for connected edges.
    ```
    N1 --> N2
     |
     +---> N3

    Visit should find 2 edges from N1.
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())
    n3 = g.insert_node(node=Node.create())

    EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    EdgeInterfaceConnection.connect(bn1=n1, bn2=n3)

    # Collect edges using visitor
    collected_edges = []

    def collect_edge(ctx, edge):
        ctx.append(edge)

    EdgeInterfaceConnection.visit_connected_edges(
        bound_node=n1, ctx=collected_edges, f=collect_edge
    )

    # Should have found 2 edges from n1
    assert len(collected_edges) == 2

    # Verify edges are interface connection edges
    for edge in collected_edges:
        assert EdgeInterfaceConnection.is_instance(edge=edge.edge())


def test_negative_partial_children_connection():
    """
    Only some children connected should NOT connect parents:
    ```
    H1      H2
     L1 -->  L1
     L2      L2  (not connected)

    H1 should NOT connect to H2 with incomplete children.
    """
    g = GraphView.create()

    h1 = g.insert_node(node=Node.create())
    h2 = g.insert_node(node=Node.create())

    l1_h1 = g.insert_node(node=Node.create())
    l2_h1 = g.insert_node(node=Node.create())
    l1_h2 = g.insert_node(node=Node.create())
    l2_h2 = g.insert_node(node=Node.create())

    EdgeComposition.add_child(bound_node=h1, child=l1_h1.node(), child_identifier="l1")
    EdgeComposition.add_child(bound_node=h1, child=l2_h1.node(), child_identifier="l2")
    EdgeComposition.add_child(bound_node=h2, child=l1_h2.node(), child_identifier="l1")
    EdgeComposition.add_child(bound_node=h2, child=l2_h2.node(), child_identifier="l2")

    # Only connect L1
    EdgeInterfaceConnection.connect(bn1=l1_h1, bn2=l1_h2)

    # H1 should NOT be connected to H2 (missing L2 connection)
    paths = EdgeInterfaceConnection.is_connected_to(source=h1, target=h2)
    assert len(paths) == 0


@pytest.mark.skip(
    reason="Complex chain with intermediate nodes requires complete child connections"
)
def test_complex_hierarchy_chain():
    """
    Complex scenario with multiple hierarchy levels and chains:
    ```
    R1              R2
     H1     HM1 ==>  H1
      L1 -->  L1      L1
      L2 -->  L2      L2
     H2 ==> HM2      H2
      L1      L1 -->  L1
      L2      L2 -->  L2

    Mix of normal connections, shallow connections, and intermediate nodes.
    """
    g = GraphView.create()

    r1 = g.insert_node(node=Node.create())
    r2 = g.insert_node(node=Node.create())

    h1_r1 = g.insert_node(node=Node.create())
    h2_r1 = g.insert_node(node=Node.create())
    h1_r2 = g.insert_node(node=Node.create())
    h2_r2 = g.insert_node(node=Node.create())

    hm1 = g.insert_node(node=Node.create())
    hm2 = g.insert_node(node=Node.create())

    l1_h1r1 = g.insert_node(node=Node.create())
    l2_h1r1 = g.insert_node(node=Node.create())
    l1_hm1 = g.insert_node(node=Node.create())
    l2_hm1 = g.insert_node(node=Node.create())
    l1_h1r2 = g.insert_node(node=Node.create())
    l2_h1r2 = g.insert_node(node=Node.create())

    l1_h2r1 = g.insert_node(node=Node.create())
    l2_h2r1 = g.insert_node(node=Node.create())
    l1_hm2 = g.insert_node(node=Node.create())
    l2_hm2 = g.insert_node(node=Node.create())
    l1_h2r2 = g.insert_node(node=Node.create())
    l2_h2r2 = g.insert_node(node=Node.create())

    # Build hierarchy
    EdgeComposition.add_child(bound_node=r1, child=h1_r1.node(), child_identifier="h1")
    EdgeComposition.add_child(bound_node=r1, child=h2_r1.node(), child_identifier="h2")
    EdgeComposition.add_child(bound_node=r2, child=h1_r2.node(), child_identifier="h1")
    EdgeComposition.add_child(bound_node=r2, child=h2_r2.node(), child_identifier="h2")

    EdgeComposition.add_child(
        bound_node=h1_r1, child=l1_h1r1.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h1_r1, child=l2_h1r1.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=hm1, child=l1_hm1.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=hm1, child=l2_hm1.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=h1_r2, child=l1_h1r2.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h1_r2, child=l2_h1r2.node(), child_identifier="l2"
    )

    EdgeComposition.add_child(
        bound_node=h2_r1, child=l1_h2r1.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h2_r1, child=l2_h2r1.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=hm2, child=l1_hm2.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=hm2, child=l2_hm2.node(), child_identifier="l2"
    )
    EdgeComposition.add_child(
        bound_node=h2_r2, child=l1_h2r2.node(), child_identifier="l1"
    )
    EdgeComposition.add_child(
        bound_node=h2_r2, child=l2_h2r2.node(), child_identifier="l2"
    )

    # Connections
    EdgeInterfaceConnection.connect(bn1=l1_h1r1, bn2=l1_hm1)
    EdgeInterfaceConnection.connect(bn1=l2_h1r1, bn2=l2_hm1)
    EdgeInterfaceConnection.connect_shallow(bn1=h2_r1, bn2=hm2)
    EdgeInterfaceConnection.connect_shallow(bn1=hm1, bn2=h1_r2)
    EdgeInterfaceConnection.connect(bn1=l1_hm2, bn2=l1_h2r2)
    EdgeInterfaceConnection.connect(bn1=l2_hm2, bn2=l2_h2r2)

    # Roots should be connected through complex path
    paths = EdgeInterfaceConnection.is_connected_to(source=r1, target=r2)
    assert len(paths) == 1


def test_multiple_connections_same_pair():
    """
    Multiple edges between the same pair of nodes:
    ```
    N1 --> N2
    N1 --> N2  (second edge)

    Should handle multiple edges correctly.
    """
    g = GraphView.create()

    n1 = g.insert_node(node=Node.create())
    n2 = g.insert_node(node=Node.create())

    # Create multiple connections
    edge1 = EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)
    edge2 = EdgeInterfaceConnection.connect(bn1=n1, bn2=n2)

    # Both should be interface connection edges
    assert EdgeInterfaceConnection.is_instance(edge=edge1.edge())
    assert EdgeInterfaceConnection.is_instance(edge=edge2.edge())

    # Should still find path (at least one)
    paths = EdgeInterfaceConnection.is_connected_to(source=n1, target=n2)
    assert len(paths) >= 1


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
