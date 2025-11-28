import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F


class DummyHasUnit:
    def __init__(self, unit):
        self._unit = unit

    def get_unit(self):
        return self._unit


def test_assert_compatible_units_empty_list():
    """Test that empty list raises ValueError"""
    with pytest.raises(ValueError):
        F.Units.IsUnit.assert_compatible_units([])


def test_assert_compatible_units_single_item():
    """Test that single item list returns its unit"""
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    item = F.Units.Meter.bind_typegraph(tg)
    result = F.Units.IsUnit.assert_compatible_units([item])
    assert result == F.Units.Meter

    item = F.Units.Meter
    result = F.Units.IsUnit.assert_compatible_units([item])
    assert result == F.Units.Meter

def test_assert_compatible_units_incompatible():
    """Test that incompatible units raise UnitCompatibilityError"""
    items = [
        F.Units.Meter,
        F.Units.Second
    ]
    with pytest.raises(F.Units.UnitCompatibilityError) as exc_info:
        F.Units.IsUnit.assert_compatible_units(items)

    assert len(exc_info.value.incompatible_items) == 2


def test_assert_compatible_units_with_derived():
    """Test that derived units are handled correctly and return first unit"""
    items = [
        F.Units.VoltsPerSecond,
        F.Units.VoltsPerSecond,
    ]
    result = F.Units.IsUnit.assert_compatible_units(items)
    assert result == F.Units.VoltsPerSecond


def test_assert_compatible_units_with_incompatible_derived():
    """Test that incompatible derived units raise UnitCompatibilityError"""
    items = [
        F.Units.VoltsPerSecond,
        F.Units.Volt,
    ]
    with pytest.raises(F.Units.UnitCompatibilityError):
        F.Units.IsUnit.assert_compatible_units(items)
