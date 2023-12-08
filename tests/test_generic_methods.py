import pytest
from atopile.generic_methods import dfs_postorder, bfs


class Node:
    def __init__(self, name, children):
        self.name = name
        self.children = children


@pytest.fixture
def tree():
    """
    a
    |- b
    |  |- e
    |  |- f
    |
    |- c
    |  |- g
    |  |- h
    |
    |- d
    """
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


def test_dfs_postorder(tree: tuple[Node]):
    a, b, c, d, e, f, g, h = tree
    assert list(dfs_postorder(lambda n: n.children, a)) == [e, f, b, g, h, c, d, a]
