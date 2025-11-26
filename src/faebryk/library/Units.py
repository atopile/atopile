"""
Implements a unit system and associated dimensional analysis.

All units are built on top of the SI base units, plus extensions for discrete quantities
(described below). A derived unit in this system can be modeled as a module over the
integers, represented by a vector of exponents for each of the base units, plus a
multiplier and offset to represent an affine transformation.

Dimensional properties:
- Units are commensurable if they share the same basis vector.
- An expression is dimensionally homogenous if all operands are commensurable.
- Dimensional homegeneity / commensurability is required for comparison, equation,
  addition, and subtraction of dimensional quantities.

Arithmetic:
- Unit multiplication/division map to addition/subtraction in the module, or
  element-wise addition/subtraction of the basis vectors.
- Exponentiation maps to scalar multiplication in the module, or element-wise
  multiplication of the basis vectors.
- Integration and differentiation map respectively to multiplication or division by the
  unit of the variable being integrated or differentiated with respect to, and therefore
  addition or subtraction of the involved basis vectors.

Discrete quantities:
The SI system specifies units for continuous quantities only. We extend this to include
certain discrete quantities (e.g. bits) in order to capture compatibility semantics.

Non-SI quantities:
Non-SI units are represented as affine transformations of SI units.

Angles:
Angle and solid angle (radian and steradian) dimensions are included in the basis,
contrary to the SI system, where they are dimensionless. This permits distinction
between e.g. torque and energy which would otherwise have the same basis vector.

Potential extensions to consider:
- explicit modeling of dimensions, separately from units
- support for rational expoonents
- model the distinction between affine and vector quantities
- also require orientational homogeneity when checking for commensurability

TODO:
 - add support for logarithmic units (e.g. dBSPL)
 - consider making incompatible units which differ only by context
   (e.g. Hertz and Becquerel)
 - check all IsUnits in compiled designs for symbol conflicts
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, ClassVar, Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph


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


class UnitsNotCommensurable(Exception):
    def __init__(self, message: str, incommensurable_items: Sequence[fabll.NodeT]):
        self.message = message
        self.incommensurable_items = incommensurable_items

    def __str__(self) -> str:
        return self.message


@dataclass
class _BasisVectorArg:
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

    def _vector_op(
        self, other: "_BasisVectorArg", op: Callable[[int, int], int]
    ) -> "_BasisVectorArg":
        return _BasisVectorArg(
            **{
                field: op(getattr(self, field), getattr(other, field))
                for field in self.__dataclass_fields__.keys()
            }
        )

    def _scalar_op(self, op: Callable[[int], int]) -> "_BasisVectorArg":
        return _BasisVectorArg(
            **{
                field: op(getattr(self, field))
                for field in self.__dataclass_fields__.keys()
            }
        )

    def multiply(self, other: "_BasisVectorArg") -> "_BasisVectorArg":
        return self._vector_op(other, lambda x, y: x + y)

    def divide(self, other: "_BasisVectorArg") -> "_BasisVectorArg":
        return self._vector_op(other, lambda x, y: x - y)

    def scalar_multiply(self, scalar: int) -> "_BasisVectorArg":
        return self._scalar_op(lambda x: x * scalar)


# TODO: iterate over _BasisVectorArg fields
class _BasisVector(fabll.Node):
    ORIGIN: ClassVar[_BasisVectorArg] = _BasisVectorArg()

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
    def MakeChild(cls, vector: _BasisVectorArg) -> fabll._ChildField[Self]:  # type: ignore
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

    def setup(self, vector: _BasisVectorArg) -> Self:  # type: ignore
        g = self.instance.g()
        BoundNumbers = F.Literals.Numbers.bind_typegraph(tg=self.tg)

        for child, exponent in (
            (self.ampere_exponent, vector.ampere),
            (self.second_exponent, vector.second),
            (self.meter_exponent, vector.meter),
            (self.kilogram_exponent, vector.kilogram),
            (self.kelvin_exponent, vector.kelvin),
            (self.mole_exponent, vector.mole),
            (self.candela_exponent, vector.candela),
            (self.radian_exponent, vector.radian),
            (self.steradian_exponent, vector.steradian),
            (self.bit_exponent, vector.bit),
        ):
            child.get().alias_to_literal(
                g=g,
                value=BoundNumbers.create_instance(g=g).setup_from_singleton(
                    value=float(exponent)
                ),
            )

    def extract_vector(self) -> _BasisVectorArg:
        return _BasisVectorArg(
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

    basis_vector = F.Collections.Pointer.MakeChild()
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
        unit_vector: _BasisVectorArg,
        multiplier: float = 1.0,
        offset: float = 0.0,
    ) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)

        for child, lit in (
            (cls.symbol, F.Literals.Strings.MakeChild(*symbols)),
            # TODO: unit?
            (cls.multiplier, F.Literals.Numbers.MakeChild(value=multiplier)),
            (cls.offset, F.Literals.Numbers.MakeChild(value=offset)),
        ):
            is_expr = F.Expressions.Is.MakeChild_Constrain([[out, child], [lit]])
            is_expr.add_dependant(lit, identifier="lit", before=True)
            out.add_dependant(is_expr)

        unit_vector_field = _BasisVector.MakeChild(unit_vector)
        out.add_dependant(unit_vector_field)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.basis_vector], [unit_vector_field])
        )

        return out

    @classmethod
    def MakeChild_Empty(cls) -> fabll._ChildField[Self]:  # type: ignore
        return fabll._ChildField(cls)

    def setup(  # type: ignore
        self,
        symbols: list[str],
        unit_vector: _BasisVectorArg,
        multiplier: float = 1.0,
        offset: float = 0.0,
    ) -> Self:
        g = self.instance.g()
        BoundNumbers = F.Literals.Numbers.bind_typegraph(tg=self.tg)

        self.symbol.get().alias_to_literal(*symbols, g=g)
        self.multiplier.get().alias_to_literal(
            g=g,
            value=BoundNumbers.create_instance(g=g).setup_from_singleton(
                value=multiplier
            ),
        )
        self.offset.get().alias_to_literal(
            g=g,
            value=BoundNumbers.create_instance(g=g).setup_from_singleton(value=offset),
        )
        _BasisVector.bind_instance(self.basis_vector.get().deref().instance).setup(
            vector=unit_vector
        )

        return self

    def _extract_basis_vector(self) -> _BasisVectorArg:
        return _BasisVector.bind_instance(
            self.basis_vector.get().deref().instance
        ).extract_vector()

    def _extract_multiplier(self) -> float:
        return self.multiplier.get().force_extract_literal().get_value()

    def _extract_offset(self) -> float:
        return self.offset.get().force_extract_literal().get_value()

    def is_commensurable_with(self, other: "IsUnit") -> bool:
        self_vector = self._extract_basis_vector()
        other_vector = other._extract_basis_vector()
        return self_vector == other_vector

    def is_dimensionless(self) -> bool:
        return self._extract_basis_vector() == _BasisVector.ORIGIN

    def to_base_units(self, g: graph.GraphView, tg: graph.TypeGraph) -> "IsUnit":
        """
        Returns a new anonymous unit with the same basis vector, but with multiplier=1.0
        and offset=0.0.

        Examples:
        Kilometer.to_base_units() -> Meter
        DegreesCelsius.to_base_units() -> Kelvin
        Newton.to_base_units() -> kg*m/s^-2 (anonymous)

        # TODO: lookup and return existing named unit if available
        """

        return self._new(
            g=g, tg=tg, vector=self._extract_basis_vector(), multiplier=1.0, offset=0.0
        )

    def _new(
        self,
        g: graph.GraphView,
        tg: graph.TypeGraph,
        vector: _BasisVectorArg,
        multiplier: float,
        offset: float,
    ) -> "IsUnit":
        # TODO: generate symbol
        unit = (
            _AnonymousUnit.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup(vector=vector, multiplier=multiplier, offset=offset)
        )

        return unit.get_trait(IsUnit)

    def op_multiply(
        self, g: graph.GraphView, tg: graph.TypeGraph, other: "IsUnit"
    ) -> "IsUnit":
        v1, v2 = self._extract_basis_vector(), other._extract_basis_vector()
        m1, m2 = self._extract_multiplier(), other._extract_multiplier()

        new_multiplier = m1 * m2
        new_vector = v1.multiply(v2)

        return self._new(
            g=g,
            tg=tg,
            vector=new_vector,
            multiplier=new_multiplier,
            offset=0.0,  # TODO
        )

    def op_divide(
        self, g: graph.GraphView, tg: graph.TypeGraph, other: "IsUnit"
    ) -> "IsUnit":
        v1, v2 = self._extract_basis_vector(), other._extract_basis_vector()
        m1, m2 = self._extract_multiplier(), other._extract_multiplier()

        new_multiplier = m1 / m2
        new_vector = v1.divide(v2)

        return self._new(
            g=g,
            tg=tg,
            vector=new_vector,
            multiplier=new_multiplier,
            offset=0.0,  # TODO
        )

    def op_invert(self, g: graph.GraphView, tg: graph.TypeGraph) -> "IsUnit":
        v = self._extract_basis_vector()
        m = self._extract_multiplier()
        return self._new(
            g=g,
            tg=tg,
            vector=v.scalar_multiply(-1),
            multiplier=1.0 / m,
            offset=0.0,
        )

    def op_power(
        self, g: graph.GraphView, tg: graph.TypeGraph, exponent: int
    ) -> "IsUnit":
        v = self._extract_basis_vector()
        m = self._extract_multiplier()
        return self._new(
            g=g,
            tg=tg,
            vector=v.scalar_multiply(exponent),
            multiplier=m**exponent,
            offset=0.0,  # TODO
        )

    def get_conversion_to(self, target: "IsUnit") -> tuple[float, float]:
        if not self.is_commensurable_with(target):
            raise UnitsNotCommensurable(
                f"Units {self} and {target} are not commensurable",
                incommensurable_items=[self, target],
            )

        m1, o1 = self._extract_multiplier(), self._extract_offset()
        m2, o2 = target._extract_multiplier(), target._extract_offset()

        scale = m1 / m2
        offset = (o1 - o2) / m2

        return (scale, offset)


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

    def setup(self, g: graph.GraphView, unit: fabll.Node) -> Self:
        self.unit.get().point(unit)
        return self

    def get_unit(self) -> IsUnit:
        return self.unit.get().deref().get_trait(IsUnit)


UnitVectorT = list[tuple[type[fabll.Node], int]]


def make_unit_expression_type(unit_vector: UnitVectorT) -> type[fabll.Node]:
    from faebryk.library.Expressions import Multiply, Power

    class UnitExpression(fabll.Node):
        expr = F.Collections.Pointer.MakeChild()

        @classmethod
        def MakeChild(cls, *units: type[fabll.Node]) -> fabll._ChildField[Self]:  # type: ignore
            out = fabll._ChildField(cls)
            term_fields = []

            for unit, exponent in unit_vector:
                unit_field = unit.MakeChild()
                out.add_dependant(unit_field)

                exponent_field = (
                    F.Parameters.NumericParameter.MakeChild_UnresolvedUnits(
                        integer=True
                    )
                )
                out.add_dependant(exponent_field)
                exponent_lit = F.Literals.Numbers.MakeChild(value=float(exponent))
                exponent_is_expr = F.Expressions.Is.MakeChild_Constrain(
                    [[exponent_field], [exponent_lit]]
                )
                exponent_is_expr.add_dependant(
                    exponent_lit, identifier="lit", before=True
                )
                out.add_dependant(exponent_is_expr)

                term_field = Power.MakeChild_FromOperands(unit_field, exponent_field)
                out.add_dependant(term_field)
                term_fields.append(term_field)

            expr_field = Multiply.MakeChild_FromOperands(*term_fields)
            out.add_dependant(expr_field)
            out.add_dependant(
                F.Collections.Pointer.MakeEdge([out, cls.expr], [expr_field])
            )

            return out

    unit_vector_str = "".join(
        f"{unit.__name__}^{exponent}" for unit, exponent in unit_vector
    )
    UnitExpression.__name__ = f"UnitExpression<{unit_vector_str}>"

    return UnitExpression


class _AnonymousUnit(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild_Empty())

    def setup(  # type: ignore
        self, vector: _BasisVectorArg, multiplier: float = 1.0, offset: float = 0.0
    ) -> Self:
        self._is_unit.get().setup(
            symbols=[],
            unit_vector=vector,
            multiplier=multiplier,
            offset=offset,
        )
        return self


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


# TODO: rename to One?
class Dimensionless(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVector.ORIGIN

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.dimensionless], unit_vector_arg)
    )


# SI base units ------------------------------------------------------------------------


class Ampere(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(ampere=1)

    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Ampere], unit_vector_arg)
    )


class Meter(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(meter=1)

    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Meter], unit_vector_arg)
    )


class Kilogram(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(kilogram=1)

    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kilogram], unit_vector_arg)
    )


class Second(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(second=1)

    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Second], unit_vector_arg)
    )


class Kelvin(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(kelvin=1)

    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Kelvin], unit_vector_arg)
    )


class Mole(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(mole=1)

    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Mole], unit_vector_arg)
    )


class Candela(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(candela=1)

    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Candela], unit_vector_arg)
    )


# SI derived units ---------------------------------------------------------------------


# TODO: prevent mixing Radian / Steradian / dimensionless
class Radian(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(radian=1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Radian], unit_vector_arg)
    )


class Steradian(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(steradian=1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Steradian], unit_vector_arg)
    )


class Hertz(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(second=-1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Hertz], unit_vector_arg)
    )


class Newton(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=1, meter=1, second=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Newton], unit_vector_arg)
    )


class Pascal(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=1, meter=-1, second=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Pascal], unit_vector_arg)
    )


class Joule(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=1, meter=2, second=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Joule], unit_vector_arg)
    )


class Watt(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=1, meter=2, second=-3
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Watt], unit_vector_arg)
    )


class Coulomb(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(ampere=1, second=1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Coulomb], unit_vector_arg)
    )


class Volt(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=1, meter=2, second=-3, ampere=-1
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Volt], unit_vector_arg)
    )


class Farad(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=-1, meter=-2, second=4, ampere=2
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Farad], unit_vector_arg)
    )


class Ohm(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=2, meter=2, second=-3, ampere=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Ohm], unit_vector_arg)
    )


class Siemens(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=-1, meter=-2, second=3, ampere=2
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Siemens], unit_vector_arg)
    )


class Weber(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=1, meter=2, second=-2, ampere=-1
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Weber], unit_vector_arg)
    )


class Tesla(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=1, second=-2, ampere=-1
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Tesla], unit_vector_arg)
    )


class Henry(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        kilogram=1, meter=2, second=-2, ampere=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Henry], unit_vector_arg)
    )


class DegreeCelsius(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(kelvin=1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.DegreeCelsius],
            unit_vector_arg,
            multiplier=1.0,
            offset=273.15,
        )
    )


class Lumen(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(candela=1, steradian=1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lumen], unit_vector_arg)
    )


class Lux(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(
        candela=1, steradian=1, meter=-2
    )

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Lux], unit_vector_arg)
    )


# TODO: prevent mixing with Hertz? also consider contexts system ala pint
class Becquerel(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(second=-1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Becquerel], unit_vector_arg)
    )


class Gray(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(meter=2, second=-2)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Gray], unit_vector_arg)
    )


class Sievert(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(meter=2, second=-2)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Sievert], unit_vector_arg)
    )


class Katal(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(mole=1, second=-1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Katal], unit_vector_arg)
    )


# non-SI base units --------------------------------------------------------------------


class Bit(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(bit=1)

    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.Bit], unit_vector_arg)
    )


# Scalar multiples --------------------------------------------------------------------


class Percent(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVector.ORIGIN

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Percent], unit_vector_arg, multiplier=1e-2
        )
    )


class Ppm(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVector.ORIGIN

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Ppm], unit_vector_arg, multiplier=1e-6
        )
    )


# Common non-SI multiples --------------------------------------------------------------


class Hour(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(second=1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.Hour], unit_vector_arg, multiplier=3600.0
        )
    )


class Byte(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(bit=1)

    _is_unit = IsUnit.MakeChild(
        _UNIT_SYMBOLS[_UnitRegistry.Byte], unit_vector_arg, multiplier=8.0
    )


# Common unit combinations -------------------------------------------------------------


class BitPerSecond(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(bit=1, second=-1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UNIT_SYMBOLS[_UnitRegistry.BitPerSecond], unit_vector_arg)
    )


class AmpereHour(fabll.Node):
    unit_vector_arg: ClassVar[_BasisVectorArg] = _BasisVectorArg(ampere=1, second=1)

    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UNIT_SYMBOLS[_UnitRegistry.AmpereHour], unit_vector_arg, multiplier=3600.0
        )
    )


# Logarithmic units --------------------------------------------------------------------
# TODO: logarithmic units


# Unit expressions ---------------------------------------------------------------------

# Covers compound unit expressions used elsewhere in the stdlib

VoltsPerSecond = make_unit_expression_type([(Volt, 1), (Second, -1)])
