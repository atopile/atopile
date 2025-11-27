from collections.abc import Sequence

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.util import not_none, once

# TODO: move to test/library/test_units.py? or faebryk/library/Units.py?


class BoundUnitsContext:
    def __init__(self, tg: fbrk.TypeGraph, g: graph.GraphView):
        self.tg = tg
        self.g = g

    @property
    @once
    def Meter(self) -> F.Units.Meter:
        return F.Units.Meter.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Second(self) -> F.Units.Second:
        return F.Units.Second.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Hour(self) -> F.Units.Hour:
        return F.Units.Hour.bind_typegraph(tg=self.tg).create_instance(g=self.g)


def assert_commensurability(items: Sequence[F.Units.IsUnit]) -> F.Units.IsUnit:
    if not items:
        raise ValueError("At least one item is required")

    (first_unit, *other_units) = items

    for other_unit in other_units:
        if not first_unit.is_commensurable_with(other_unit):
            symbols = [unit.symbol.get() for unit in items]
            raise F.Units.UnitsNotCommensurable(
                "Operands have incommensurable units:\n"
                + "\n".join(
                    f"`{item.__repr__()}` ({symbols[i]})"
                    for i, item in enumerate(items)
                ),
                incommensurable_items=items,
            )

    # TODO: consider returning simplest commensurable unit
    return first_unit


@pytest.fixture
def ctx() -> BoundUnitsContext:
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return BoundUnitsContext(tg=tg, g=g)


def test_assert_commensurability_empty_list():
    """Test that empty list raises ValueError"""
    with pytest.raises(ValueError):
        assert_commensurability([])


def test_assert_commmensurability_single_item(ctx: BoundUnitsContext):
    """Test that single item list returns its unit"""
    result = assert_commensurability([ctx.Meter._is_unit.get()])
    assert result == ctx.Meter._is_unit.get()
    parent, _ = result.get_parent_force()
    assert parent.isinstance(F.Units.Meter)

    # FIXME
    # assert (
    #     F.Units.IsUnit.bind_instance(result.instance)
    #     .symbol.get()
    #     .try_extract_constrained_literal()
    #     == "m"
    # )


def test_assert_commensurability(ctx: BoundUnitsContext):
    """Test that commensurable units pass validation and return first unit"""
    result = assert_commensurability(
        [
            ctx.Second._is_unit.get(),
            ctx.Hour._is_unit.get(),
        ]
    )
    parent, _ = result.get_parent_force()
    assert parent.isinstance(F.Units.Second)


def test_assert_incommensurability(ctx: BoundUnitsContext):
    """Test that incompatible units raise UnitsNotCommensurable"""
    with pytest.raises(F.Units.UnitsNotCommensurable):
        assert_commensurability([ctx.Meter._is_unit.get(), ctx.Second._is_unit.get()])


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


def test_isunit_setup(ctx):
    is_unit = F.Units.IsUnit.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
    is_unit.setup(
        symbols=["m"],
        unit_vector=F.Units._BasisVector.ORIGIN,
        multiplier=1.0,
        offset=0.0,
    )
    assert not_none(
        is_unit.symbol.get().try_extract_constrained_literal()
    ).get_values() == ["m"]
    assert (
        F.Units._BasisVector.bind_instance(
            is_unit.basis_vector.get().deref().instance
        ).extract_vector()
        == F.Units._BasisVector.ORIGIN
    )
    # TODO: pending Numbers impl
    # assert is_unit.multiplier.get().force_extract_literal().get_value() == 1.0
    assert is_unit.offset.get().force_extract_literal().get_value() == 0.0
