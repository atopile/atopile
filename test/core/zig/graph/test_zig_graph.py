import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph


def test_load_graph_module():
    from faebryk.core.zig.gen.graph.graph import GraphView  # type: ignore  # noqa: F401


def test_minimal_graph():
    from faebryk.core.zig.gen.graph.graph import (  # type: ignore
        Edge,
        GraphView,
        Node,
    )

    g = GraphView.create()

    n1 = Node.create()
    n2 = Node.create()
    n3 = Node.create()
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


def test_node_count():
    from faebryk.core.zig.gen.graph.graph import (  # type: ignore
        GraphView,
        Node,
    )

    g = GraphView.create()

    # GraphView starts with 1 node (the self_node)
    assert g.get_node_count() == 1

    n1 = Node.create()
    n2 = Node.create()
    n3 = Node.create()

    g.insert_node(node=n1)
    assert g.get_node_count() == 2

    g.insert_node(node=n2)
    assert g.get_node_count() == 3

    g.insert_node(node=n3)
    assert g.get_node_count() == 4


def test_edge_composition_create():
    parent = graph.Node.create()
    child = graph.Node.create()

    edge = fbrk.EdgeComposition.create(
        parent=parent, child=child, child_identifier="kid"
    )

    assert fbrk.EdgeComposition.is_instance(edge=edge) is True
    assert edge.directional() is True
    assert fbrk.EdgeComposition.get_name(edge=edge) == "kid"
    assert fbrk.EdgeComposition.get_tid() == edge.edge_type()


def test_edge_composition_add_child_and_visit():
    g = graph.GraphView.create()
    parent = graph.Node.create()
    child_a = graph.Node.create()
    child_b = graph.Node.create()

    parent_bound = g.insert_node(node=parent)
    child_a_bound = g.insert_node(node=child_a)
    child_b_bound = g.insert_node(node=child_b)

    edge_a = fbrk.EdgeComposition.add_child(
        bound_node=parent_bound, child=child_a, child_identifier="kid_a"
    )
    edge_b = fbrk.EdgeComposition.add_child(
        bound_node=parent_bound, child=child_b, child_identifier="kid_b"
    )

    collected = []
    fbrk.EdgeComposition.visit_children_edges(
        bound_node=parent_bound,
        ctx=collected,
        f=lambda ctx, bound_edge: ctx.append(
            fbrk.EdgeComposition.get_name(edge=bound_edge.edge())
        ),
    )

    assert collected == ["kid_a", "kid_b"]

    parent_edge_a = fbrk.EdgeComposition.get_parent_edge(bound_node=child_a_bound)
    assert parent_edge_a is not None
    assert parent_edge_a.edge().is_same(other=edge_a.edge())

    parent_edge_b = fbrk.EdgeComposition.get_parent_edge(bound_node=child_b_bound)
    assert parent_edge_b is not None
    assert parent_edge_b.edge().is_same(other=edge_b.edge())

    assert fbrk.EdgeComposition.get_parent_edge(bound_node=parent_bound) is None


def test_edge_type_create():
    type_node = graph.Node.create()
    instance_node = graph.Node.create()
    edge = fbrk.EdgeType.create(type_node=type_node, instance_node=instance_node)

    assert fbrk.EdgeType.is_instance(edge=edge) is True
    assert type_node.is_same(other=fbrk.EdgeType.get_type_node(edge=edge))

    get_instance_node = fbrk.EdgeType.get_instance_node(edge=edge)
    assert isinstance(get_instance_node, graph.Node)
    assert instance_node.is_same(other=get_instance_node)


def test_edge_next():
    g = graph.GraphView.create()

    previous_node = graph.Node.create()
    next_node = graph.Node.create()
    previous_bound = g.insert_node(node=previous_node)
    _ = g.insert_node(node=next_node)
    edge = fbrk.EdgeNext.create(previous_node=previous_node, next_node=next_node)
    _ = g.insert_edge(edge=edge)
    assert fbrk.EdgeNext.is_instance(edge=edge) is True
    get_next_node = fbrk.EdgeNext.get_next_node_from_node(node=previous_bound)
    assert isinstance(get_next_node, graph.Node)
    assert next_node.is_same(other=get_next_node)


def test_typegraph_instantiate():
    g = graph.GraphView.create()
    type_graph = fbrk.TypeGraph.create(g=g)

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
        edge_type=fbrk.EdgePointer.get_tid(),
        edge_directional=True,
        edge_name="test",
        edge_attributes={"test_key": "test_value"},
    )

    resistor_instance = type_graph.instantiate(type_identifier="Resistor")

    collected = []
    fbrk.EdgeComposition.visit_children_edges(
        bound_node=resistor_instance,
        ctx=collected,
        f=lambda ctx, bound_edge: ctx.append(
            fbrk.EdgeComposition.get_name(edge=bound_edge.edge())
        ),
    )

    assert collected == ["p1", "p2"]

    rp1 = fbrk.EdgeComposition.get_child_by_identifier(
        bound_node=resistor_instance, child_identifier="p1"
    )
    rp2 = fbrk.EdgeComposition.get_child_by_identifier(
        bound_node=resistor_instance, child_identifier="p2"
    )
    assert rp1 is not None
    assert rp2 is not None
    collect = list[graph.BoundEdge]()
    rp1.visit_edges_of_type(
        edge_type=fbrk.EdgePointer.get_tid(),
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
    test_node_count()
    test_edge_composition_create()
    test_edge_composition_add_child_and_visit()
    test_edge_type_create()
    test_edge_next()
    test_typegraph_instantiate()

    print("-" * 80)
    print("All tests passed")
