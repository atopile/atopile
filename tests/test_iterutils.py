from atopile.iterutils import bfs, ordered_unique


def test_bfs():
    class Node:
        def __init__(self, name, children):
            self.name = name
            self.children = children

    a = Node("a", [])
    b = Node("b", [])
    c = Node("c", [])
    d = Node("d", [])
    e = Node("e", [])
    f = Node("f", [])
    g = Node("g", [])
    h = Node("h", [])

    a.children = [b, c, d]
    b.children = [e, f]
    c.children = [g, h]

    assert list(bfs(a, lambda n: n.children)) == [a, b, c, d, e, f, g, h]


def test_ordered_unique_empty():
    assert ordered_unique(()) == (set(), [])


def test_ordered_unique():
    assert ordered_unique((1,2,2,3,4,4,5)) == (
        {1,2,3,4,5},
        [1,2,3,4,5]
    )
