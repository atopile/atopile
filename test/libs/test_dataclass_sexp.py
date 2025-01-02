from dataclasses import dataclass

from faebryk.libs.sexp.dataclass_sexp import sort_dataclass_sexp


@dataclass
class SimpleChild:
    numbers: list[int]
    text: str


@dataclass
class SimpleParent:
    children: list[SimpleChild]
    tags: list[str]
    name: str


def test_sort_lists_simple():
    # Create a simple test case
    obj = SimpleParent(
        children=[
            SimpleChild(numbers=[3, 1, 2], text="first"),
            SimpleChild(numbers=[5, 4, 6], text="second"),
        ],
        tags=["c", "a", "b"],
        name="test",
    )

    # Sort all lists in the object
    sort_dataclass_sexp(obj)

    # Check that lists are sorted
    assert obj.tags == ["a", "b", "c"]
    assert obj.children[0].numbers == [1, 2, 3]
    assert obj.children[1].numbers == [4, 5, 6]
    # Check that non-list fields are unchanged
    assert obj.name == "test"
    assert obj.children[0].text == "first"
    assert obj.children[1].text == "second"


def test_sort_lists_empty():
    # Test with empty lists
    obj = SimpleParent(
        children=[
            SimpleChild(numbers=[], text="empty"),
        ],
        tags=[],
        name="test_empty",
    )

    sort_dataclass_sexp(obj)

    # Check that empty lists remain empty
    assert obj.tags == []
    assert obj.children[0].numbers == []
    # Check that non-list fields are unchanged
    assert obj.name == "test_empty"
    assert obj.children[0].text == "empty"
