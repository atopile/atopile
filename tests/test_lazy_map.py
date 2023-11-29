import pytest

from atopile.lazy_map import LazyMap


@pytest.fixture
def lazy_map():
    def double(x):
        return x * 2

    known_keys = [1, 2, 3, 4]

    initial_values = {1: 2, 2: 4}

    return LazyMap(double, known_keys, initial_values)


def test_lazy_map(lazy_map: LazyMap):
    # Test case 1: Test initialization with known keys and initial values
    assert len(lazy_map) == 4

    # from the initial values
    assert lazy_map[1] == 2
    assert lazy_map[2] == 4

    # not already defined in the map
    assert lazy_map[3] == 6
    assert lazy_map[4] == 8


def test_set_item(lazy_map: LazyMap):
    lazy_map[10] = 8
    assert len(lazy_map) == 5
    assert lazy_map[10] == 8


def test_del_item(lazy_map: LazyMap):
    del lazy_map[2]
    assert len(lazy_map) == 3
    assert 2 not in lazy_map


def test_iter(lazy_map: LazyMap):
    keys = list(lazy_map)
    assert keys == [1, 2, 3, 4]


def test_override(lazy_map: LazyMap):
    lazy_map[1] = 10
    assert lazy_map[1] == 10


def test_key_error(lazy_map: LazyMap):
    with pytest.raises(KeyError):
        value = lazy_map[5]
