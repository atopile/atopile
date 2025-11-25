from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Self

import faebryk.core.node as fabll
import faebryk.library._F as F

"""
Units representation.

All units are built on top of the SI base units, plus extensions for discrete quantities
(described below). A derived unit in this system can be represented as a vector of
exponents for each of the base units, plus a multiplier and offset to represent a linear
transformation.

Discrete quantities:
The SI system specifies units for continuous quantities only. We extend this to include
certain discrete quantities (e.g. bits) in order to capture compatibility semantics.
These units correspond to a count of 1 rather than to a physical measurement.

Non-SI quantities:
Non-SI units are represented as a linear transformation of an SI unit.

Compatibility:
Units are compatible iff they share the same base unit vector.

Arithmetic:
Unit multiplication/division map to element-wise addition/subtraction of the base unit
vectors.

TODO:
 - add support for logarithmic units (e.g. dBSPL)
 - consider making incompatible units which differ only by context
   (e.g. Hertz and Becquerel)
 - check all IsUnits in compiled designs for symbol conflicts
"""


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


@dataclass
class _BaseUnitVectorArg:
    ampere: int = 0
    second: int = 0
    meter: int = 0
    kilogram: int = 0
    kelvin: int = 0
    mole: int = 0
    candela: int = 0
    radian: int = 0
    steradian: int = 0
    bit: int = 0


class _BaseUnitVector(fabll.Node):
    ampere_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
        integer=True
    )
    second_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
        integer=True
    )
    meter_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
        integer=True
    )
    kilogram_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
        integer=True
    )
    kelvin_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
        integer=True
    )
    mole_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
        integer=True
    )
    candela_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
        integer=True
    )

    # pseudo base units
    radian_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
        integer=True
    )
    steradian_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
        integer=True
    )

    # non-SI base units
    bit_exponent = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(integer=True)

    @classmethod
    def MakeChild(cls, vector: _BaseUnitVectorArg) -> fabll._ChildField[Self]:  # type: ignore
        out = fabll._ChildField(cls)

        for child, exponent in (
            (cls.ampere_exponent, vector.ampere),
            (cls.second_exponent, vector.second),
            (cls.meter_exponent, vector.meter),
            (cls.kilogram_exponent, vector.kilogram),
            (cls.kelvin_exponent, vector.kelvin),
            (cls.mole_exponent, vector.mole),
            (cls.candela_exponent, vector.candela),
            (cls.radian_exponent, vector.radian),
            (cls.steradian_exponent, vector.steradian),
            (cls.bit_exponent, vector.bit),
        ):
            assert isinstance(exponent, int)
            lit = F.Literals.Numbers.MakeChild(value=float(exponent))
            is_expr = F.Expressions.Is.MakeChild_Constrain([[out, child], [lit]])
            is_expr.add_dependant(lit, identifier="lit", before=True)
            out.add_dependant(is_expr)

        return out

    def extract_vector(self) -> _BaseUnitVectorArg:
        return _BaseUnitVectorArg(
            ampere=int(self.ampere_exponent.get().force_extract_literal().get_value()),
            second=int(self.second_exponent.get().force_extract_literal().get_value()),
            meter=int(self.meter_exponent.get().force_extract_literal().get_value()),
            kilogram=int(
                self.kilogram_exponent.get().force_extract_literal().get_value()
            ),
            kelvin=int(self.kelvin_exponent.get().force_extract_literal().get_value()),
            mole=int(self.mole_exponent.get().force_extract_literal().get_value()),
            candela=int(
                self.candela_exponent.get().force_extract_literal().get_value()
            ),
            radian=int(self.radian_exponent.get().force_extract_literal().get_value()),
            steradian=int(
                self.steradian_exponent.get().force_extract_literal().get_value()
            ),
            bit=int(self.bit_exponent.get().force_extract_literal().get_value()),
        )


class IsBaseUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class IsUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    symbol = F.Parameters.StringParameter.MakeChild()
    """
    Symbol or symbols representing the unit. Any member of the set is valid to indicate
    the unit in ato code. Must not conflict with symbols for other units
    """

    unit_vector = F.Collections.Pointer.MakeChild()
    """
    SI base units and corresponding exponents representing a derived unit. Must consist
    of base units only.
    """

    multiplier = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits()
    """
    Multiplier to apply when converting to SI base units.
    """

    offset = F.Parameters.NumericParameter.MakeChild_UnresolvedUnits()
    """
    Offset to apply when converting to SI base units.
    """

    @classmethod
    def MakeChild(  # type: ignore
        cls,
        symbols: list[str],
        unit_vector: _BaseUnitVectorArg,
        multiplier: float = 1.0,
        offset: float = 0.0,
    ) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)

        # TODO: support multiple symbols (requires string set literals)
        assert len(symbols) == 1
        (symbol,) = symbols

        for child, lit in (
            (cls.symbol, F.Literals.Strings.MakeChild(symbol)),
            # TODO: unit?
            (cls.multiplier, F.Literals.Numbers.MakeChild(value=multiplier)),
            (cls.offset, F.Literals.Numbers.MakeChild(value=offset)),
        ):
            is_expr = F.Expressions.Is.MakeChild_Constrain([[out, child], [lit]])
            is_expr.add_dependant(lit, identifier="lit", before=True)
            out.add_dependant(is_expr)

        unit_vector_field = _BaseUnitVector.MakeChild(unit_vector)
        out.add_dependant(unit_vector_field)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.unit_vector], [unit_vector_field])
        )

        return out

    def is_compatible_with(self, other: "IsUnit") -> bool:
        self_unit_vector = _BaseUnitVector.bind_instance(
            self.unit_vector.get().deref().instance
        ).extract_vector()

        other_unit_vector = _BaseUnitVector.bind_instance(
            other.unit_vector.get().deref().instance
        ).extract_vector()

        return self_unit_vector == other_unit_vector


class HasUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    unit = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, unit: type[fabll.NodeT]) -> fabll._ChildField[Self]:  # type: ignore
        out = fabll._ChildField(cls)
        unit_field = unit.MakeChild()
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


_UNIT_SYMBOLS: dict[_UnitRegistry, list[str]] = {
    _UnitRegistry.dimensionless: ["dimensionless"],  # TODO: allow None?
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
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.dimensionless], _BaseUnitVectorArg()
        )
    )


# SI base units ------------------------------------------------------------------------


class Ampere(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ampere], _BaseUnitVectorArg(ampere=1)
        )
    )


class Meter(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Meter], _BaseUnitVectorArg(meter=1)
        )
    )


class Kilogram(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Kilogram], _BaseUnitVectorArg(kilogram=1)
        )
    )


class Second(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Second], _BaseUnitVectorArg(second=1)
        )
    )


class Kelvin(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Kelvin], _BaseUnitVectorArg(kelvin=1)
        )
    )


class Mole(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Mole], _BaseUnitVectorArg(mole=1))
    )


class Candela(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Candela], _BaseUnitVectorArg(candela=1)
        )
    )


# SI derived units ---------------------------------------------------------------------


# TODO: prevent mixing Radian / Steradian / dimensionless
class Radian(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Radian], _BaseUnitVectorArg(radian=1)
        )
    )


class Steradian(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Steradian], _BaseUnitVectorArg(steradian=1)
        )
    )


class Hertz(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Hertz], _BaseUnitVectorArg(second=-1)
        )
    )


class Newton(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Newton],
            _BaseUnitVectorArg(kilogram=1, meter=1, second=-2),
        )
    )


class Pascal(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Pascal],
            _BaseUnitVectorArg(kilogram=1, meter=-1, second=-2),
        )
    )


class Joule(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Joule],
            _BaseUnitVectorArg(kilogram=1, meter=2, second=-2),
        )
    )


class Watt(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Watt],
            _BaseUnitVectorArg(kilogram=1, meter=2, second=-3),
        )
    )


class Coulomb(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Coulomb],
            _BaseUnitVectorArg(ampere=1, second=1),
        )
    )


class Volt(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Volt],
            _BaseUnitVectorArg(kilogram=1, meter=2, second=-3, ampere=-1),
        )
    )


class Farad(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Farad],
            _BaseUnitVectorArg(kilogram=-1, meter=-2, second=4, ampere=2),
        )
    )


class Ohm(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ohm],
            _BaseUnitVectorArg(kilogram=2, meter=2, second=-3, ampere=-2),
        )
    )


class Siemens(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Siemens],
            _BaseUnitVectorArg(kilogram=-1, meter=-2, second=3, ampere=2),
        )
    )


class Weber(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Weber],
            _BaseUnitVectorArg(kilogram=1, meter=2, second=-2, ampere=-1),
        )
    )


class Tesla(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Tesla],
            _BaseUnitVectorArg(kilogram=1, second=-2, ampere=-1),
        )
    )


class Henry(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Henry],
            _BaseUnitVectorArg(kilogram=1, meter=2, second=-2, ampere=-2),
        )
    )


class DegreeCelsius(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.DegreeCelsius],
            _BaseUnitVectorArg(kelvin=1),
            multiplier=1.0,
            offset=273.15,
        )
    )


class Lumen(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Lumen],
            _BaseUnitVectorArg(candela=1, steradian=1),
        )
    )


class Lux(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Lux], _BaseUnitVectorArg(candela=1, meter=-2)
        )
    )


# TODO: prevent mixing with Hertz?
class Becquerel(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Becquerel], _BaseUnitVectorArg(second=-1)
        )
    )


class Gray(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Gray], _BaseUnitVectorArg(kilogram=1, meter=2)
        )
    )


class Sievert(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Sievert],
            _BaseUnitVectorArg(kilogram=1, meter=2),
        )
    )


class Katal(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Katal], _BaseUnitVectorArg(mole=1, second=-1)
        )
    )


# non-SI base units --------------------------------------------------------------------


class Bit(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Bit], _BaseUnitVectorArg(bit=1))
    )


# Scalar multiples --------------------------------------------------------------------


class Percent(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Percent], _BaseUnitVectorArg(), multiplier=1e-2
        )
    )


class Ppm(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ppm], _BaseUnitVectorArg(), multiplier=10e-6
        )
    )


# Common non-SI multiples --------------------------------------------------------------


class Hour(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Hour],
            _BaseUnitVectorArg(second=1),
            multiplier=3600.0,
        )
    )


class Byte(fabll.Node):
    _is_unit = IsUnit.MakeChild(
        _UNIT_SYMBOLS[_UnitRegistry.Byte], _BaseUnitVectorArg(bit=1), multiplier=8.0
    )


# Common unit combinations -------------------------------------------------------------


class BitPerSecond(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.BitPerSecond],
            _BaseUnitVectorArg(bit=1, second=-1),
        )
    )


class AmpereHour(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.AmpereHour],
            _BaseUnitVectorArg(ampere=1, second=1),
            multiplier=3600.0,
        )
    )


# Logarithmic units --------------------------------------------------------------------
# TODO: logarithmic units
