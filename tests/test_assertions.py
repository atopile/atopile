import pytest

from atopile import assertions


def test_DotDict():
    d = assertions.DotDict({"a": 1, "b": 2})
    assert d.a == 1
    assert d.b == 2

    with pytest.raises(AttributeError):
        d.c


def test_follow_the_dots():
    d = assertions.DotDict({"a": {"b": {"c": 1}}})
    assert assertions._follow_the_dots(d, ["a", "b", "c"]) == 1
