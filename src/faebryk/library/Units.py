from typing import Any

import faebryk.core.node as fabll
import faebryk.library._F as F

# TODO add all si units
# TODO decide whether base units require unit trait


class IsBaseUnit(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()
    symbol = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(cls, symbol: str) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        # out.add_dependant(
        #     EdgeField(
        #         [out],
        #         [symbol],
        #         edge=EdgePointer.build(identifier=None, order=None),
        #     )
        # )
        return out


class IsUnit(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()
    base_unit = fabll.ChildField(fabll.Node)

    @classmethod
    def MakeChild(
        cls, symbol: str, base_units: list[tuple[type[fabll.NodeT], int]]
    ) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        # TODO
        return out

    @staticmethod
    def is_compatible_with(unit: "fabll.NodeT", other: "fabll.NodeT") -> bool:
        # TODO
        raise NotImplementedError

    @staticmethod
    def get_units(obj: "fabll.NodeT") -> "fabll.NodeT":
        # TODO
        raise NotImplementedError

    @staticmethod
    def get_units_or_dimensionless(obj: "fabll.NodeT") -> "fabll.NodeT":
        # TODO
        raise NotImplementedError


# Base units ---------------------------------------------------------------------------


class Ampere(fabll.Node):
    _is_base_unit = IsBaseUnit.MakeChild("A")
    _is_unit = IsUnit.MakeChild("A", [])


class Meter(fabll.Node):
    _is_base_unit = IsBaseUnit.MakeChild("m")
    _is_unit = IsUnit.MakeChild("m", [])


class Kilogram(fabll.Node):
    _is_base_unit = IsBaseUnit.MakeChild("kg")
    _is_unit = IsUnit.MakeChild("kg", [])


class Second(fabll.Node):
    _is_base_unit = IsBaseUnit.MakeChild("s")
    _is_unit = IsUnit.MakeChild("s", [])


class Kelvin(fabll.Node):
    _is_base_unit = IsBaseUnit.MakeChild("K")
    _is_unit = IsUnit.MakeChild("K", [])


class Mole(fabll.Node):
    _is_base_unit = IsBaseUnit.MakeChild("mol")
    _is_unit = IsUnit.MakeChild("mol", [])


class Candela(fabll.Node):
    _is_base_unit = IsBaseUnit.MakeChild("cd")
    _is_unit = IsUnit.MakeChild("cd", [])


class Bit(fabll.Node):
    _is_base_unit = IsBaseUnit.MakeChild("bit")
    _is_unit = IsUnit.MakeChild("bit", [])


# Derived units ------------------------------------------------------------------------


class Ohm(fabll.Node):
    _is_unit = IsUnit.MakeChild(
        "Ohm", [(Kilogram, 2), (Meter, 2), (Second, -3), (Ampere, -2)]
    )


class Volt(fabll.Node):
    _is_unit = IsUnit.MakeChild(
        "V", [(Kilogram, 1), (Meter, 2), (Second, -3), (Ampere, -1)]
    )


class Watt(fabll.Node):
    _is_unit = IsUnit.MakeChild("W", [(Kilogram, 1), (Meter, 2), (Second, -3)])


class Hertz(fabll.Node):
    _is_unit = IsUnit.MakeChild("Hz", [(Second, -1)])


class Farad(fabll.Node):
    _is_unit = IsUnit.MakeChild(
        "F", [(Kilogram, -1), (Meter, -2), (Second, 4), (Ampere, 2)]
    )


class Henry(fabll.Node):
    _is_unit = IsUnit.MakeChild(
        "H", [(Kilogram, 1), (Meter, 2), (Second, -2), (Ampere, -2)]
    )


class Lumen(fabll.Node):
    _is_unit = IsUnit.MakeChild("lm", [(Candela, 1)])


class Lux(fabll.Node):
    _is_unit = IsUnit.MakeChild("lx", [(Candela, 1), (Meter, -2)])


class Dimensionless(fabll.Node):
    _is_unit = IsUnit.MakeChild("dimensionless", [])


class Ppm(fabll.Node):
    _is_unit = IsUnit.MakeChild("ppm", [])


class Natural(fabll.Node):
    _is_unit = IsUnit.MakeChild("natural", [])


class AmpereHour(fabll.Node):
    _is_unit = IsUnit.MakeChild("Ah", [(Ampere, 1), (Second, 3600)])


class Decibel(fabll.Node):
    _is_unit = IsUnit.MakeChild("dB", [])


class BitPerSecond(fabll.Node):
    _is_unit = IsUnit.MakeChild("bps", [(Bit, 1), (Second, -1)])


class Byte(fabll.Node):
    _is_unit = IsUnit.MakeChild("B", [(Dimensionless, 8)])


class VoltsPerSecond(fabll.Node):
    _is_unit = IsUnit.MakeChild("V/s", [(Volt, 1), (Second, -1)])


# Scalar units ------------------------------------------------------------------------

# dB, %, ppm


# Non-SI -------------------------------------------------------------------------------

# byte, bit
