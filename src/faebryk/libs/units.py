# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

# re-exporting Quantity in-case we ever want to change it
from pint import Quantity as _Quantity  # noqa: F401
from pint import UndefinedUnitError, Unit, UnitRegistry  # noqa: F401
from pint.util import UnitsContainer  # noqa: F401

P = UnitRegistry()

Quantity = P.Quantity


def to_si_str(
    value: Quantity | float | int,
    unit: str | UnitsContainer,
    num_decimals: int = 2,
) -> str:
    """
    Convert a float to a string with SI prefix and unit.
    """
    from faebryk.libs.util import round_str

    if isinstance(value, Quantity):
        out = f"{value.to(unit).to_compact(unit):.{num_decimals}f~#P}"
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
