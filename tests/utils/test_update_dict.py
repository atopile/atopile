import pytest

from atopile.utils import update_dict


def test_update_top_level():
    a = {"a": 1, "b": {"c": 2}}
    update_dict(a, {"a": 3})
    assert a == {"a": 3, "b": {"c": 2}}


def test_update_nested_top_level():
    a = {"a": 1, "b": {"c": 2, "d": 4}}
    update_dict(a, {"b": {"c": 3}})
    assert a == {"a": 1, "b": {"c": 3, "d": 4}}


def test_append_top_level():
    a = {"a": 1, "b": {"c": 2}}
    update_dict(a, {"d": 3})
    assert a == {"a": 1, "b": {"c": 2}, "d": 3}


@pytest.mark.xfail
def test_remove_top_level():
    # TODO: how do we remove things neatly?
    raise NotImplementedError


def test_update_second_level():
    a = {"a": 1, "b": {"c": 2}}
    update_dict(a, {"b": {"c": 3}})
    assert a == {"a": 1, "b": {"c": 3}}


def test_append_second_level():
    a = {"a": 1, "b": {"c": 2}}
    update_dict(a, {"b": {"d": 3}})
    assert a == {"a": 1, "b": {"c": 2, "d": 3}}


def test_update_subdict():
    # TODO: I'm not convinced I like this behaviour
    a = {"a": 1, "b": {"c": 2}}
    update_dict(a, {"b": 3})
    assert a == {"a": 1, "b": 3}
