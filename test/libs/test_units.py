from collections.abc import Sequence

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.util import not_none, once

# FIXME: move to Units.py


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

    @property
    @once
    def Dimensionless(self) -> F.Units.Dimensionless:
        return F.Units.Dimensionless.bind_typegraph(tg=self.tg).create_instance(
            g=self.g
        )

    @property
    @once
    def Percent(self) -> F.Units.Percent:
        return F.Units.Percent.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Ppm(self) -> F.Units.Ppm:
        return F.Units.Ppm.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Radian(self) -> F.Units.Radian:
        return F.Units.Radian.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Steradian(self) -> F.Units.Steradian:
        return F.Units.Steradian.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def DegreeCelsius(self) -> F.Units.DegreeCelsius:
        return F.Units.DegreeCelsius.bind_typegraph(tg=self.tg).create_instance(
            g=self.g
        )

    @property
    @once
    def Kelvin(self) -> F.Units.Kelvin:
        return F.Units.Kelvin.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Volt(self) -> F.Units.Volt:
        return F.Units.Volt.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Ohm(self) -> F.Units.Ohm:
        return F.Units.Ohm.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Ampere(self) -> F.Units.Ampere:
        return F.Units.Ampere.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    @property
    @once
    def Degree(self) -> F.Units.Degree:
        return F.Units.Degree.bind_typegraph(tg=self.tg).create_instance(g=self.g)


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
            raise F.Units.UnitsNotCommensurableError(
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
    with pytest.raises(F.Units.UnitsNotCommensurableError):
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
    with pytest.raises(F.Units.UnitsNotCommensurableError):
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


def test_decode_symbol(ctx):
    _ = ctx.Meter
    decoded_meter = F.Units.decode_symbol(g=ctx.g, tg=ctx.tg, symbol="m")

    assert decoded_meter._extract_basis_vector() == F.Units.BasisVector(meter=1)
    assert decoded_meter._extract_multiplier() == 1.0
    assert decoded_meter._extract_offset() == 0.0

    kilometer = F.Units.decode_symbol(g=ctx.g, tg=ctx.tg, symbol="km")
    assert kilometer._extract_basis_vector() == F.Units.BasisVector(meter=1)
    assert kilometer._extract_multiplier() == 1000.0
    assert kilometer._extract_offset() == 0.0


def test_decode_symbol_not_found(ctx):
    with pytest.raises(F.Units.UnitNotFoundError):
        F.Units.decode_symbol(g=ctx.g, tg=ctx.tg, symbol="not_found")


def test_decode_symbol_not_a_unit(ctx):
    with pytest.raises(F.Units.UnitNotFoundError):
        F.Units.decode_symbol(g=ctx.g, tg=ctx.tg, symbol="m/s")


def test_decode_symbol_invalid_prefix_for_unit(ctx):
    with pytest.raises(F.Units.UnitNotFoundError):
        F.Units.decode_symbol(g=ctx.g, tg=ctx.tg, symbol="k%")


def test_dimensionless_radian_steradian_incompatible(ctx: BoundUnitsContext):
    """Test that dimensionless, radian, and steradian are mutually incommensurable."""
    dimensionless = ctx.Dimensionless._is_unit.get()
    radian = ctx.Radian._is_unit.get()
    steradian = ctx.Steradian._is_unit.get()

    with pytest.raises(F.Units.UnitsNotCommensurableError):
        assert_commensurability([dimensionless, radian])

    with pytest.raises(F.Units.UnitsNotCommensurableError):
        assert_commensurability([dimensionless, steradian])

    with pytest.raises(F.Units.UnitsNotCommensurableError):
        assert_commensurability([radian, steradian])


def test_dimensionless_percent_ppm_compatible(ctx: BoundUnitsContext):
    """Test that dimensionless, percent, and ppm are mutually commensurable."""
    dimensionless = ctx.Dimensionless._is_unit.get()
    percent = ctx.Percent._is_unit.get()
    ppm = ctx.Ppm._is_unit.get()

    result = assert_commensurability([dimensionless, percent, ppm])
    parent, _ = result.get_parent_force()
    assert parent.isinstance(F.Units.Dimensionless)


def test_affine_unit_in_expression_raises(ctx: BoundUnitsContext):
    """Test that affine units (non-zero offset) raise error in compound expressions."""
    celsius = ctx.DegreeCelsius._is_unit.get()
    assert celsius.is_affine

    CelsiusExpr = F.Units.make_unit_expression_type([(F.Units.DegreeCelsius, 1)])

    class App(fabll.Node):
        celsius_expr = CelsiusExpr.MakeChild()

    app = App.bind_typegraph(tg=ctx.tg).create_instance(g=ctx.g)

    with pytest.raises(F.Units.UnitExpressionError):
        F.Units.resolve_unit_expression(
            tg=ctx.tg, g=ctx.g, expr=app.celsius_expr.get().instance
        )


def test_unit_multiply(ctx: BoundUnitsContext):
    """Test unit multiplication: Volt * Ampere produces Watt-equivalent basis."""
    volt = ctx.Volt._is_unit.get()
    ampere = ctx.Ampere._is_unit.get()

    result = volt.op_multiply(ctx.g, ctx.tg, ampere)
    assert result._extract_basis_vector() == F.Units.BasisVector(
        kilogram=1, meter=2, second=-3
    )


def test_unit_divide(ctx: BoundUnitsContext):
    """Test unit division: Volt / Ampere produces Ohm-equivalent basis."""
    volt = ctx.Volt._is_unit.get()
    ampere = ctx.Ampere._is_unit.get()

    result = volt.op_divide(ctx.g, ctx.tg, ampere)
    assert result._extract_basis_vector() == F.Units.Ohm.unit_vector_arg


def test_unit_power(ctx: BoundUnitsContext):
    """Test unit exponentiation."""
    meter = ctx.Meter._is_unit.get()

    squared = meter.op_power(ctx.g, ctx.tg, 2)
    assert squared._extract_basis_vector() == F.Units.BasisVector(meter=2)

    cubed = meter.op_power(ctx.g, ctx.tg, 3)
    assert cubed._extract_basis_vector() == F.Units.BasisVector(meter=3)

    inverse = meter.op_power(ctx.g, ctx.tg, -1)
    assert inverse._extract_basis_vector() == F.Units.BasisVector(meter=-1)


def test_unit_invert(ctx: BoundUnitsContext):
    """Test unit inversion: 1/Second has the same basis as Hertz."""
    second = ctx.Second._is_unit.get()

    result = second.op_invert(ctx.g, ctx.tg)
    assert result._extract_basis_vector() == F.Units.Hertz.unit_vector_arg


def test_get_conversion_to_scaled(ctx: BoundUnitsContext):
    """Test conversion between units with different multipliers."""
    _ = ctx.Meter
    meter = F.Units.decode_symbol(g=ctx.g, tg=ctx.tg, symbol="m")
    kilometer = F.Units.decode_symbol(g=ctx.g, tg=ctx.tg, symbol="km")

    scale, offset = kilometer.get_conversion_to(meter)
    assert scale == 1000.0
    assert offset == 0.0

    scale, offset = meter.get_conversion_to(kilometer)
    assert scale == 0.001
    assert offset == 0.0


def test_get_conversion_to_affine(ctx: BoundUnitsContext):
    """Test conversion between affine units (DegreeCelsius <-> Kelvin)."""
    celsius = ctx.DegreeCelsius._is_unit.get()
    kelvin = ctx.Kelvin._is_unit.get()

    scale, offset = celsius.get_conversion_to(kelvin)
    assert scale == 1.0
    assert offset == 273.15


def test_get_conversion_to_incommensurable_raises(ctx: BoundUnitsContext):
    """Test that conversion between incommensurable units raises error."""
    meter = ctx.Meter._is_unit.get()
    second = ctx.Second._is_unit.get()

    with pytest.raises(F.Units.UnitsNotCommensurableError):
        meter.get_conversion_to(second)


@pytest.mark.parametrize(
    "symbol,expected_multiplier",
    [
        ("km", 1000.0),
        ("mm", 0.001),
        ("µm", 1e-6),
        ("um", 1e-6),
        ("nm", 1e-9),
        ("pm", 1e-12),
        ("Mm", 1e6),
        ("Gm", 1e9),
    ],
)
def test_decode_symbol_si_prefixes(
    ctx: BoundUnitsContext, symbol: str, expected_multiplier: float
):
    """Test decoding symbols with various SI prefixes."""
    _ = ctx.Meter
    decoded = F.Units.decode_symbol(g=ctx.g, tg=ctx.tg, symbol=symbol)

    assert decoded._extract_basis_vector() == F.Units.BasisVector(meter=1)
    assert decoded._extract_multiplier() == pytest.approx(expected_multiplier)


def test_is_affine(ctx: BoundUnitsContext):
    """Test is_affine property for affine and non-affine units."""
    celsius = ctx.DegreeCelsius._is_unit.get()
    kelvin = ctx.Kelvin._is_unit.get()
    meter = ctx.Meter._is_unit.get()

    assert celsius.is_affine
    assert not kelvin.is_affine
    assert not meter.is_affine


def test_is_dimensionless(ctx: BoundUnitsContext):
    """Test is_dimensionless property."""
    dimensionless = ctx.Dimensionless._is_unit.get()
    percent = ctx.Percent._is_unit.get()
    ppm = ctx.Ppm._is_unit.get()
    meter = ctx.Meter._is_unit.get()

    assert dimensionless.is_dimensionless()
    assert percent.is_dimensionless()
    assert ppm.is_dimensionless()
    assert not meter.is_dimensionless()


def test_is_angular(ctx: BoundUnitsContext):
    """Test is_angular property."""
    radian = ctx.Radian._is_unit.get()
    degree = ctx.Degree._is_unit.get()
    meter = ctx.Meter._is_unit.get()
    dimensionless = ctx.Dimensionless._is_unit.get()

    assert radian.is_angular()
    assert degree.is_angular()
    assert not meter.is_angular()
    assert not dimensionless.is_angular()
