from unittest.mock import MagicMock

import pytest

from atopile.model2.flat_datamodel import (
    Instance,
    dfs,
    dfs_with_ref,
    find_all_with_super,
)


@pytest.fixture
def instance_structure():
    f = Instance(addr=("f",))
    e = Instance(addr=("e",))

    d = Instance(addr=("d",), children_from_mods={"e": e, "f": f})
    c = Instance(addr=("c",))
    b = Instance(addr=("b",), children_from_mods={"c": c, "d": d})
    a = Instance(addr=("a",), children_from_mods={"b": b})

    return a, b, c, d, e, f


def test_dfs(instance_structure: tuple[Instance]):
    a, b, c, d, e, f = instance_structure

    assert list(dfs(a)) == [a, b, c, d, e, f]


def test_dfs_with_ref(instance_structure: tuple[Instance]):
    a, b, c, d, e, f = instance_structure
    assert list(dfs_with_ref(a)) == [
        ((), a),
        (("b",), b),
        (("b", "c"), c),
        (("b", "d"), d),
        (("b", "d", "e"), e),
        (("b", "d", "f"), f),
    ]


def test_find_all_instances_of_types(instance_structure: tuple[Instance]):
    a, b, c, d, e, f = instance_structure

    A = 1
    B = 2
    C = 3

    origin_a = MagicMock()
    origin_a.supers_bfs = [A, B]

    origin_b = MagicMock()
    origin_b.supers_bfs = [B, C]

    f.origin=origin_b
    e.origin=origin_b
    d.origin=origin_b
    c.origin=origin_a
    b.origin=origin_a
    a.origin=origin_a

    assert list(find_all_with_super(a, (A,))) == [a, b, c]
    assert list(find_all_with_super(a, (A,C))) == [a, b, c, d, e, f]
    assert list(find_all_with_super(a, (B,))) == [a, b, c, d, e, f]
    assert list(find_all_with_super(a, (C,))) == [d, e, f]
