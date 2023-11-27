from atopile.iterutils import bfs, unique_by_id, unique_list


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


def test_unique_list_empty():
    assert unique_list(()) == []


def test_unique_list():
    assert unique_list((1,2,3,3,3,2,1)) == [1,2,3]


def test_unique_by_id_empty():
    assert unique_by_id(()) == (set(), [])


def test_unique_by_id():
    a = 1
    b = 2
    c = 3
    assert unique_by_id((a,b,c,c,c,b,a)) == (
        {id(a), id(b), id(c)},
        [a, b, c]
    )
