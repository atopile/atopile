from typing import Any, Sequence, Self
from enum import StrEnum
from typing import Any, Self

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


class _UnitSymbols(StrEnum):
    # SI base units
    Ampere = "A"
    Second = "s"
    Meter = "m"
    Kilogram = "kg"
    Kelvin = "K"
    Mole = "mol"
    Candela = "cd"

    # SI compound units
    Ohm = "Ω"
    Volt = "V"
    Watt = "W"
    Hertz = "Hz"
    Farad = "F"
    Henry = "H"
    Lumen = "lm"
    Lux = "lx"

    # Scalar units
    Radian = "rad"
    Steradian = "sr"


UnitVectorT = list[tuple[fabll.NodeT, int]]


class UnitVectorComponent(fabll.Node):
    base_unit = F.Collections.Pointer.MakeChild()
    exponent = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless, integer=True
    )

    # def setup(
    #     self,
    #     tg: graph.TypeGraph,
    #     base_unit: fabll.Node,
    #     exponent: int,
    # ) -> Self:
    #     self.base_unit.get().point(base_unit)
    #     self.exponent.get().constrain_to_literal(
    #         g=self.instance.g(),
    #         value=F.Literals.Numbers.make_lit(tg=tg, value=exponent),
    #     )
    #     return self

    # @classmethod
    # def create_instance(
    #     cls, tg: graph.TypeGraph, base_unit: fabll.Node, exponent: int
    # ) -> Self:
    #     return (
    #         cls.bind_typegraph(tg=tg)
    #         .create_instance(g=tg.get_graph_view())
    #         .setup(tg=tg, base_unit=base_unit, exponent=exponent)
    #     )

    @classmethod
    def MakeChild(cls, base_unit: fabll.Node, exponent: int) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        # FIXME
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.base_unit], [base_unit])
        )

        # TODO: exponent constraint

        return out


class IsBaseUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class IsUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    symbol = F.Parameters.StringParameter.MakeChild()
    unit_vector = F.Collections.PointerSet.MakeChild()

    multiplier = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
    offset = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    @classmethod
    def MakeChild(
        cls,
        symbol: _UnitSymbols,
        base_units: UnitVectorT,
        multiplier: float = 1,
        offset: float = 0,
    ) -> fabll._ChildField[Any]:
        # TODO: any unit can be the base unit
        # TODO: multiplier, offset

        out = fabll._ChildField(cls)

        # TODO: symbol -> symbols, is! (set of string parameters)
        out.get().symbol.add_dependant(
            F.Expressions.Is.MakeChild_Constrain(
                [[out, cls.symbol], [F.Literals.Strings.MakeChild(value=symbol.value)]]
            )
        )

        # TODO: resolve to base units
        for base_unit, exponent in base_units:
            base_unit_field = UnitVectorComponent.MakeChild(base_unit, exponent)
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


# class HasUnit(fabll.Node):
#     _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
#     unit = F.Collections.Pointer.MakeChild()

#     def get_unit(self) -> IsUnit:
#         return self.unit.get().deref().get_trait(IsUnit)

#     @classmethod
#     def MakeChild(cls, unit: type[fabll.NodeT]) -> fabll._ChildField[Self]:
#         out = fabll._ChildField(cls)
#         unit_field = fabll._ChildField(unit)
#         out.add_dependant(unit_field)
#         out.add_dependant(
#             F.Collections.Pointer.MakeEdge(
#                 [out, cls.unit],
#                 [unit_field],
#             )
#         )
#         return out


# SI base units ------------------------------------------------------------------------


# TODO: add self to unit vector
class Ampere(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild(_UnitSymbols.Ampere, []))


class Meter(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild(_UnitSymbols.Meter, []))


class Kilogram(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild(_UnitSymbols.Kilogram, []))


class Second(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild(_UnitSymbols.Second, []))


class Kelvin(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild(_UnitSymbols.Kelvin, []))


class Mole(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild(_UnitSymbols.Mole, []))


class Candela(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild(_UnitSymbols.Candela, []))


# SI derived units ---------------------------------------------------------------------


class Ohm(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Ohm,
            [
                (Kilogram._is_unit.get(), 2),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -3),
                (Ampere._is_unit.get(), -2),
            ],
        )
    )


class Volt(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Volt,
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -3),
                (Ampere._is_unit.get(), -1),
            ],
        )
    )


class Watt(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Watt,
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -3),
            ],
        )
    )


class Hertz(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Hertz,
            [(Second._is_unit.get(), -1)],
        )
    )


class Farad(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Farad,
            [
                (Kilogram._is_unit.get(), -1),
                (Meter._is_unit.get(), -2),
                (Second._is_unit.get(), 4),
                (Ampere._is_unit.get(), 2),
            ],
        )
    )


class Henry(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Henry,
            [
                (Kilogram._is_unit.get(), 1),
                (Meter._is_unit.get(), 2),
                (Second._is_unit.get(), -2),
                (Ampere._is_unit.get(), -2),
            ],
        )
    )


# TODO: unit vector should be [self, 1]
class Radian(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild(_UnitSymbols.Radian, []))


class Steradian(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(_UnitSymbols.Steradian, [(Radian._is_unit.get(), 2)])
    )


class Lumen(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Lumen,
            [(Candela._is_unit.get(), 1), (Steradian._is_unit.get(), 1)],
        )
    )


class Lux(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Lux,
            [(Candela._is_unit.get(), 1), (Meter._is_unit.get(), -2)],
        )
    )


class Dimensionless(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("dimensionless", []))


class Percent(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Percent, [(Dimensionless._is_unit.get(), 1)], multiplier=1e-2
        )
    )


class Ppm(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Ppm, [(Dimensionless._is_unit.get(), 1)], multiplier=10e-6
        )
    )


class Hour(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.Hour, [(Second._is_unit.get(), 1)], multiplier=3600
        )
    )


class AmpereHour(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.AmpereHour,
            [(Ampere._is_unit.get(), 1), (Hour._is_unit.get(), 1)],
        )
    )


class Bit(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild())
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild(_UnitSymbols.Bit, []))


class BitPerSecond(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild("bps", [(Bit._is_unit.get(), 1), (Second._is_unit.get(), -1)])
    )


class Byte(fabll.Node):
    _is_unit = IsUnit.MakeChild(
        _UnitSymbols.Byte, [(Dimensionless._is_unit.get(), 1)], multiplier=8
    )


class VoltsPerSecond(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild(
            _UnitSymbols.VoltsPerSecond,
            [(Volt._is_unit.get(), 1), (Second._is_unit.get(), -1)],
        )
    )


# Scalar units ------------------------------------------------------------------------

# %, ppm


# Non-SI -------------------------------------------------------------------------------

# byte, bit


# TODO: logarithmic units
