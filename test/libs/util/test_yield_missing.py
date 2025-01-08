import pytest

from faebryk.libs.util import yield_missing


def test_basic():
    existing = {1, 2, 3}
    candidates = [1, 2, 3, 4, 5]
    assert list(yield_missing(existing, candidates)) == [4, 5]


def test_no_candidates():
    existing = {0, 1, 3}
    missing = iter(yield_missing(existing))
    assert next(missing) == 2
    assert next(missing) == 4
    assert next(missing) == 5
    assert next(missing) == 6


def test_max_range():
    existing = {1, 2, 3}
    missing = iter(yield_missing(existing, range(7)))
    assert next(missing) == 0
    assert next(missing) == 4
    assert next(missing) == 5
    assert next(missing) == 6
    with pytest.raises(StopIteration):
        next(missing)
