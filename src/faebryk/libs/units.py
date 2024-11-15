# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

# re-exporting Quantity in-case we ever want to change it
from typing import Any, cast

from pint import Quantity as _Quantity  # noqa: F401
from pint import UndefinedUnitError, Unit, UnitRegistry  # noqa: F401
from pint.util import UnitsContainer as _UnitsContainer

from faebryk.libs.util import cast_assert

P = UnitRegistry()

UnitsContainer = _UnitsContainer | str | _Quantity | Unit
Quantity = P.Quantity
dimensionless = cast_assert(Unit, P.dimensionless)


def quantity(value: float | int, unit: UnitsContainer | Unit | Quantity) -> Quantity:
    return P.Quantity(value, unit)


class HasUnit:
    units: Unit

    @staticmethod
    def check(obj: Any) -> bool:
        return hasattr(obj, "units") or isinstance(obj, Unit)

    @staticmethod
    def get_units(obj: Any) -> Unit:
        assert HasUnit.check(obj)
        return obj.units

    @staticmethod
    def get_units_or_dimensionless(obj: Any) -> Unit:
        if isinstance(obj, Unit):
            return obj
        return obj.units if HasUnit.check(obj) else dimensionless


def to_si_str(
    value: Quantity | float | int,
    unit: UnitsContainer,
    num_decimals: int = 2,
) -> str:
    """
    Convert a float to a string with SI prefix and unit.
    """
    from faebryk.libs.util import round_str

    if isinstance(value, Quantity):
        compacted = value.to(unit).to_compact(cast(_UnitsContainer, unit))
        out = f"{compacted:.{num_decimals}f~#P}"
    else:
        out = f"{round_str(value, num_decimals)} {unit}"
    m, u = out.split(" ")
    if "." in m:
        int_, frac = m.split(".")
        clean_decimals = frac.rstrip("0")
        m = f"{int_}.{clean_decimals}" if clean_decimals else int_

    return f"{m}{u}"


def Scalar(value: float):
    return Quantity(value)
