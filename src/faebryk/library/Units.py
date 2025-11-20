from enum import Enum, auto
from typing import Any, Self, Sequence

import faebryk.core.node as fabll
import faebryk.library._F as F


class UnitCompatibilityError(ValueError):
    def __init__(self, message: str, incompatible_items: Sequence[Any]):
        super().__init__(message)
        self.incompatible_items = list(incompatible_items)


# Simple helper to normalize various unit-like objects to a class, defaulting to
# Dimensionless when no unit information is available.
def _unit_or_dimensionless(unit_like: Any) -> type[fabll.Node]:
    if isinstance(unit_like, fabll.TypeNodeBoundTG):
        return unit_like.t
    if isinstance(unit_like, type) and issubclass(unit_like, fabll.Node):
        return unit_like
    if isinstance(unit_like, fabll.Node):
        try:
            unit_trait = unit_like.get_trait(HasUnit).get_unit()
            return type(unit_trait)
        except fabll.TraitNotFound:
            return Dimensionless
    if hasattr(unit_like, "get_unit"):
        return _unit_or_dimensionless(unit_like.get_unit())
    return Dimensionless


# TODO add all si units
# TODO decide whether base units require unit trait
# TODO: check all IsUnits in design for symbol conflicts


class _UnitVectorComponent(fabll.Node):
    base_unit = F.Collections.Pointer.MakeChild()
    exponent = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless, integer=True
    )

    @classmethod
    def MakeChild(
        cls, base_unit: fabll.NodeT, exponent: int
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        # FIXME
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.base_unit], [base_unit])
        )

        # TODO: exponent constraint

        return out


_UnitVectorT = list[tuple["IsUnit | IsBaseUnit", int]]


class IsBaseUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class IsUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    symbol = F.Parameters.StringParameter.MakeChild()
    unit_vector = F.Collections.PointerSet.MakeChild()

    multiplier = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits()
    offset = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits()

    @classmethod
    def MakeChild(  # type: ignore
        cls,
        symbols: list[str],
        unit_vector: _UnitVectorT,
        multiplier: float = 1,
        offset: float = 0,
    ) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)

        # TODO: support multiple symbols (requires string set literals)
        assert len(symbols) == 1
        (symbol,) = symbols
        out.get().symbol.add_dependant(
            F.Expressions.Is.MakeChild_Constrain(
                [[out, cls.symbol], [F.Literals.Strings.MakeChild(value=symbol)]]
            )
        )

        for child, value in (
            (out.get().multiplier, multiplier),
            (out.get().offset, offset),
        ):
            # TODO: unit?
            child.add_dependant(
                F.Expressions.Is.MakeChild_Constrain(
                    [[out, child], [F.Literals.Numbers.MakeChild(value=value)]]
                )
            )

        # TODO: resolve to base units
        # TODO: base_unit might be IsUnit or IsBaseUnit
        for base_unit, exponent in unit_vector:
            base_unit_field = _UnitVectorComponent.MakeChild(base_unit, exponent)
            out.get().unit_vector.add_dependant(base_unit_field)

        return out

    def is_compatible_with(self, other: Any) -> bool:
        return _unit_or_dimensionless(self) == _unit_or_dimensionless(other)

    @staticmethod
    def assert_compatible_units(items: Sequence[Any]) -> Any:
        if not items:
            raise ValueError("At least one item is required")

        units = [_unit_or_dimensionless(item) for item in items]
        reference = units[0]

        if len(units) == 1:
            return reference

        for idx, unit in enumerate(units[1:], start=1):
            if reference != unit:
                raise UnitCompatibilityError(
                    "Operands have incompatible units:\n"
                    + "\n".join(
                        f"`{items[i]}` ({units[i].__name__})" for i in range(len(items))
                    ),
                    incompatible_items=items,
                )

        return reference


class HasUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    unit = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, unit: type[fabll.NodeT]) -> fabll._ChildField[Self]:  # type: ignore
        out = fabll._ChildField(cls)
        unit_field = fabll._ChildField(unit)
        out.add_dependant(unit_field)
        out.add_dependant(F.Collections.Pointer.MakeEdge([out, cls.unit], [unit_field]))
        return out

    def get_unit(self) -> IsUnit:
        return self.unit.get().deref().get_trait(IsUnit)


class _UnitRegistry(Enum):
    # TODO: check all IsUnits in design for symbol conflicts

    dimensionless = auto()

    # Scalar multiples
    Percent = auto()
    Ppm = auto()

    # SI base units
    Ampere = auto()
    Second = auto()
    Meter = auto()
    Kilogram = auto()
    Kelvin = auto()
    Mole = auto()
    Candela = auto()

    # SI derived units
    Radian = auto()
    Steradian = auto()
    Hertz = auto()
    Newton = auto()
    Pascal = auto()
    Joule = auto()
    Watt = auto()
    Coulomb = auto()
    Volt = auto()
    Farad = auto()
    Ohm = auto()
    Siemens = auto()
    Weber = auto()
    Tesla = auto()
    Henry = auto()
    DegreeCelsius = auto()
    Lumen = auto()
    Lux = auto()
    Becquerel = auto()
    Gray = auto()
    Sievert = auto()
    Katal = auto()

    # non-SI units
    Bit = auto()
    Byte = auto()

    # non-SI multiples
    Hour = auto()

    # Common combinations
    BitPerSecond = auto()
    AmpereHour = auto()


_UNIT_SYMBOLS = {
    _UnitRegistry.dimensionless: [""],
    _UnitRegistry.Percent: ["%"],
    _UnitRegistry.Ppm: ["ppm"],
    _UnitRegistry.Ampere: ["A"],
    _UnitRegistry.Second: ["s"],
    _UnitRegistry.Meter: ["m"],
    _UnitRegistry.Kilogram: ["kg"],
    _UnitRegistry.Kelvin: ["K"],
    _UnitRegistry.Mole: ["mol"],
    _UnitRegistry.Candela: ["cd"],
    _UnitRegistry.Radian: ["rad"],
    _UnitRegistry.Steradian: ["sr"],
    _UnitRegistry.Hertz: ["Hz"],
    _UnitRegistry.Newton: ["N"],
    _UnitRegistry.Pascal: ["Pa"],
    _UnitRegistry.Joule: ["J"],
    _UnitRegistry.Watt: ["W"],
    _UnitRegistry.Coulomb: ["C"],
    _UnitRegistry.Volt: ["V"],
    _UnitRegistry.Farad: ["F"],
    _UnitRegistry.Ohm: ["Ω"],
    _UnitRegistry.Siemens: ["S"],
    _UnitRegistry.Weber: ["Wb"],
    _UnitRegistry.Tesla: ["T"],
    _UnitRegistry.Henry: ["H"],
    _UnitRegistry.DegreeCelsius: ["°C"],
    _UnitRegistry.Lumen: ["lm"],
    _UnitRegistry.Lux: ["lx"],
    _UnitRegistry.Becquerel: ["Bq"],
    _UnitRegistry.Gray: ["Gy"],
    _UnitRegistry.Sievert: ["Sv"],
    _UnitRegistry.Katal: ["kat"],
    _UnitRegistry.Bit: ["bit"],
    _UnitRegistry.Byte: ["B"],
    _UnitRegistry.Hour: ["h"],
    _UnitRegistry.BitPerSecond: ["bps"],
    _UnitRegistry.AmpereHour: ["Ah"],
}


# Dimensionless ------------------------------------------------------------------------


class Dimensionless(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.dimensionless], [])
    )


# SI base units ------------------------------------------------------------------------


class Ampere(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ampere], [(_is_base_unit.get(), 1)]
        )
    )


class Meter(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Meter], [(_is_base_unit.get(), 1)])
    )


class Kilogram(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Kilogram], [(_is_base_unit.get(), 1)]
        )
    )


class Second(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Second], [(_is_base_unit.get(), 1)]
        )
    )


class Kelvin(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Kelvin], [(_is_base_unit.get(), 1)]
        )
    )


class Mole(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Mole], [(_is_base_unit.get(), 1)])
    )


class Candela(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Candela], [(_is_base_unit.get(), 1)]
        )
    )


# SI derived units ---------------------------------------------------------------------


class Radian(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Radian], [(Dimensionless._is_unit.get(), 1)]
        )
    )


class Steradian(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Steradian], [(Dimensionless._is_unit.get(), 1)]
        )
    )


class Hertz(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Hertz],
            [(Second._is_unit.get(), -1)],
        )
    )


class Newton(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Newton],
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), 1),
                (Second._is_unit.get(), -2),
            ],
        )
    )


class Pascal(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Pascal],
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), -1),
                (Second._is_unit.get(), -2),
            ],
        )
    )


class Joule(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Joule],
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -2),
            ],
        )
    )


class Watt(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Watt],
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -3),
            ],
        )
    )


class Coulomb(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Coulomb],
            [(Ampere._is_unit.get(), 1), (Second._is_unit.get(), 1)],
        )
    )


class Volt(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Volt],
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -3),
                (Ampere._is_unit.get(), -1),
            ],
        )
    )


class Farad(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Farad],
            [
                (Kilogram._is_unit.get(), -1),
                (Meter._is_unit.get(), -2),
                (Second._is_unit.get(), 4),
                (Ampere._is_unit.get(), 2),
            ],
        )
    )


class Ohm(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ohm],
            [
                (Kilogram._is_unit.get(), 2),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -3),
                (Ampere._is_unit.get(), -2),
            ],
        )
    )


class Siemens(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Siemens],
            [
                (Kilogram._is_unit.get(), -1),
                (Meter._is_unit.get(), -2),
                (Second._is_unit.get(), 3),
                (Ampere._is_unit.get(), 2),
            ],
        )
    )


class Weber(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Weber],
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -2),
                (Ampere._is_unit.get(), -1),
            ],
        )
    )


class Tesla(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Tesla],
            [
                (Kilogram._is_unit.get(), 1),
                (Second._is_unit.get(), -2),
                (Ampere._is_unit.get(), -1),
            ],
        )
    )


class Henry(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Henry],
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -2),
                (Ampere._is_unit.get(), -2),
            ],
        )
    )


class DegreeCelsius(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.DegreeCelsius],
            [(Kelvin._is_unit.get(), 1)],
            multiplier=1,
            offset=273.15,
        )
    )


class Lumen(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Lumen],
            [(Candela._is_unit.get(), 1), (Steradian._is_unit.get(), 1)],
        )
    )


class Lux(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Lux],
            [(Candela._is_unit.get(), 1), (Meter._is_unit.get(), -2)],
        )
    )


class Becquerel(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Becquerel],
            [(Second._is_unit.get(), -1)],
        )
    )


class Gray(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Gray],
            [(Kilogram._is_unit.get(), 1), (Meter._is_unit.get(), 2)],
        )
    )


class Sievert(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Sievert],
            [(Kilogram._is_unit.get(), 1), (Meter._is_unit.get(), 2)],
        )
    )


class Katal(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Katal],
            [(Mole._is_unit.get(), 1), (Second._is_unit.get(), -1)],
        )
    )


# non-SI base units --------------------------------------------------------------------


class Bit(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Bit], [])
    )


# Scalar multiples --------------------------------------------------------------------


class Percent(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Percent],
            [(Dimensionless._is_unit.get(), 1)],
            multiplier=1e-2,
        )
    )


class Ppm(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ppm],
            [(Dimensionless._is_unit.get(), 1)],
            multiplier=10e-6,
        )
    )


# Common non-SI multiples --------------------------------------------------------------


class Hour(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Hour],
            [(Second._is_unit.get(), 1)],
            multiplier=3600,
        )
    )


class Byte(fabll.Node):
    _is_unit = IsUnit.MakeChild(
        _UNIT_SYMBOLS[_UnitRegistry.Byte],
        [(Dimensionless._is_unit.get(), 1)],
        multiplier=8,
    )


# Common unit combinations -------------------------------------------------------------


class BitPerSecond(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.BitPerSecond],
            [(Bit._is_unit.get(), 1), (Second._is_unit.get(), -1)],
        )
    )


class AmpereHour(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.AmpereHour],
            [(Ampere._is_unit.get(), 1), (Hour._is_unit.get(), 1)],
        )
    )


# Logarithmic units --------------------------------------------------------------------
# TODO: logarithmic units
