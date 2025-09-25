def test_load_graph_module():
    from faebryk.core.zig.gen.graph.graph import GraphView  # type: ignore  # noqa: F401


def test_minimal_graph():
    from faebryk.core.zig.gen.graph.graph import (  # type: ignore  # noqa: F401
        Edge,
        GraphView,
        Node,
    )

    g = GraphView.create()

    n1 = Node.create()
    n2 = Node.create()
    n3 = Node.create()
    e120 = Edge.create(n1, n2, 0)
    e130 = Edge.create(n1, n3, 0)
    e121 = Edge.create(n1, n2, 1)

    bn1 = g.insert_node(n1)
    g.insert_node(n2)
    g.insert_node(n3)
    g.insert_edge(e120)
    g.insert_edge(e130)
    g.insert_edge(e121)

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


if __name__ == "__main__":
    test_minimal_graph()
