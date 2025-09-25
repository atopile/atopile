def test_load_graph_module():
    # Test import working
    import faebryk.core.zig.gen.graph  # noqa: F401
    from faebryk.core.zig.gen.graph.graph import GraphView

    g = GraphView.create()
    print(repr(g))


if __name__ == "__main__":
    test_load_graph_module()
