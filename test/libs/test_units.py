from collections.abc import Sequence

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import faebrykpy as fbrk
from faebryk.core import graph
from faebryk.core import node as fabll

# class DummyHasUnit:
#     def __init__(self, units: Unit):
#         self.units = units

# TODO: move to test/library/test_units.py?


class UnitCompatibilityError(Exception):
    def __init__(self, message: str, incompatible_items: Sequence[fabll.NodeT]):
        self.message = message
        self.incompatible_items = incompatible_items

    def __str__(self) -> str:
        return self.message


def assert_compatible_units(items: Sequence[F.Units.IsUnit]) -> F.Units.IsUnit:
    if not items:
        raise ValueError("At least one item is required")

    (first_unit, *other_units) = items

    for other_unit in other_units:
        if not first_unit.is_compatible_with(other_unit):
            symbols = [unit.symbol.get() for unit in items]
            raise UnitCompatibilityError(
                "Operands have incompatible units:\n"
                + "\n".join(
                    f"`{item.__repr__()}` ({symbols[i]})"
                    for i, item in enumerate(items)
                ),
                incompatible_items=items,
            )

    return first_unit


def test_assert_compatible_units_empty_list():
    """Test that empty list raises ValueError"""
    with pytest.raises(ValueError):
        F.Units.IsUnit.assert_compatible_units([])


def test_assert_compatible_units_single_item():
    """Test that single item list returns its unit"""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    meter = F.Units.Meter.bind_typegraph(tg=tg).create_instance(g=g)
    result = assert_compatible_units([meter._is_unit.get()])
    assert result == meter._is_unit.get()

    (parent, _) = result.get_parent_force()
    assert F.Units.Meter.bind_instance(parent.instance).isinstance(F.Units.Meter)

    # FIXME
    # assert (
    #     F.Units.IsUnit.bind_instance(result.instance)
    #     .symbol.get()
    #     .try_extract_constrained_literal()
    #     == "m"
    # )


def test_assert_compatible_units_compatible():
    """Test that compatible units pass validation and return first unit"""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    second = F.Units.Second.bind_typegraph(tg=tg).create_instance(g=g)
    hour = F.Units.Hour.bind_typegraph(tg=tg).create_instance(g=g)
    result = assert_compatible_units([second._is_unit.get(), hour._is_unit.get()])
    assert result.isinstance(F.Units.Second)


# def test_assert_compatible_units_incompatible():
#     """Test that incompatible units raise UnitCompatibilityError"""
#     items = [
#         DummyHasUnit(P.meter),
#         DummyHasUnit(P.second),
#     ]
#     with pytest.raises(UnitCompatibilityError) as exc_info:
#         assert_compatible_units(items)

#     assert len(exc_info.value.incompatible_items) == 2


# def test_assert_compatible_units_with_derived():
#     """Test that derived units are handled correctly and return first unit"""
#     items = [
#         DummyHasUnit(P.meter / P.second),
#         DummyHasUnit(P.kilometer / P.hour),
#     ]
#     result = assert_compatible_units(items)
#     assert result == P.meter / P.second


# def test_assert_compatible_units_with_incompatible_derived():
#     """Test that incompatible derived units raise UnitCompatibilityError"""
#     items = [
#         DummyHasUnit(P.meter / P.second),
#         DummyHasUnit(P.meter * P.second),
#     ]
#     with pytest.raises(UnitCompatibilityError):
#         assert_compatible_units(items)


# TODO: more tests
# - mutually incompatible: dimensionless, radian, steradian
# - mutually compatible: dimensionless, ppm, percent
