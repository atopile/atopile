# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

# re-exporting Quantity in-case we ever want to change it
from typing import Any, Iterable, Sequence, cast

from pint import Quantity as _Quantity  # noqa: F401
from pint import (  # noqa: F401
    UndefinedUnitError,
    Unit,  # It's a trap. Unit here is in the wrong registry. DO NOT CONSTRUCT
    UnitRegistry,
)
from pint._typing import Scalar as _Scalar  # noqa: F401
from pint.util import UnitsContainer as _UnitsContainer

from faebryk.libs.exceptions import UserException
from faebryk.libs.util import cast_assert

P = UnitRegistry()

UnitsContainer = _UnitsContainer | str | _Quantity | Unit
Quantity = P.Quantity
dimensionless = cast_assert(Unit, P.dimensionless)

# int, float, Decimal, Fraction, np.number
type Number = _Scalar
# int, float, Decimal, Fraction, Quantity, Unit
type Scalar_ = Number | _Quantity | Unit

assert issubclass(Quantity, _Quantity)


def quantity(
    value: Number | str | Quantity, unit: UnitsContainer | Quantity | None = None
) -> Quantity:
    if isinstance(value, Quantity) and unit is not None:
        value = value.to_base_units().m
    return P.Quantity(value, unit)  # type: ignore


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


def to_si(
    value: Quantity | float | int,
    unit: UnitsContainer,
    num_decimals: int = 2,
):
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

    return m, u


def to_si_str(
    value: Quantity | float | int,
    unit: UnitsContainer,
    num_decimals: int = 2,
) -> str:
    m, u = to_si(value, unit, num_decimals)
    return f"{m}{u}"


def format_time(seconds: float) -> str:
    return to_si_str(seconds, "s")


def Scalar(value: float):
    return Quantity(value)


class UnitCompatibilityError(UserException):
    """
    Incompatible units.
    """

    def __init__(self, *args, incompatible_items: Iterable, **kwargs):
        super().__init__(*args, **kwargs)
        self.incompatible_items = list(incompatible_items)


def assert_compatible_units(items: Sequence) -> Unit:
    if not items:
        raise ValueError("At least one item is required")

    units = [HasUnit.get_units_or_dimensionless(item) for item in items]
    u0 = units[0]

    if len(items) == 1:
        return u0

    if not all(u0.is_compatible_with(u) for u in units[1:]):
        raise UnitCompatibilityError(
            "Operands have incompatible units:\n"
            + "\n".join(
                f"`{item.__repr__()}` ({units[i]})" for i, item in enumerate(items)
            ),
            incompatible_items=items,
        )

    return u0
