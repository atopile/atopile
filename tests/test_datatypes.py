import pytest

from atopile.datatypes import DotDict, KeyOptItem, KeyOptMap, Ref, StackList, Strainer


def test_ref_from_one():
    assert Ref.from_one("foo") == ("foo",)
    assert Ref.from_one(42) == (42,)


def test_ref_add_name():
    assert Ref.from_one("foo").add_name("bar") == ("foo", "bar")


def test_keyoptitem_from_kv():
    assert KeyOptItem.from_kv(None, "foo") == (None, "foo")


def test_keyoptmap_from_item():
    assert KeyOptMap.from_item(KeyOptItem.from_kv(None, "foo")) == ((None, "foo"),)


def test_keyoptmap_from_kv():
    assert KeyOptMap.from_kv(None, "foo") == ((None, "foo"),)


def test_keyoptitem_ref():
    assert KeyOptItem((None, "foo")).ref is None
    assert KeyOptItem((Ref.from_one("foo"), "bar")).ref == ("foo",)


def test_keyoptmap_get_named_items():
    assert dict(
        KeyOptMap(
            (
                KeyOptItem((None, "foo")),
                KeyOptItem((Ref.from_one("bar"), "baz")),
            )
        ).named_items()
    ) == {
        ("bar",): "baz",
    }


def test_filter_items_by_type():
    strs = KeyOptMap(
        (
            KeyOptItem((None, "foo")),
            KeyOptItem((Ref.from_one("bar"), "baz")),
        )
    )

    ints = KeyOptMap(
        (
            KeyOptItem((None, 42)),
            KeyOptItem(("test", 43)),
        )
    )

    nones = KeyOptMap((KeyOptItem((None, None)),))

    items = KeyOptMap(strs + ints + nones)

    assert tuple(items.filter_items_by_type(int)) == ints
    assert tuple(items.filter_items_by_type(str)) == strs
    assert tuple(items.filter_items_by_type((int, str))) == strs + ints


def test_keyoptmap_get_items_by_type():
    strs = KeyOptMap(
        (
            KeyOptItem((None, "foo")),
            KeyOptItem((Ref.from_one("bar"), "baz")),
        )
    )

    ints = KeyOptMap(
        (
            KeyOptItem((None, 42)),
            KeyOptItem(("test", 43)),
        )
    )

    nones = KeyOptMap((KeyOptItem((None, None)),))

    items = KeyOptMap(strs + ints + nones)

    items_by_type = items.map_items_by_type((int, str))

    assert items_by_type[str] == strs
    assert items_by_type[int] == ints


def test_keyoptmap_get_unnamed_items():
    assert tuple(
        KeyOptMap(
            (
                KeyOptItem((None, "foo")),
                KeyOptItem((Ref.from_one("bar"), "baz")),
                KeyOptItem((None, 42)),
            )
        ).unnamed_items()
    ) == ("foo", 42)


def test_keyoptmap_keys():
    assert tuple(
        KeyOptMap(
            (
                KeyOptItem((None, "foo")),
                KeyOptItem((Ref.from_one("bar"), "baz")),
                KeyOptItem((None, 42)),
            )
        ).keys()
    ) == (("bar",),)


def test_keyoptmap_values():
    assert tuple(
        KeyOptMap(
            (
                KeyOptItem((None, "foo")),
                KeyOptItem((Ref.from_one("bar"), "baz")),
                KeyOptItem((None, 42)),
            )
        ).values()
    ) == ("foo", "baz", 42)


def test_strainer():
    s = Strainer([1, 2, 3, 4, 5])
    assert list(s) == [1, 2, 3, 4, 5]
    assert s.strain(lambda x: x % 2 == 0) == [2, 4]
    assert s == [1, 3, 5]

    for i in s.iter_strain(lambda x: x in (1, 3)):
        assert i in (1, 3)

    assert s == [5]

    if not s:
        raise Exception

    s.pop(0)

    if s:
        raise Exception


def test_stack_list():
    stack = StackList()
    with stack.enter(1):
        assert stack == [1]
        assert stack.top == 1
        with stack.enter(2):
            assert stack == [1, 2]
            assert stack.top == 2
        assert stack == [1]
        assert stack.top == 1


def test_DotDict():
    d = DotDict({"a": 1, "b": 2})
    assert d.a == 1
    assert d.b == 2

    with pytest.raises(AttributeError):
        d.c
