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


class IsBaseUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    symbol = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(cls, symbol: str) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        # out.add_dependant(
        #     MakeEdge(
        #         [out],
        #         [symbol],
        #         edge=EdgePointer.build(identifier=None, order=None),
        #     )
        # )
        return out


# class UnitVectorComponent(fabll.Node):
#     base_unit = F.Collections.Pointer.MakeChild()
#     exponent=F.Parameters.NumericParameter.MakeChild(unit=Dimensionless,integer=True)
#
#     @classmethod
#     def MakeChild(
#         cls, base_unit: type[fabll.NodeT], exponent: int
#     ) -> fabll._ChildField[Any]:
#         out = fabll._ChildField(cls)
#         base_unit_field = fabll._ChildField(base_unit)
#         out.add_dependant(base_unit_field)
#         out.add_dependant(
#             F.Collections.Pointer.MakeEdge([out, cls.base_unit], [base_unit_field])
#         )
#         return out


class IsUnit(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    base_units = F.Collections.PointerSet.MakeChild()

    @classmethod
    def MakeChild(
        cls, symbol: str, base_units: list[tuple[type[fabll.NodeT], int]]
    ) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        # FIXME cycling code [IsUnit, UnitVectorComponent, Dimensionless]
        # for base_unit, exponent in base_units:
        #    base_unit_field = _UnitVectorComponent.MakeChild(base_unit, exponent)
        #    out.add_dependant(base_unit_field)
        #    out.add_dependant(
        #        F.Collections.PointerSet.MakeEdge(
        #            [out, cls.base_units],
        #            [base_unit_field],
        #        )
        #    )
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

    def get_unit(self) -> IsUnit:
        return self.unit.get().deref().get_trait(IsUnit)

    def setup(self, units: type[fabll.NodeT]) -> Self:
        unit_node = units.bind_typegraph(tg=self.tg).create_instance(g=self.g)
        self.unit.get().point(unit_node)
        return self

    @classmethod
    def MakeChild(cls, unit: type[fabll.NodeT]) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        unit_field = fabll._ChildField(unit)
        out.add_dependant(unit_field)
        out.add_dependant(F.Collections.Pointer.MakeEdge([out, cls.unit], [unit_field]))
        return out


# Base units ---------------------------------------------------------------------------


class Ampere(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild("A"))
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("A", []))


class Meter(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild("m"))
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("m", []))


class Kilogram(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild("kg"))
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("kg", []))


class Second(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild("s"))
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("s", []))


class Kelvin(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild("K"))
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("K", []))


class Mole(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild("mol"))
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("mol", []))


class Candela(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild("cd"))
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("cd", []))


class Bit(fabll.Node):
    _is_base_unit = fabll.Traits.MakeEdge(IsBaseUnit.MakeChild("bit"))
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("bit", []))


# Derived units ------------------------------------------------------------------------


class Ohm(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild("Ohm", [(Kilogram, 2), (Meter, 2), (Second, -3), (Ampere, -2)])
    )


class Volt(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild("V", [(Kilogram, 1), (Meter, 2), (Second, -3), (Ampere, -1)])
    )


class Watt(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild("W", [(Kilogram, 1), (Meter, 2), (Second, -3)])
    )


class Hertz(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("Hz", [(Second, -1)]))


class Farad(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild("F", [(Kilogram, -1), (Meter, -2), (Second, 4), (Ampere, 2)])
    )


class Henry(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild("H", [(Kilogram, 1), (Meter, 2), (Second, -2), (Ampere, -2)])
    )


class Lumen(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("lm", [(Candela, 1)]))


class Lux(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(
        IsUnit.MakeChild("lx", [(Candela, 1), (Meter, -2)])
    )


class Dimensionless(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("dimensionless", []))


class Ppm(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("ppm", []))


class Natural(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("natural", []))


class AmpereHour(fabll.Node):
    _is_unit = IsUnit.MakeChild(
        "Ah", [(Ampere, 1), (Second, 3600)]
    )  # TODO: This exponent should be 1, we need some represenation of multiplying


class Decibel(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("dB", []))


class BitPerSecond(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("bps", [(Bit, 1), (Second, -1)]))


class Byte(fabll.Node):
    _is_unit = IsUnit.MakeChild(
        "B", [(Dimensionless, 8)]
    )  # TODO: exponent should be 1, we need some represenation of multiplying


class VoltsPerSecond(fabll.Node):
    _is_unit = fabll.Traits.MakeEdge(IsUnit.MakeChild("V/s", [(Volt, 1), (Second, -1)]))


# Scalar units ------------------------------------------------------------------------

# dB, %, ppm


# Non-SI -------------------------------------------------------------------------------

# byte, bit
