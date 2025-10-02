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


def test_edge_composition_create():
    from faebryk.core.zig.gen.faebryk.composition import EdgeComposition  # type: ignore
    from faebryk.core.zig.gen.graph.graph import Node  # type: ignore

    parent = Node.create()
    child = Node.create()

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
        Node,
    )

    graph = GraphView.create()
    parent = Node.create()
    child_a = Node.create()
    child_b = Node.create()

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
    from faebryk.core.zig.gen.graph.graph import Node  # type: ignore

    type_node = Node.create()
    instance_node = Node.create()
    edge = EdgeType.create(type_node=type_node, instance_node=instance_node)

    assert EdgeType.is_instance(edge=edge) is True
    assert type_node.is_same(other=EdgeType.get_type_node(edge=edge))

    get_instance_node = EdgeType.get_instance_node(edge=edge)
    assert isinstance(get_instance_node, Node)
    assert instance_node.is_same(other=get_instance_node)


def test_edge_next():
    from faebryk.core.zig.gen.faebryk.next import EdgeNext  # type: ignore
    from faebryk.core.zig.gen.graph.graph import GraphView, Node  # type: ignore

    graph = GraphView.create()

    previous_node = Node.create()
    next_node = Node.create()
    previous_bound = graph.insert_node(node=previous_node)
    _ = graph.insert_node(node=next_node)
    edge = EdgeNext.create(previous_node=previous_node, next_node=next_node)
    _ = graph.insert_edge(edge=edge)
    assert EdgeNext.is_instance(edge=edge) is True
    get_next_node = EdgeNext.get_next_node_from_node(node=previous_bound)
    assert isinstance(get_next_node, Node)
    assert next_node.is_same(other=get_next_node)


if __name__ == "__main__":
    test_minimal_graph()
    test_edge_composition_create()
    test_edge_composition_add_child_and_visit()
    test_edge_type_create()
    test_edge_next()

    print("-" * 80)
    print("All tests passed")
