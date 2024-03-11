from atopile import instance_methods
from unittest.mock import MagicMock


def test_common_children():
    a = MagicMock()
    a.children = {
        "a": MagicMock(children={"a": MagicMock(children={})}),
        "b": MagicMock(children={}),
        "c": MagicMock(children={}),
    }

    children = list(instance_methods._common_children(a, a))
    r_aa, r_a, r_b, r_c = children

    assert r_a == (a.children["a"], a.children["a"])
    assert r_aa == (a.children["a"].children["a"], a.children["a"].children["a"])
    assert r_b == (a.children["b"], a.children["b"])
    assert r_c == (a.children["c"], a.children["c"])

    b = MagicMock(children={"a": MagicMock(children={})})
    assert list(instance_methods._common_children(a, b)) == [(a.children["a"], b.children["a"])]
