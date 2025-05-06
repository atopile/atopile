from atopile.datatypes import KeyOptItem, KeyOptMap, StackList, TypeRef


def test_ref_from_one():
    assert TypeRef.from_one("foo") == ("foo",)
    assert TypeRef.from_one(42) == ("42",)


def test_ref_add_name():
    assert TypeRef.from_one("foo").add_name("bar") == ("foo", "bar")


def test_keyoptitem_from_kv():
    assert KeyOptItem.from_kv(None, "foo") == (None, "foo")


def test_keyoptmap_from_item():
    assert KeyOptMap.from_item(KeyOptItem.from_kv(None, "foo")) == ((None, "foo"),)


def test_keyoptmap_from_kv():
    assert KeyOptMap.from_kv(None, "foo") == ((None, "foo"),)


def test_keyoptitem_ref():
    assert KeyOptItem((None, "foo")).ref is None
    assert KeyOptItem((TypeRef.from_one("foo"), "bar")).ref == ("foo",)


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
