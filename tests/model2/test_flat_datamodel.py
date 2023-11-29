from unittest.mock import MagicMock

from collections import defaultdict

import pytest

from atopile.model2.flat_datamodel import (
    Instance,
    dfs,
    dfs_with_ref,
    filter_by_supers,
    find_like
)

from atopile.model2.datamodel import Object, COMPONENT, MODULE
from atopile.address import AddrStr
from atopile.model2.datatypes import KeyOptMap


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


def test_filter_by_supers(instance_structure: tuple[Instance]):
    a, b, c, d, e, f = instance_structure

    A = 1
    B = 2
    C = 3

    origin_a = MagicMock()
    origin_a.supers_bfs = [A, B]

    origin_b = MagicMock()
    origin_b.supers_bfs = [B, C]

    f.origin = origin_b
    e.origin = origin_b
    d.origin = origin_b
    c.origin = origin_a
    b.origin = origin_a
    a.origin = origin_a

    assert list(filter_by_supers(instance_structure, (A,))) == [a, b, c]
    assert list(filter_by_supers(instance_structure, (A,C))) == [a, b, c, d, e, f]
    assert list(filter_by_supers(instance_structure, (B,))) == [a, b, c, d, e, f]
    assert list(filter_by_supers(instance_structure, (C,))) == [d, e, f]

@pytest.fixture
def unique_structure():
    def _make_obj() -> Object:
        return Object(supers_refs=(), locals_=KeyOptMap(()))

    foo = _make_obj()

    c_obj = _make_obj()
    c_obj.supers_bfs=(COMPONENT,)
    c_obj.locals_ = ((("foo",), foo),)

    m_obj = _make_obj()
    m_obj.supers_bfs=(MODULE,)
    m_obj.locals_ = ((("foo",), foo),)

    b = Instance(addr=("b",), origin=c_obj, children_from_mods={"value":"1"})
    c = Instance(addr=("c",), origin=c_obj, children_from_mods={"value":"1"})
    g = Instance(addr=("g",), origin=c_obj, children_from_mods={"value":"2"})
    d = Instance(addr=("d",), origin=m_obj)
    e = Instance(addr=("e",), origin=c_obj, children_from_mods={"b": b, "c": c, "d": d, "value":"1"})

    a = Instance(addr=("a",), origin=m_obj, children_from_mods={"g": g, "e": e})

    return a, b, c, d, e, g

def test_extract_unique(unique_structure: tuple[Instance]):
    a, b, c, d, e, g = unique_structure

    test = filter_by_supers(dfs(a), COMPONENT)
    ret = find_like(test,("value",))

    expected_ret = defaultdict(list)
    expected_ret[('1',)] = [e,b,c]
    expected_ret[('2',)] = [g]

    assert ret == expected_ret
