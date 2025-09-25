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
    e12 = Edge.create(n1, n2, 0)
    e13 = Edge.create(n1, n3, 0)

    bn1 = g.insert_node(n1)
    g.insert_node(n2)
    g.insert_node(n3)
    g.insert_edge(e12)
    g.insert_edge(e13)

    # print(repr(g))

    class Ctx:
        def __init__(self):
            self.edges = []

    ctx = Ctx()

    bn1.visit_edges_of_type(
        edge_type=0,
        T=Ctx,
        ctx=ctx,
        f=lambda ctx, edge: ctx.edges.append(edge.edge()),
    )

    assert len(ctx.edges) == 2

    for edge in ctx.edges:
        print(edge)


if __name__ == "__main__":
    test_minimal_graph()
