from atopile.model2.datatypes import Ref, KeyOptMap, KeyOptItem

def test_ref_from_one():
    assert Ref.from_one("foo") == ("foo",)
    assert Ref.from_one(42) == (42,)

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
    assert KeyOptMap((
        KeyOptItem((None, "foo")),
        KeyOptItem((Ref.from_one("bar"), "baz")),
    )).get_named_items() == {
        ("bar",): "baz",
    }

def test_keyoptmap_get_items_by_type():
    items_by_type = KeyOptMap((
        KeyOptItem((None, "foo")),
        KeyOptItem((Ref.from_one("bar"), "baz")),
        KeyOptItem((None, 42)),
    )).get_items_by_type((str,))

    assert tuple(items_by_type[str]) == ((None, "foo"), (Ref.from_one("bar"), "baz"))

def test_keyoptmap_get_unnamed_items():
    assert tuple(KeyOptMap((
        KeyOptItem((None, "foo")),
        KeyOptItem((Ref.from_one("bar"), "baz")),
        KeyOptItem((None, 42)),
    )).get_unnamed_items()) == ("foo", 42)

def test_keyoptmap_keys():
    assert tuple(KeyOptMap((
        KeyOptItem((None, "foo")),
        KeyOptItem((Ref.from_one("bar"), "baz")),
        KeyOptItem((None, 42)),
    )).keys()) == (("bar",),)

def test_keyoptmap_values():
    assert tuple(KeyOptMap((
        KeyOptItem((None, "foo")),
        KeyOptItem((Ref.from_one("bar"), "baz")),
        KeyOptItem((None, 42)),
    )).values()) == ("foo", "baz", 42)
