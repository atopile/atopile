import pytest

from atopile import assertions


def test_DotDict():
    d = assertions.DotDict({"a": 1, "b": 2})
    assert d.a == 1
    assert d.b == 2

    with pytest.raises(AttributeError):
        d.c
