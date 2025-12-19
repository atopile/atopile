import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll


def test_copy_into_matches_old():
    g, tg = fabll._make_graph_and_typegraph()
    g_old = graph.GraphView.create()
    g_new = graph.GraphView.create()

    class Leaf(fabll.Node):
        pass

    class N(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        leaf = Leaf.MakeChild()

    class Root(fabll.Node):
        a = N.MakeChild()
        b = N.MakeChild()

    root = Root.bind_typegraph(tg).create_instance(g=g)
    a = root.a.get()
    b = root.b.get()
    a.connect(to=b, edge_attrs=fbrk.EdgePointer.build(identifier="peer", order=1))

    def _node_uuids(g: graph.GraphView) -> set[int]:
        self_uuid = g.get_self_node().node().get_uuid()
        return {
            n.node().get_uuid()
            for n in g.get_nodes()
            if n.node().get_uuid() != self_uuid
        }

    type_subgraph = tg.get_type_subgraph()
    g_old.insert_subgraph(subgraph=type_subgraph)
    g_new.insert_subgraph(subgraph=type_subgraph)
    type_subgraph.destroy()

    baseline_old = _node_uuids(g_old)
    baseline_new = _node_uuids(g_new)
    assert baseline_old == baseline_new
    baseline_nodes = baseline_old

    g_sub = fbrk.TypeGraph.get_subgraph_of_node(start_node=a.instance)
    sub_self_uuid = g_sub.get_self_node().node().get_uuid()
    subgraph_nodes = {
        n.node().get_uuid()
        for n in g_sub.get_nodes()
        if n.node().get_uuid() != sub_self_uuid
    }
    expected_delta = subgraph_nodes - baseline_nodes
    g_old.insert_subgraph(subgraph=g_sub)
    g_sub.destroy()
    fbrk.TypeGraph.copy_node_into(start_node=a.instance, target_graph=g_new)

    def _edge_signature(
        edge: graph.Edge,
    ) -> tuple[int, int, int, bool | None, str | None, fabll.Literal | None]:
        return (
            edge.edge_type(),
            edge.source().get_uuid(),
            edge.target().get_uuid(),
            edge.directional(),
            edge.name(),
            edge.get_attr(key="order"),
        )

    edge_types = [
        fbrk.EdgeType.get_tid(),
        fbrk.EdgeComposition.get_tid(),
        fbrk.EdgePointer.get_tid(),
        fbrk.EdgeTrait.get_tid(),
        fbrk.EdgeOperand.get_tid(),
        fbrk.EdgeNext.build().get_tid(),
    ]

    def _collect_edges(
        g: graph.GraphView,
        allowed_nodes: set[int],
    ) -> set[tuple[int, int, int, bool | None, str | None, fabll.Literal | None]]:
        edges: set[
            tuple[int, int, int, bool | None, str | None, fabll.Literal | None]
        ] = set()

        def _collect(
            edge_set: set[
                tuple[int, int, int, bool | None, str | None, fabll.Literal | None]
            ],
            bound_edge: graph.BoundEdge,
        ) -> None:
            edge = bound_edge.edge()
            src = edge.source().get_uuid()
            dst = edge.target().get_uuid()
            if src in allowed_nodes and dst in allowed_nodes:
                edge_set.add(_edge_signature(edge))

        for bound_node in g.get_nodes():
            for tid in edge_types:
                bound_node.visit_edges_of_type(edge_type=tid, ctx=edges, f=_collect)

        return edges

    old_nodes = _node_uuids(g_old)
    new_nodes = _node_uuids(g_new)
    old_delta = old_nodes - baseline_nodes
    new_delta = new_nodes - baseline_nodes
    assert expected_delta.issubset(old_delta)
    assert expected_delta.issubset(new_delta)
    assert len(old_delta - expected_delta) == 1
    assert len(new_delta - expected_delta) == 1
    compare_nodes = baseline_nodes | expected_delta
    assert _collect_edges(g_old, compare_nodes) == _collect_edges(g_new, compare_nodes)
