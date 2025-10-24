# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import GraphView, Node

# ============================================================================
# Group 1: Working tests matching test_mif_connect.py
# ============================================================================


def test_self():
    g = GraphView.create()
    bn1 = g.insert_node(node=Node.create())

    assert EdgeInterfaceConnection.is_connected_to(source=bn1, target=bn1)


def test_down_connect():
    """
    ```
    P1 -->  P2
     HV      HV
     LV      LV
    ```
    """
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    # Create type hierarchy
    ElectricPowerType = tg.add_type(identifier="ElectricPower")
    ElectricalType = tg.add_type(identifier="Electrical")

    # Add children to ElectricPower type
    tg.add_make_child(
        type_node=ElectricPowerType, 
        child_type_node=ElectricalType, 
        identifier="HV"
    )
    tg.add_make_child(
        type_node=ElectricPowerType, 
        child_type_node=ElectricalType, 
        identifier="LV"
    )

    # Create instances
    ep = [tg.instantiate_node(type_node=ElectricPowerType, attributes={}) for _ in range(2)]
    
    # Get child nodes using EdgeComposition
    hv = [EdgeComposition.get_child_by_identifier(bound_node=ep[i], child_identifier="HV") for i in range(2)]
    lv = [EdgeComposition.get_child_by_identifier(bound_node=ep[i], child_identifier="LV") for i in range(2)]

    EdgeInterfaceConnection.connect(bn1=ep[0], bn2=ep[1])

    assert EdgeInterfaceConnection.is_connected_to(source=ep[0], target=ep[1])
    assert EdgeInterfaceConnection.is_connected_to(source=hv[0], target=hv[1])
    assert EdgeInterfaceConnection.is_connected_to(source=lv[0], target=lv[1])


def test_chains_direct():
    """
    ```
    M1 --> M2 --> M3
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(3)]
    EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[1])
    EdgeInterfaceConnection.connect(bn1=bns[1], bn2=bns[2])
    assert EdgeInterfaceConnection.is_connected_to(source=bns[0], target=bns[2])


def test_chains_double_shallow_flat():
    """
    ```
    M1 ==> M2 ==> M3
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(3)]
    EdgeInterfaceConnection.connect_shallow(bn1=bns[0], bn2=bns[1])
    EdgeInterfaceConnection.connect_shallow(bn1=bns[1], bn2=bns[2])

    assert EdgeInterfaceConnection.is_connected_to(source=bns[0], target=bns[2])


def test_chains_mixed_shallow_flat():
    """
    ```
    M1 ==> M2 --> M3
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(3)]
    EdgeInterfaceConnection.connect_shallow(bn1=bns[0], bn2=bns[1])
    EdgeInterfaceConnection.connect(bn1=bns[1], bn2=bns[2])

    assert EdgeInterfaceConnection.is_connected_to(source=bns[0], target=bns[2])


def test_chains_mixed_shallow_nested():
    """
    ```
    L1  ==>  L2 -->  L3
     S        S       S
     R        R       R
      HV       HV      HV
      LV       LV      LV
    ```
    """
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    # Create type hierarchy
    ElType = tg.add_type(identifier="El")
    LineType = tg.add_type(identifier="Line")
    RefType = tg.add_type(identifier="Ref")
    HVType = tg.add_type(identifier="HV")
    LVType = tg.add_type(identifier="LV")

    # Add children to El type
    tg.add_make_child(
        type_node=ElType, 
        child_type_node=LineType, 
        identifier="line"
    )
    tg.add_make_child(
        type_node=ElType, 
        child_type_node=RefType, 
        identifier="reference"
    )
    
    # Add children to Ref type
    tg.add_make_child(
        type_node=RefType, 
        child_type_node=HVType, 
        identifier="hv"
    )
    tg.add_make_child(
        type_node=RefType, 
        child_type_node=LVType, 
        identifier="lv"
    )

    # Create instances
    el = [tg.instantiate_node(type_node=ElType, attributes={}) for _ in range(3)]
    
    # Get child nodes
    line = [EdgeComposition.get_child_by_identifier(bound_node=el[i], child_identifier="line") for i in range(3)]
    ref = [EdgeComposition.get_child_by_identifier(bound_node=el[i], child_identifier="reference") for i in range(3)]
    hv = [EdgeComposition.get_child_by_identifier(bound_node=ref[i], child_identifier="hv") for i in range(3)]
    lv = [EdgeComposition.get_child_by_identifier(bound_node=ref[i], child_identifier="lv") for i in range(3)]

    EdgeInterfaceConnection.connect_shallow(bn1=el[0], bn2=el[1])
    EdgeInterfaceConnection.connect(bn1=el[1], bn2=el[2])
    assert EdgeInterfaceConnection.is_connected_to(source=el[0], target=el[2])

    assert EdgeInterfaceConnection.is_connected_to(source=line[1], target=line[2])
    assert EdgeInterfaceConnection.is_connected_to(source=ref[1], target=ref[2])
    assert not EdgeInterfaceConnection.is_connected_to(source=line[0], target=line[1])
    assert not EdgeInterfaceConnection.is_connected_to(source=ref[0], target=ref[1])
    assert not EdgeInterfaceConnection.is_connected_to(source=line[0], target=line[2])
    assert not EdgeInterfaceConnection.is_connected_to(source=ref[0], target=ref[2])

    EdgeInterfaceConnection.connect(bn1=line[0], bn2=line[1])
    EdgeInterfaceConnection.connect(bn1=ref[0], bn2=ref[1])
    assert EdgeInterfaceConnection.is_connected_to(source=el[0], target=el[1])
    assert EdgeInterfaceConnection.is_connected_to(source=el[0], target=el[2])


@pytest.mark.slow
def test_loooooong_chain():
    """
    ```
    N1 --> N2 --> N3 --> ... --> N1000
    ```
    """
    g = GraphView.create()

    chain_length = 1000
    nodes = [g.insert_node(node=Node.create()) for _ in range(chain_length)]

    for i in range(chain_length - 1):
        EdgeInterfaceConnection.connect(bn1=nodes[i], bn2=nodes[i + 1])

    paths = EdgeInterfaceConnection.is_connected_to(source=nodes[0], target=nodes[-1])
    assert len(paths) == 1
    assert paths[0] == chain_length - 1


def test_split_flip_negative():
    """
    ```
    H1     H2
     L1 --> L2
     L2 --> L1
    ```
    """
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    # Create type hierarchy
    HighType = tg.add_type(identifier="High")
    Lower1Type = tg.add_type(identifier="Lower1")
    Lower2Type = tg.add_type(identifier="Lower2")

    # Add children to High type
    tg.add_make_child(
        type_node=HighType, 
        child_type_node=Lower1Type, 
        identifier="lower1"
    )
    tg.add_make_child(
        type_node=HighType, 
        child_type_node=Lower2Type, 
        identifier="lower2"
    )

    # Create instances
    high = [tg.instantiate_node(type_node=HighType, attributes={}) for _ in range(2)]
    
    # Get child nodes
    lower1 = [EdgeComposition.get_child_by_identifier(bound_node=high[i], child_identifier="lower1") for i in range(2)]
    lower2 = [EdgeComposition.get_child_by_identifier(bound_node=high[i], child_identifier="lower2") for i in range(2)]

    EdgeInterfaceConnection.connect(bn1=lower1[0], bn2=lower2[1])
    EdgeInterfaceConnection.connect(bn1=lower2[0], bn2=lower1[1])

    assert not EdgeInterfaceConnection.is_connected_to(source=high[0], target=high[1])


def test_up_connect_simple_two_negative():
    """
    ```
    H1      H2
     L1 -->  L1
     L2      L2
    ```
    """
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    # Create type hierarchy
    HighType = tg.add_type(identifier="High")
    Lower1Type = tg.add_type(identifier="Lower1")
    Lower2Type = tg.add_type(identifier="Lower2")

    # Add children to High type
    tg.add_make_child(
        type_node=HighType, 
        child_type_node=Lower1Type, 
        identifier="lower1"
    )
    tg.add_make_child(
        type_node=HighType, 
        child_type_node=Lower2Type, 
        identifier="lower2"
    )

    # Create instances
    high = [tg.instantiate_node(type_node=HighType, attributes={}) for _ in range(2)]
    
    # Get child nodes
    lower1 = [EdgeComposition.get_child_by_identifier(bound_node=high[i], child_identifier="lower1") for i in range(2)]
    lower2 = [EdgeComposition.get_child_by_identifier(bound_node=high[i], child_identifier="lower2") for i in range(2)]

    EdgeInterfaceConnection.connect(bn1=lower1[0], bn2=lower1[1])
    assert not EdgeInterfaceConnection.is_connected_to(source=high[0], target=high[1])


# ============================================================================
# Group 2: Skipped tests matching test_mif_connect.py (incomplete implementation)
# ============================================================================


@pytest.mark.skip(reason="Requires all children paths to complete")
def test_split_chain_single():
    """
    ```
    H1     H2 --> H3
     L1 --> L1     L1
     L2     L2     L2
      |            ^
      +------------+
    ```
    """
    g = GraphView.create()

    h = [g.insert_node(node=Node.create()) for _ in range(3)]
    l1 = [g.insert_node(node=Node.create()) for _ in range(3)]
    l2 = [g.insert_node(node=Node.create()) for _ in range(3)]

    for i in range(3):
        EdgeComposition.add_child(
            bound_node=h[i], child=l1[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=h[i], child=l2[i].node(), child_identifier="l2"
        )

    EdgeInterfaceConnection.connect(bn1=l1[0], bn2=l1[1])
    EdgeInterfaceConnection.connect(bn1=l2[0], bn2=l2[1])
    EdgeInterfaceConnection.connect(bn1=h[1], bn2=h[2])

    assert EdgeInterfaceConnection.is_connected_to(source=h[0], target=h[2])


@pytest.mark.skip(reason="Requires all children paths to complete")
def test_split_chain_flip():
    """
    ```
    H1     H2 ==> H3     H4
     L1 --> L2     L2 --> L1
     L2 --> L1     L1 --> L2
    ```
    """
    g = GraphView.create()

    h = [g.insert_node(node=Node.create()) for _ in range(4)]
    l1 = [g.insert_node(node=Node.create()) for _ in range(4)]
    l2 = [g.insert_node(node=Node.create()) for _ in range(4)]

    for i in range(4):
        EdgeComposition.add_child(
            bound_node=h[i], child=l1[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=h[i], child=l2[i].node(), child_identifier="l2"
        )

    EdgeInterfaceConnection.connect(bn1=l1[0], bn2=l2[1])
    EdgeInterfaceConnection.connect(bn1=l2[0], bn2=l1[1])
    EdgeInterfaceConnection.connect_shallow(bn1=h[1], bn2=h[2])
    EdgeInterfaceConnection.connect(bn1=l1[2], bn2=l2[3])
    EdgeInterfaceConnection.connect(bn1=l2[2], bn2=l1[3])

    assert EdgeInterfaceConnection.is_connected_to(source=h[0], target=h[3])


@pytest.mark.skip(reason="Requires all children paths to complete")
def test_up_connect_chain_multiple_same():
    """
    ```
    H1      H2      H3
     L1 -->  L1 -->  L1
     L2 -->  L2 -->  L2
    ```
    """
    g = GraphView.create()

    h = [g.insert_node(node=Node.create()) for _ in range(3)]
    l1 = [g.insert_node(node=Node.create()) for _ in range(3)]
    l2 = [g.insert_node(node=Node.create()) for _ in range(3)]

    for i in range(3):
        EdgeComposition.add_child(
            bound_node=h[i], child=l1[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=h[i], child=l2[i].node(), child_identifier="l2"
        )

    EdgeInterfaceConnection.connect(bn1=l1[0], bn2=l1[1])
    EdgeInterfaceConnection.connect(bn1=l2[0], bn2=l2[1])
    EdgeInterfaceConnection.connect(bn1=l1[1], bn2=l1[2])
    EdgeInterfaceConnection.connect(bn1=l2[1], bn2=l2[2])

    assert len(EdgeInterfaceConnection.is_connected_to(source=h[0], target=h[2])) == 1


@pytest.mark.skip(reason="Requires all children paths to complete")
def test_alternating_hierarchy_levels():
    """
    ```
    H1 --> H2      H3 --> H4
            L1 -->  L1
            L2 -->  L2
    ```
    """
    g = GraphView.create()

    h = [g.insert_node(node=Node.create()) for _ in range(4)]
    l1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    l2 = [g.insert_node(node=Node.create()) for _ in range(2)]

    for i in range(2):
        EdgeComposition.add_child(
            bound_node=h[i + 1], child=l1[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=h[i + 1], child=l2[i].node(), child_identifier="l2"
        )

    EdgeInterfaceConnection.connect(bn1=h[0], bn2=h[1])
    EdgeInterfaceConnection.connect(bn1=l1[0], bn2=l1[1])
    EdgeInterfaceConnection.connect(bn1=l2[0], bn2=l2[1])
    EdgeInterfaceConnection.connect(bn1=h[2], bn2=h[3])

    assert len(EdgeInterfaceConnection.is_connected_to(source=h[0], target=h[3])) == 1


@pytest.mark.skip(reason="Requires all children paths to complete")
def test_up_connect_hierarchy_mixed():
    """
    ```
    R1      R2
     H1      H1
      L1 -->  L1
      L2 -->  L2
     H2 ==>  H2
      L1      L1
      L2      L2
    ```
    """
    g = GraphView.create()

    r = [g.insert_node(node=Node.create()) for _ in range(2)]
    h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    h2 = [g.insert_node(node=Node.create()) for _ in range(2)]
    l1_h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    l2_h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    l1_h2 = [g.insert_node(node=Node.create()) for _ in range(2)]
    l2_h2 = [g.insert_node(node=Node.create()) for _ in range(2)]

    for i in range(2):
        EdgeComposition.add_child(
            bound_node=r[i], child=h1[i].node(), child_identifier="h1"
        )
        EdgeComposition.add_child(
            bound_node=r[i], child=h2[i].node(), child_identifier="h2"
        )
        EdgeComposition.add_child(
            bound_node=h1[i], child=l1_h1[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=h1[i], child=l2_h1[i].node(), child_identifier="l2"
        )
        EdgeComposition.add_child(
            bound_node=h2[i], child=l1_h2[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=h2[i], child=l2_h2[i].node(), child_identifier="l2"
        )

    EdgeInterfaceConnection.connect(bn1=l1_h1[0], bn2=l1_h1[1])
    EdgeInterfaceConnection.connect(bn1=l2_h1[0], bn2=l2_h1[1])
    EdgeInterfaceConnection.connect_shallow(bn1=h2[0], bn2=h2[1])

    assert len(EdgeInterfaceConnection.is_connected_to(source=h1[0], target=h1[1])) == 1
    assert len(EdgeInterfaceConnection.is_connected_to(source=h2[0], target=h2[1])) == 1
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=l1_h2[0], target=l1_h2[1]))
        == 0
    )
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=l2_h2[0], target=l2_h2[1]))
        == 0
    )
    assert len(EdgeInterfaceConnection.is_connected_to(source=r[0], target=r[1])) == 1


@pytest.mark.skip(reason="Requires all children paths to complete")
def test_up_connect_chain_hierarchy():
    """
    ```
    R1              R2
     H1     HM1 ==>  H1
      L1 -->  L1      L1
      L2 -->  L2      L2
     H2 ==> HM2      H2
      L1      L1 -->  L1
      L2      L2 -->  L2
    ```
    """
    g = GraphView.create()

    r = [g.insert_node(node=Node.create()) for _ in range(2)]
    h1_r = [g.insert_node(node=Node.create()) for _ in range(2)]
    h2_r = [g.insert_node(node=Node.create()) for _ in range(2)]
    hm = [g.insert_node(node=Node.create()) for _ in range(2)]

    l1_h1r = [g.insert_node(node=Node.create()) for _ in range(2)]
    l2_h1r = [g.insert_node(node=Node.create()) for _ in range(2)]
    l1_hm = [g.insert_node(node=Node.create()) for _ in range(2)]
    l2_hm = [g.insert_node(node=Node.create()) for _ in range(2)]
    l1_h2r = [g.insert_node(node=Node.create()) for _ in range(2)]
    l2_h2r = [g.insert_node(node=Node.create()) for _ in range(2)]

    for i in range(2):
        EdgeComposition.add_child(
            bound_node=r[i], child=h1_r[i].node(), child_identifier="h1"
        )
        EdgeComposition.add_child(
            bound_node=r[i], child=h2_r[i].node(), child_identifier="h2"
        )
        EdgeComposition.add_child(
            bound_node=h1_r[i], child=l1_h1r[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=h1_r[i], child=l2_h1r[i].node(), child_identifier="l2"
        )
        EdgeComposition.add_child(
            bound_node=h2_r[i], child=l1_h2r[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=h2_r[i], child=l2_h2r[i].node(), child_identifier="l2"
        )
        EdgeComposition.add_child(
            bound_node=hm[i], child=l1_hm[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=hm[i], child=l2_hm[i].node(), child_identifier="l2"
        )

    EdgeInterfaceConnection.connect(bn1=l1_h1r[0], bn2=l1_hm[0])
    EdgeInterfaceConnection.connect(bn1=l2_h1r[0], bn2=l2_hm[0])
    EdgeInterfaceConnection.connect_shallow(bn1=h2_r[0], bn2=hm[1])
    EdgeInterfaceConnection.connect_shallow(bn1=hm[0], bn2=h1_r[1])
    EdgeInterfaceConnection.connect(bn1=l1_hm[1], bn2=l1_h2r[1])
    EdgeInterfaceConnection.connect(bn1=l2_hm[1], bn2=l2_h2r[1])

    assert len(EdgeInterfaceConnection.is_connected_to(source=r[0], target=r[1])) == 1


@pytest.mark.skip(reason="Requires all children paths to complete")
def test_multi_level_hierarchy():
    """
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
    ```
    """
    g = GraphView.create()

    r = [g.insert_node(node=Node.create()) for _ in range(2)]
    h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    h2 = [g.insert_node(node=Node.create()) for _ in range(2)]
    m1_h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    m2_h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    m1_h2 = [g.insert_node(node=Node.create()) for _ in range(2)]

    l1_m1h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    l2_m1h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    l1_m2h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    l2_m2h1 = [g.insert_node(node=Node.create()) for _ in range(2)]
    l1_m1h2 = [g.insert_node(node=Node.create()) for _ in range(2)]

    for i in range(2):
        EdgeComposition.add_child(
            bound_node=r[i], child=h1[i].node(), child_identifier="h1"
        )
        EdgeComposition.add_child(
            bound_node=r[i], child=h2[i].node(), child_identifier="h2"
        )
        EdgeComposition.add_child(
            bound_node=h1[i], child=m1_h1[i].node(), child_identifier="m1"
        )
        EdgeComposition.add_child(
            bound_node=h1[i], child=m2_h1[i].node(), child_identifier="m2"
        )
        EdgeComposition.add_child(
            bound_node=h2[i], child=m1_h2[i].node(), child_identifier="m1"
        )
        EdgeComposition.add_child(
            bound_node=m1_h1[i], child=l1_m1h1[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=m1_h1[i], child=l2_m1h1[i].node(), child_identifier="l2"
        )
        EdgeComposition.add_child(
            bound_node=m2_h1[i], child=l1_m2h1[i].node(), child_identifier="l1"
        )
        EdgeComposition.add_child(
            bound_node=m2_h1[i], child=l2_m2h1[i].node(), child_identifier="l2"
        )
        EdgeComposition.add_child(
            bound_node=m1_h2[i], child=l1_m1h2[i].node(), child_identifier="l1"
        )

    EdgeInterfaceConnection.connect(bn1=l1_m1h1[0], bn2=l1_m1h1[1])
    EdgeInterfaceConnection.connect(bn1=l2_m1h1[0], bn2=l2_m1h1[1])
    EdgeInterfaceConnection.connect(bn1=l1_m2h1[0], bn2=l1_m2h1[1])
    EdgeInterfaceConnection.connect(bn1=l2_m2h1[0], bn2=l2_m2h1[1])
    EdgeInterfaceConnection.connect(bn1=l1_m1h2[0], bn2=l1_m1h2[1])

    assert (
        len(
            EdgeInterfaceConnection.is_connected_to(
                source=l1_m1h1[0], target=l1_m1h1[1]
            )
        )
        == 1
    )
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=m1_h1[0], target=m1_h1[1]))
        == 1
    )
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=m2_h1[0], target=m2_h1[1]))
        == 1
    )
    assert len(EdgeInterfaceConnection.is_connected_to(source=h1[0], target=h1[1])) == 1
    assert (
        len(EdgeInterfaceConnection.is_connected_to(source=m1_h2[0], target=m1_h2[1]))
        == 1
    )
    assert len(EdgeInterfaceConnection.is_connected_to(source=h2[0], target=h2[1])) == 1
    assert len(EdgeInterfaceConnection.is_connected_to(source=r[0], target=r[1])) == 1


# ============================================================================
# Group 3: Zig-specific tests (no equivalent in test_mif_connect.py)
# ============================================================================


def test_basic_connection():
    """
    ```
    N1 --> N2
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(2)]

    edge = EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[1])

    assert EdgeInterfaceConnection.is_instance(edge=edge.edge())
    assert edge.edge().edge_type() == EdgeInterfaceConnection.get_tid()

    paths = EdgeInterfaceConnection.is_connected_to(source=bns[0], target=bns[1])
    assert len(paths) == 1
    assert paths[0] == 1


def test_not_connected():
    """
    ```
    N1     N2
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(2)]

    assert not EdgeInterfaceConnection.is_connected_to(source=bns[0], target=bns[1])


def test_get_connected():
    """
    ```
    N1 --> N2 --> N3
     |
     +---> N4
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(4)]

    EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[1])
    EdgeInterfaceConnection.connect(bn1=bns[1], bn2=bns[2])
    EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[3])

    all_paths = EdgeInterfaceConnection.get_connected(source=bns[0])
    assert len(all_paths) == 4


def test_no_parent_to_child():
    """
    ```
    P1
     C1
    ```
    """
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    # Create type hierarchy
    ParentType = tg.add_type(identifier="Parent")
    ChildType = tg.add_type(identifier="Child")

    # Add child to parent type
    tg.add_make_child(
        type_node=ParentType, 
        child_type_node=ChildType, 
        identifier="c1"
    )

    # Create instances
    parent = tg.instantiate_node(type_node=ParentType, attributes={})
    child = EdgeComposition.get_child_by_identifier(bound_node=parent, child_identifier="c1")

    assert not EdgeInterfaceConnection.is_connected_to(source=parent, target=child)


def test_no_sibling_connection():
    """
    ```
    P1
     C1
     C2
    ```
    """
    g = GraphView.create()

    parent = g.insert_node(node=Node.create())
    children = [g.insert_node(node=Node.create()) for _ in range(2)]

    EdgeComposition.add_child(
        bound_node=parent, child=children[0].node(), child_identifier="c1"
    )
    EdgeComposition.add_child(
        bound_node=parent, child=children[1].node(), child_identifier="c2"
    )

    assert not EdgeInterfaceConnection.is_connected_to(
        source=children[0], target=children[1]
    )


def test_shallow_connection_simple():
    """
    ```
    N1 ==> N2
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(2)]

    EdgeInterfaceConnection.connect_shallow(bn1=bns[0], bn2=bns[1])

    assert EdgeInterfaceConnection.is_connected_to(source=bns[0], target=bns[1])


def test_shallow_connection_blocks_children():
    """
    ```
    P1 ==> P2
     C1     C1
    ```
    """
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    # Create type hierarchy
    ParentType = tg.add_type(identifier="Parent")
    ChildType = tg.add_type(identifier="Child")

    # Add child to parent type
    tg.add_make_child(
        type_node=ParentType, 
        child_type_node=ChildType, 
        identifier="c1"
    )

    # Create instances
    parents = [tg.instantiate_node(type_node=ParentType, attributes={}) for _ in range(2)]
    
    # Get child nodes
    children = [EdgeComposition.get_child_by_identifier(bound_node=parents[i], child_identifier="c1") for i in range(2)]

    EdgeInterfaceConnection.connect_shallow(bn1=parents[0], bn2=parents[1])

    assert EdgeInterfaceConnection.is_connected_to(source=parents[0], target=parents[1])
    assert not EdgeInterfaceConnection.is_connected_to(
        source=children[0], target=children[1]
    )


def test_multiple_paths():
    r"""
    ```
         N3
        /  \
    N1 -- N2 -- N4
        \  /
         N5
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(5)]

    EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[1])
    EdgeInterfaceConnection.connect(bn1=bns[1], bn2=bns[3])
    EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[2])
    EdgeInterfaceConnection.connect(bn1=bns[2], bn2=bns[3])
    EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[4])
    EdgeInterfaceConnection.connect(bn1=bns[4], bn2=bns[3])

    assert EdgeInterfaceConnection.is_connected_to(source=bns[0], target=bns[3])


def test_get_other_connected_node():
    """
    ```
    N1 -- E1 -- N2
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(3)]

    be = EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[1])
    edge = be.edge()

    other_from_0 = EdgeInterfaceConnection.get_other_connected_node(
        edge=edge, node=bns[0].node()
    )
    assert other_from_0 is not None
    assert other_from_0.is_same(other=bns[1].node())

    other_from_1 = EdgeInterfaceConnection.get_other_connected_node(
        edge=edge, node=bns[1].node()
    )
    assert other_from_1 is not None
    assert other_from_1.is_same(other=bns[0].node())

    other_from_2 = EdgeInterfaceConnection.get_other_connected_node(
        edge=edge, node=bns[2].node()
    )
    assert other_from_2 is None


def test_edge_type_consistency():
    """Verify EdgeInterfaceConnection edges have consistent type IDs."""
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(4)]

    tid = EdgeInterfaceConnection.get_tid()
    assert tid > 0

    be = EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[1])
    edge = be.edge()

    assert edge.edge_type() == tid
    assert EdgeInterfaceConnection.is_instance(edge=edge)

    be_shallow = EdgeInterfaceConnection.connect_shallow(bn1=bns[2], bn2=bns[3])
    edge_shallow = be_shallow.edge()

    assert edge_shallow.edge_type() == tid
    assert EdgeInterfaceConnection.is_instance(edge=edge_shallow)


def test_composition_and_interface_edges():
    """Test composition hierarchy with interface connections."""
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    # Create type hierarchy
    RootType = tg.add_type(identifier="Root")
    ChildType = tg.add_type(identifier="Child")

    # Add child to root type
    tg.add_make_child(
        type_node=RootType, 
        child_type_node=ChildType, 
        identifier="child"
    )

    # Create instances
    roots = [tg.instantiate_node(type_node=RootType, attributes={}) for _ in range(2)]
    
    # Get child nodes
    children = [EdgeComposition.get_child_by_identifier(bound_node=roots[i], child_identifier="child") for i in range(2)]

    EdgeInterfaceConnection.connect(bn1=children[0], bn2=children[1])

    assert EdgeInterfaceConnection.is_connected_to(
        source=children[0], target=children[1]
    )
    assert not EdgeInterfaceConnection.is_connected_to(source=roots[0], target=roots[1])

    EdgeInterfaceConnection.connect(bn1=roots[0], bn2=roots[1])

    paths = EdgeInterfaceConnection.is_connected_to(source=roots[0], target=roots[1])
    assert len(paths) == 1
    assert paths[0] == 1


def test_visit_connected_edges():
    """
    ```
    N1 --> N2
     |
     +---> N3
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(3)]

    EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[1])
    EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[2])

    collected_edges = []

    def collect_edge(ctx, edge):
        ctx.append(edge)

    EdgeInterfaceConnection.visit_connected_edges(
        bound_node=bns[0], ctx=collected_edges, f=collect_edge
    )

    assert len(collected_edges) == 2

    for edge in collected_edges:
        assert EdgeInterfaceConnection.is_instance(edge=edge.edge())


def test_multiple_connections_same_pair():
    """
    ```
    N1 --> N2
    N1 --> N2
    ```
    """
    g = GraphView.create()

    bns = [g.insert_node(node=Node.create()) for _ in range(2)]

    edge1 = EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[1])
    edge2 = EdgeInterfaceConnection.connect(bn1=bns[0], bn2=bns[1])

    assert EdgeInterfaceConnection.is_instance(edge=edge1.edge())
    assert EdgeInterfaceConnection.is_instance(edge=edge2.edge())

    assert EdgeInterfaceConnection.is_connected_to(source=bns[0], target=bns[1])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
