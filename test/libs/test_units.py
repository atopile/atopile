from collections.abc import Sequence

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
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


@pytest.fixture
def ctx() -> BoundUnitsContext:
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return BoundUnitsContext(tg=tg, g=g)


def assert_commensurability(items: Sequence[F.Units.is_unit]) -> F.Units.is_unit:
    if not items:
        raise ValueError("At least one item is required")

    (first_unit, *other_units) = items

    for other_unit in other_units:
        if not first_unit.is_commensurable_with(other_unit):
            symbols = [unit._extract_symbol() for unit in items]
            raise F.Units.UnitsNotCommensurable(
                "Operands have incommensurable units:\n"
                + "\n".join(
                    f"`{item.__repr__()}` ({symbols[i]})"
                    for i, item in enumerate(items)
                ),
                incommensurable_items=items,
            )

    return first_unit


def test_assert_commensurability_empty_list():
    """Test that empty list raises ValueError"""
    with pytest.raises(ValueError):
        assert_commensurability([])


def test_assert_commmensurability_single_item(ctx: BoundUnitsContext):
    """Test that single item list returns its unit"""
    result = assert_commensurability([ctx.Meter.get_trait(F.Units.is_unit)])
    assert result == ctx.Meter.get_trait(F.Units.is_unit)
    parent, _ = result.get_parent_force()
    assert parent.isinstance(F.Units.Meter)
    assert not_none(
        F.Units.is_unit.bind_instance(result.instance)._extract_symbol()
    ) == ["m"]


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


def test_assert_commensurable_units_with_derived(ctx: BoundUnitsContext):
    """Test that derived units are handled correctly"""

    MetersPerSecondExpr = F.Units.make_unit_expression_type(
        [(F.Units.Meter, 1), (F.Units.Second, -1)]
    )
    KilometerExpr = F.Units.make_unit_expression_type(
        [(F.Units.Meter, 1)], multiplier=1000
    )
    KilometersPerHourExpr = F.Units.make_unit_expression_type(
        [(KilometerExpr, 1), (F.Units.Hour, -1)]
    )

    class App(fabll.Node):
        meters_per_second_expr = MetersPerSecondExpr.MakeChild()
        kilometers_per_hour_expr = KilometersPerHourExpr.MakeChild()

    app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
    meters_per_second = F.Units.resolve_unit_expression(
        tg=ctx.tg, g=ctx.g, expr=app.meters_per_second_expr.get().instance
    )
    kilometers_per_hour = F.Units.resolve_unit_expression(
        tg=ctx.tg, g=ctx.g, expr=app.kilometers_per_hour_expr.get().instance
    )

    assert_commensurability(
        [
            meters_per_second.get_trait(F.Units.is_unit),
            kilometers_per_hour.get_trait(F.Units.is_unit),
        ]
    )


def test_assert_commensurability_with_incommensurable_derived(ctx: BoundUnitsContext):
    """Test that incommensurable derived units raise UnitsNotCommensurable"""
    MetersPerSecondExpr = F.Units.make_unit_expression_type(
        [(F.Units.Meter, 1), (F.Units.Second, -1)]
    )

    MeterSecondsExpr = F.Units.make_unit_expression_type(
        [(F.Units.Meter, 1), (F.Units.Second, 1)]
    )

    class App(fabll.Node):
        meters_per_second_expr = MetersPerSecondExpr.MakeChild()
        meter_seconds_expr = MeterSecondsExpr.MakeChild()

    app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
    meters_per_second = F.Units.resolve_unit_expression(
        tg=ctx.tg, g=ctx.g, expr=app.meters_per_second_expr.get().instance
    )
    meter_seconds = F.Units.resolve_unit_expression(
        tg=ctx.tg, g=ctx.g, expr=app.meter_seconds_expr.get().instance
    )
    with pytest.raises(F.Units.UnitsNotCommensurable):
        assert_commensurability(
            [
                meters_per_second.get_trait(F.Units.is_unit),
                meter_seconds.get_trait(F.Units.is_unit),
            ]
        )


def test_isunit_setup(ctx):
    is_unit = F.Units.is_unit.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)
    is_unit.setup(
        g=ctx.g,
        tg=ctx.tg,
        symbols=["m"],
        unit_vector=F.Units.BasisVector(meter=1),
        multiplier=1.0,
        offset=0.0,
    )
    assert not_none(is_unit._extract_symbol()) == ["m"]

    assert F.Units._BasisVector.bind_instance(
        is_unit.basis_vector.get().deref().instance
    ).extract_vector() == F.Units.BasisVector(meter=1)

    assert is_unit._extract_multiplier() == 1.0
    assert is_unit._extract_offset() == 0.0


# TODO: more tests
# - mutually incompatible: dimensionless, radian, steradian
# - mutually compatible: dimensionless, ppm, percent
# - expressions with affine units
