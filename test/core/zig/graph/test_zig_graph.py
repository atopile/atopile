def test_load_graph_module():
    from faebryk.core.zig.gen.graph.graph import GraphView  # type: ignore  # noqa: F401


def test_minimal_graph():
    from faebryk.core.zig.gen.graph.graph import (  # type: ignore
        Edge,
        GraphView,
        fabll.Node,
    )

    g = GraphView.create()

    n1 = fabll.Node.create()
    n2 = fabll.Node.create()
    n3 = fabll.Node.create()
    e120 = Edge.create(source=n1, target=n2, edge_type=0)
    e130 = Edge.create(source=n1, target=n3, edge_type=0)
    e121 = Edge.create(source=n1, target=n2, edge_type=1)

    bn1 = g.insert_node(node=n1)
    g.insert_node(node=n2)
    g.insert_node(node=n3)
    g.insert_edge(edge=e120)
    g.insert_edge(edge=e130)
    g.insert_edge(edge=e121)

    # print(repr(g))

    class Ctx:
        def __init__(self):
            self.edges = []

    ctx = Ctx()

    bn1.visit_edges_of_type(
        edge_type=0,
        ctx=ctx,
        f=lambda ctx, edge: ctx.edges.append(edge.edge()),
    )

    assert len(ctx.edges) == 2

    for edge in ctx.edges:
        print(edge)


def test_edge_composition_create():
    from faebryk.core.zig.gen.faebryk.composition import EdgeComposition  # type: ignore
    from faebryk.core.zig.gen.graph.graph import fabll.Node  # type: ignore

    parent = fabll.Node.create()
    child = fabll.Node.create()

    edge = EdgeComposition.create(parent=parent, child=child, child_identifier="kid")

    assert EdgeComposition.is_instance(edge=edge) is True
    assert edge.directional() is True
    assert EdgeComposition.get_name(edge=edge) == "kid"
    assert EdgeComposition.get_tid() == edge.edge_type()


def test_edge_composition_add_child_and_visit():
    from faebryk.core.zig.gen.faebryk.composition import (  # type: ignore
        EdgeComposition,
    )
    from faebryk.core.zig.gen.graph.graph import (  # type: ignore
        GraphView,
        fabll.Node,
    )

    graph = GraphView.create()
    parent = fabll.Node.create()
    child_a = fabll.Node.create()
    child_b = fabll.Node.create()

    parent_bound = graph.insert_node(node=parent)
    child_a_bound = graph.insert_node(node=child_a)
    child_b_bound = graph.insert_node(node=child_b)

    edge_a = EdgeComposition.add_child(
        bound_node=parent_bound, child=child_a, child_identifier="kid_a"
    )
    edge_b = EdgeComposition.add_child(
        bound_node=parent_bound, child=child_b, child_identifier="kid_b"
    )

    collected = []
    EdgeComposition.visit_children_edges(
        bound_node=parent_bound,
        ctx=collected,
        f=lambda ctx, bound_edge: ctx.append(
            EdgeComposition.get_name(edge=bound_edge.edge())
        ),
    )

    assert collected == ["kid_a", "kid_b"]

    parent_edge_a = EdgeComposition.get_parent_edge(bound_node=child_a_bound)
    assert parent_edge_a is not None
    assert parent_edge_a.edge().is_same(other=edge_a.edge())

    parent_edge_b = EdgeComposition.get_parent_edge(bound_node=child_b_bound)
    assert parent_edge_b is not None
    assert parent_edge_b.edge().is_same(other=edge_b.edge())

    assert EdgeComposition.get_parent_edge(bound_node=parent_bound) is None


def test_edge_type_create():
    from faebryk.core.zig.gen.faebryk.node_type import EdgeType  # type: ignore
    from faebryk.core.zig.gen.graph.graph import fabll.Node  # type: ignore

    type_node = fabll.Node.create()
    instance_node = fabll.Node.create()
    edge = EdgeType.create(type_node=type_node, instance_node=instance_node)

    assert EdgeType.is_instance(edge=edge) is True
    assert type_node.is_same(other=EdgeType.get_type_node(edge=edge))

    get_instance_node = EdgeType.get_instance_node(edge=edge)
    assert isinstance(get_instance_node, fabll.Node)
    assert instance_node.is_same(other=get_instance_node)


def test_edge_next():
    from faebryk.core.zig.gen.faebryk.next import EdgeNext  # type: ignore
    from faebryk.core.zig.gen.graph.graph import GraphView, fabll.Node  # type: ignore

    graph = GraphView.create()

    previous_node = fabll.Node.create()
    next_node = fabll.Node.create()
    previous_bound = graph.insert_node(node=previous_node)
    _ = graph.insert_node(node=next_node)
    edge = EdgeNext.create(previous_node=previous_node, next_node=next_node)
    _ = graph.insert_edge(edge=edge)
    assert EdgeNext.is_instance(edge=edge) is True
    get_next_node = EdgeNext.get_next_node_from_node(node=previous_bound)
    assert isinstance(get_next_node, fabll.Node)
    assert next_node.is_same(other=get_next_node)


def test_typegraph_instantiate():
    from faebryk.core.zig.gen.faebryk.composition import EdgeComposition  # type: ignore
    from faebryk.core.zig.gen.faebryk.pointer import EdgePointer  # type: ignore
    from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph  # type: ignore
    from faebryk.core.zig.gen.graph.graph import BoundEdge, GraphView  # type: ignore

    g = GraphView.create()
    type_graph = TypeGraph.create(g=g)

    Electrical = type_graph.add_type(identifier="Electrical")
    Resistor = type_graph.add_type(identifier="Resistor")
    type_graph.add_make_child(
        type_node=Resistor, child_type_node=Electrical, identifier="p1"
    )
    type_graph.add_make_child(
        type_node=Resistor, child_type_node=Electrical, identifier="p2"
    )

    rp1_ref = type_graph.add_reference(type_node=Resistor, path=["p1"])
    rp2_ref = type_graph.add_reference(type_node=Resistor, path=["p2"])
    type_graph.add_make_link(
        type_node=Resistor,
        lhs_reference_node=rp1_ref.node(),
        rhs_reference_node=rp2_ref.node(),
        edge_type=EdgePointer.get_tid(),
        edge_directional=True,
        edge_name="test",
        edge_attributes={"test_key": "test_value"},
    )

    resistor_instance = type_graph.instantiate(type_identifier="Resistor")

    collected = []
    EdgeComposition.visit_children_edges(
        bound_node=resistor_instance,
        ctx=collected,
        f=lambda ctx, bound_edge: ctx.append(
            EdgeComposition.get_name(edge=bound_edge.edge())
        ),
    )

    assert collected == ["p1", "p2"]

    rp1 = EdgeComposition.get_child_by_identifier(
        node=resistor_instance, child_identifier="p1"
    )
    rp2 = EdgeComposition.get_child_by_identifier(
        node=resistor_instance, child_identifier="p2"
    )
    assert rp1 is not None
    assert rp2 is not None
    collect = list[BoundEdge]()
    rp1.visit_edges_of_type(
        edge_type=EdgePointer.get_tid(),
        ctx=collect,
        f=lambda ctx, bound_edge: ctx.append(bound_edge),
    )

    assert len(collect) == 1
    e = collect[0].edge()
    assert e.source().is_same(other=rp1.node())
    assert e.target().is_same(other=rp2.node())
    assert e.directional() is True
    assert e.name() == "test"
    assert e.get_attr(key="test_key") == "test_value", e.get_attr(key="test_key")


if __name__ == "__main__":
    test_minimal_graph()
    test_edge_composition_create()
    test_edge_composition_add_child_and_visit()
    test_edge_type_create()
    test_edge_next()
    test_typegraph_instantiate()

    print("-" * 80)
    print("All tests passed")
