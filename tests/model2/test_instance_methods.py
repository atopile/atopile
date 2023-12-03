from unittest.mock import MagicMock

import pytest

from atopile.model2.instance_methods import (
    Instance,
    dfs,
    dfs_with_ref,
    iter_nets,
    find_like_instances,
    any_supers_match,
    match_components,
    iter_parents,
    lowest_common_parent,
)

from atopile.model2.datamodel import Object, COMPONENT, MODULE, PIN, SIGNAL
from atopile.model2.datatypes import KeyOptMap


@pytest.fixture
def instance_structure():
    f = Instance(ref=("f",))
    e = Instance(ref=("e",))

    d = Instance(ref=("d",), children_from_mods={"e": e, "f": f})
    c = Instance(ref=("c",))
    b = Instance(ref=("b",), children_from_mods={"c": c, "d": d})
    a = Instance(ref=("a",), children_from_mods={"b": b})

    b.parent = a
    c.parent = b
    d.parent = b
    e.parent = d
    f.parent = d

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


def test_any_supers_match(instance_structure: tuple[Instance]):
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

    assert all(any_supers_match(A, )(i) for i in  [a, b, c])
    assert all(any_supers_match(A,C)(i) for i in  [a, b, c, d, e, f])
    assert all(any_supers_match(B, )(i) for i in  [a, b, c, d, e, f])
    assert all(any_supers_match(C, )(i) for i in  [d, e, f])

@pytest.fixture
def unique_structure():
    def _make_obj() -> Object:
        return Object(supers_refs=(), locals_=KeyOptMap(()))

    foo = _make_obj()

    c_obj = _make_obj()
    c_obj.all_supers=(COMPONENT,)
    c_obj.locals_ = ((("foo",), foo),)

    m_obj = _make_obj()
    m_obj.all_supers=(MODULE,)
    m_obj.locals_ = ((("foo",), foo),)

    b = Instance(ref=("b",), origin=c_obj, children_from_mods={"value":"1"})
    c = Instance(ref=("c",), origin=c_obj, children_from_mods={"value":"1"})
    g = Instance(ref=("g",), origin=c_obj, children_from_mods={"value":"2"})
    d = Instance(ref=("d",), origin=m_obj)
    e = Instance(ref=("e",), origin=c_obj, children_from_mods={"b": b, "c": c, "d": d, "value":"1"})

    a = Instance(ref=("a",), origin=m_obj, children_from_mods={"g": g, "e": e})

    return a, b, c, d, e, g

def test_extract_unique(unique_structure: tuple[Instance]):
    a, b, c, d, e, g = unique_structure

    to_test = list(filter(match_components, dfs(a)))
    ret = find_like_instances(to_test, ("value",))

    assert ret == {
        ('1',): [e,b,c],
        ('2',): [g]
    }

@pytest.fixture
def typed_structure(instance_structure):
    a, b, c, d, e, f = instance_structure

    signal_origin = MagicMock(supers_bfs=(SIGNAL,))
    pin_origin = MagicMock(supers_bfs=(PIN,))
    empty_origin = MagicMock(supers_bfs=())

    a.origin = empty_origin
    b.origin = empty_origin
    c.origin = pin_origin
    d.origin = empty_origin
    e.origin = signal_origin
    f.origin = signal_origin

    return a, b, c, d, e, f

def test_iter_nets_no_joints(typed_structure: tuple[Instance]):
    a, b, c, d, e, f = typed_structure

    for net in iter_nets(a):
        assert len(list(net)) == 1

def test_joints(typed_structure: tuple[Instance]):
    a, b, c, d, e, f = typed_structure

    joint = MagicMock(source=c, target=f)
    c.joined_to_me = [joint]
    f.joined_to_me = [joint]

    results = list(list(net) for net in iter_nets(a))

    assert len(results[0]) == 2
    assert results[0][0] == c
    assert results[0][1] == f

    assert len(results[1]) == 1
    assert results[1][0] == e


def test_iter_parents(instance_structure: tuple[Instance]):
    a, b, c, d, e, f = instance_structure

    assert list(iter_parents(a, include_self=False)) == []
    assert list(iter_parents(b, include_self=False)) == [a]
    assert list(iter_parents(c, include_self=False)) == [b, a]
    assert list(iter_parents(d, include_self=False)) == [b, a]
    assert list(iter_parents(e, include_self=False)) == [d, b, a]
    assert list(iter_parents(f, include_self=False)) == [d, b, a]


def test_lowest_common_parent(instance_structure: tuple[Instance]):
    a, b, c, d, e, f = instance_structure

    assert lowest_common_parent([a, b, c, d, e, f]) == a
    assert lowest_common_parent([b, c, d, e, f]) == b
    assert lowest_common_parent([c, e, f]) == b
    assert lowest_common_parent([e, f]) == d
