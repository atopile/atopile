import faebryk.core.node as fabll

# TODO add all si units
# TODO decide whether base units require unit trait

# Base units ---------------------------------------------------------------------------


class Ampere(fabll.Node):
    _is_base_unit = fabll.IsBaseUnit.MakeChild("A")
    _is_unit = fabll.IsUnit.MakeChild("A", [])


class Meter(fabll.Node):
    _is_base_unit = fabll.IsBaseUnit.MakeChild("m")
    _is_unit = fabll.IsUnit.MakeChild("m", [])


class Kilogram(fabll.Node):
    _is_base_unit = fabll.IsBaseUnit.MakeChild("kg")
    _is_unit = fabll.IsUnit.MakeChild("kg", [])


class Second(fabll.Node):
    _is_base_unit = fabll.IsBaseUnit.MakeChild("s")
    _is_unit = fabll.IsUnit.MakeChild("s", [])


class Kelvin(fabll.Node):
    _is_base_unit = fabll.IsBaseUnit.MakeChild("K")
    _is_unit = fabll.IsUnit.MakeChild("K", [])


class Mole(fabll.Node):
    _is_base_unit = fabll.IsBaseUnit.MakeChild("mol")
    _is_unit = fabll.IsUnit.MakeChild("mol", [])


class Candela(fabll.Node):
    _is_base_unit = fabll.IsBaseUnit.MakeChild("cd")
    _is_unit = fabll.IsUnit.MakeChild("cd", [])


class Bit(fabll.Node):
    _is_base_unit = fabll.IsBaseUnit.MakeChild("bit")
    _is_unit = fabll.IsUnit.MakeChild("bit", [])


# Derived units ------------------------------------------------------------------------


class Ohm(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild(
        "Ohm", [(Kilogram, 2), (Meter, 2), (Second, -3), (Ampere, -2)]
    )


class Volt(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild(
        "V", [(Kilogram, 1), (Meter, 2), (Second, -3), (Ampere, -1)]
    )


class Watt(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("W", [(Kilogram, 1), (Meter, 2), (Second, -3)])


class Hertz(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("Hz", [(Second, -1)])


class Farad(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild(
        "F", [(Kilogram, -1), (Meter, -2), (Second, 4), (Ampere, 2)]
    )


class Henry(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild(
        "H", [(Kilogram, 1), (Meter, 2), (Second, -2), (Ampere, -2)]
    )


class Lumen(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("lm", [(Candela, 1)])


class Lux(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("lx", [(Candela, 1), (Meter, -2)])


class Dimensionless(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("dimensionless", [])


class Ppm(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("ppm", [])


class Natural(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("natural", [])


class AmpereHour(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("Ah", [(Ampere, 1), (Second, 3600)])


class Decibel(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("dB", [])


class BitPerSecond(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("bps", [(Bit, 1), (Second, -1)])


class Byte(fabll.Node):
    _is_unit = fabll.IsUnit.MakeChild("B", [(Dimensionless, 8)])


# Scalar units ------------------------------------------------------------------------

# dB, %, ppm


# Non-SI -------------------------------------------------------------------------------

# byte, bit
