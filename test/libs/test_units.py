import pytest

from faebryk.libs.units import (
    P,
    Unit,
    UnitCompatibilityError,
    assert_compatible_units,
)


class DummyHasUnit:
    def __init__(self, units: Unit):
        self.units = units


def test_assert_compatible_units_empty_list():
    """Test that empty list raises ValueError"""
    with pytest.raises(ValueError):
        assert_compatible_units([])


def test_assert_compatible_units_single_item():
    """Test that single item list returns its unit"""
    item = DummyHasUnit(P.meter)
    result = assert_compatible_units([item])
    assert result == P.meter


def test_assert_compatible_units_compatible():
    """Test that compatible units pass validation and return first unit"""
    items = [
        DummyHasUnit(P.meter),
        DummyHasUnit(P.kilometer),
        DummyHasUnit(P.centimeter),
    ]
    result = assert_compatible_units(items)
    assert result == P.meter


def test_assert_compatible_units_incompatible():
    """Test that incompatible units raise UnitCompatibilityError"""
    items = [
        DummyHasUnit(P.meter),
        DummyHasUnit(P.second),
    ]
    with pytest.raises(UnitCompatibilityError) as exc_info:
        assert_compatible_units(items)

    assert len(exc_info.value.incompatible_items) == 2


def test_assert_compatible_units_with_derived():
    """Test that derived units are handled correctly and return first unit"""
    items = [
        DummyHasUnit(P.meter / P.second),
        DummyHasUnit(P.kilometer / P.hour),
    ]
    result = assert_compatible_units(items)
    assert result == P.meter / P.second


def test_assert_compatible_units_with_incompatible_derived():
    """Test that incompatible derived units raise UnitCompatibilityError"""
    items = [
        DummyHasUnit(P.meter / P.second),
        DummyHasUnit(P.meter * P.second),
    ]
    with pytest.raises(UnitCompatibilityError):
        assert_compatible_units(items)
