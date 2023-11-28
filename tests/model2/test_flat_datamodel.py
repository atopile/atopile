from unittest.mock import MagicMock

from atopile.model2.flat_datamodel import Instance, dfs, find_all_with_super


def test_dfs():
    f = Instance(addr=("f",))
    e = Instance(addr=("e",))

    d = Instance(addr=("d",), children_from_mods={"e": e, "f": f})
    c = Instance(addr=("c",))
    b = Instance(addr=("b",), children_from_mods={"c": c, "d": d})
    a = Instance(addr=("a",), children_from_mods={"b": b})

    assert list(dfs(a)) == [a, b, c, d, e, f]


def test_find_all_instances_of_types():
    A = 1
    B = 2
    C = 3

    origin_a = MagicMock()
    origin_a.supers_bfs = [A, B]

    origin_b = MagicMock()
    origin_b.supers_bfs = [B, C]

    f = Instance(addr=("f",), origin=origin_b)
    e = Instance(addr=("e",), origin=origin_b)

    d = Instance(addr=("d",), children_from_mods={"e": e, "f": f}, origin=origin_b)
    c = Instance(addr=("c",), origin=origin_a)
    b = Instance(addr=("b",), children_from_mods={"c": c, "d": d}, origin=origin_a)
    a = Instance(addr=("a",), children_from_mods={"b": b}, origin=origin_a)

    assert list(find_all_with_super(a, (A,))) == [a, b, c]
    assert list(find_all_with_super(a, (A,C))) == [a, b, c, d, e, f]
    assert list(find_all_with_super(a, (B,))) == [a, b, c, d, e, f]
    assert list(find_all_with_super(a, (C,))) == [d, e, f]


