from faebryk.libs.util import FuncDict, FuncSet


def test_func_dict_contains():
    a = FuncDict([(1, 2), (FuncDict, 4), (FuncSet, 5)])
    assert 1 in a
    assert FuncDict in a
    assert FuncSet in a

    assert a[1] == 2
    assert a[FuncDict] == 4
    assert a[FuncSet] == 5

    assert id not in a

    a[id] = 10
    assert a[id] == 10


def test_func_dict_iter():
    items = [(1, 2), (FuncDict, 4), (FuncSet, 5)]
    a = FuncDict(items)
    assert len(a) == len(items)
    assert all(item[0] in a for item in items)

    for item, aa in zip(items, a):
        assert item[0] == aa

    for (ia, iv), (ak, av) in zip(items, a.items()):
        assert ak == ia
        assert av == iv


def test_func_dict_hash_collision():
    a = FuncDict(hasher=lambda _: 1)
    a[1] = "a"
    a[2] = "b"
    assert len(a) == 2
    assert a[1] == "a"
    assert a[2] == "b"


def test_func_dict_backwards_lookup():
    a = FuncDict()
    a[1] = "a"
    a[2] = "b"
    assert a.backwards_lookup("a") == 1
    assert a.backwards_lookup("b") == 2


def test_func_dict_setdefault():
    a = FuncDict()
    assert 1 not in a
    assert a.setdefault(1, "a") == "a"
    assert a[1] == "a"


def test_func_set_contains():
    a = FuncSet([1, 2, 3, FuncDict, FuncSet])
    assert 1 in a
    assert FuncDict in a
    assert FuncSet in a
    assert 4 not in a


def test_iter_func_set():
    items = [1, 2, 3, FuncDict, FuncSet]
    a = FuncSet(items)
    assert len(a) == len(items)
    assert all(item in a for item in items)

    for item, aa in zip(items, a):
        assert item == aa


def test_func_set_hash_collision():
    a = FuncSet(hasher=lambda _: 1)
    a.add(1)
    a.add(2)
    assert len(a) == 2
    assert 1 in a
    assert 2 in a


def test_func_set_discard():
    a = FuncSet((1, 2), hasher=lambda x: x)
    assert 1 in a
    assert 2 in a
    a.discard(1)
    assert 1 not in a
    assert 2 in a
