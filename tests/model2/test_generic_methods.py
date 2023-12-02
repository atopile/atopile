import pytest
from atopile.model2.generic_methods import dfs, bfs


class Node:
    def __init__(self, name, children):
        self.name = name
        self.children = children


@pytest.fixture
def tree():
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

    return a, b, c, d, e, f, g, h


def test_bfs(tree: tuple[Node]):
    a, b, c, d, e, f, g, h = tree
    assert list(bfs(lambda n: n.children, a)) == [a, b, c, d, e, f, g, h]


def test_dfs(tree: tuple[Node]):
    a, b, c, d, e, f, g, h = tree
    assert list(dfs(lambda n: n.children, a)) == [a, b, e, f, c, g, h, d]