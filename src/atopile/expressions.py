"""
Work with expressions and ranged values.
"""

import collections.abc
from numbers import Number
from typing import Any, Callable, Mapping, Optional, Type, Union

import pint
from attrs import define


def _custom_float_format(value, max_decimals: int):
    """
    Format the float to have up to max_decimals places, but fewer if there's no more precision.
    """
    # Format with fixed-point notation, up to max_decimals
    formatted = f"{value:.{max_decimals}f}"
    # Remove trailing zeros and the decimal point if not needed
    return formatted.rstrip("0").rstrip(".")


class RangedValue:
    """
    Let's get physical!

    Ranged values are designed to represent a range of physical values, such as
    a voltage or current, including tolerances.
    """

    def __init__(
        self,
        val_a: Union[Number, pint.Quantity],
        val_b: Union[Number, pint.Quantity],
        unit: Optional[str | pint.Unit] = None,
        pretty_unit: Optional[str] = None,
    ):
        if unit:
            if isinstance(unit, pint.Unit):
                self.unit = unit
            else:
                self.unit = pint.Unit(unit)
        elif isinstance(val_a, pint.Quantity):
            # TODO: look into warnings here
            self.unit = val_a.units
        elif isinstance(val_a, pint.Quantity):
            self.unit = val_b.units
        else:
            self.unit = pint.Unit("")

        if isinstance(val_a, pint.Quantity):
            val_a_mag = val_a.to(self.unit).magnitude
        else:
            val_a_mag = val_a

        if isinstance(val_b, pint.Quantity):
            val_b_mag = val_b.to(self.unit).magnitude
        else:
            val_b_mag = val_b

        self._pretty_unit = pretty_unit
        self.min_val = min(val_a_mag, val_b_mag)
        self.max_val = max(val_a_mag, val_b_mag)

    @property
    def pretty_unit(self) -> str:
        """Return a pretty string representation of the unit."""
        if self._pretty_unit:
            return self._pretty_unit
        return str(self.unit)

    def __str__(self) -> str:
        return self.pretty_str()

    def pretty_str(self, max_decimals: int = 2) -> str:
        """Return a pretty string representation of the RangedValue."""
        nom = _custom_float_format(self.nominal, max_decimals)
        tol = _custom_float_format(self.tolerance, max_decimals)
        return f"{nom} +/- {tol} {self.pretty_unit}"

    @property
    def nominal(self) -> float:
        """Return the nominal value of the RangedValue."""
        return (self.min_val + self.max_val) / 2

    @property
    def tolerance(self) -> float:
        """Return the tolerance of the RangedValue."""
        return (self.max_val - self.min_val) / 2

    @property
    def tolerance_pct(self) -> Optional[float]:
        """Return the tolerance as a percentage of the nominal value."""
        if self.nominal == 0:
            return None
        return self.tolerance / self.nominal * 100

    def to_dict(self) -> dict:
        """Convert the Physical instance to a dictionary."""
        return {
            "unit": str(self.unit),
            "min_val": self.min_val,
            "max_val": self.max_val,
            # TODO: remove these - we shouldn't be duplicating this kind of information
            "nominal": self.nominal,
            "tolerance": self.tolerance,
            "tolerance_pct": self.tolerance_pct,
        }

    @property
    def min_qty(self) -> pint.Quantity:
        """Return the minimum of self as a pint Quantity."""
        return self.unit * self.min_val

    @property
    def max_qty(self) -> pint.Quantity:
        """Return the maximum of self as a pint Quantity."""
        return self.unit * self.max_val

    def __mul__(self, other: Union["RangedValue", Number]) -> "RangedValue":
        if not isinstance(other, RangedValue):
            other = RangedValue(other, other, self.unit)

        new_values = [
            self.min_qty * other.min_qty,
            self.min_qty * other.max_qty,
            self.max_qty * other.min_qty,
            self.max_qty * other.max_qty,
        ]

        return RangedValue(
            min(new_values),
            max(new_values),
        )

    def __rmul__(self, other: Union["RangedValue", Number]) -> "RangedValue":
        return self.__mul__(other)

    def __pow__(self, other: Union["RangedValue", Number]) -> "RangedValue":
        if isinstance(other, RangedValue):
            if not (other.min_qty == other.max_qty and other.unit.dimensionless):
                raise ValueError("Exponent must be a constant valueless quantity")
            other = other.min_qty
        return RangedValue(self.min_qty**other, self.max_val**other)

    @classmethod
    def _do_truediv(
        cls, numerator: Union["RangedValue", Number], denominator: Union["RangedValue", Number]
    ) -> "RangedValue":
        if not isinstance(numerator, RangedValue) and not isinstance(
            denominator, RangedValue
        ):
            raise TypeError("a or b must be RangedValue")

        if not isinstance(numerator, RangedValue):
            numerator = RangedValue(numerator, numerator, denominator.unit)
        elif not isinstance(denominator, RangedValue):
            denominator = RangedValue(denominator, denominator, numerator.unit)

        new_values = [
            numerator.min_qty / denominator.min_qty,
            numerator.min_qty / denominator.max_qty,
            numerator.max_qty / denominator.min_qty,
            numerator.max_qty / denominator.max_qty,
        ]

        return RangedValue(
            min(new_values),
            max(new_values),
        )

    def __truediv__(self, other: Union["RangedValue", Number]) -> "RangedValue":
        return self._do_truediv(self, other)

    def __rtruediv__(self, other: Union["RangedValue", Number]) -> "RangedValue":
        return self._do_truediv(other, self)

    def __add__(self, other: Union["RangedValue", Number]) -> "RangedValue":
        if not isinstance(other, RangedValue):
            other = RangedValue(other, other, self.unit)

        return RangedValue(
            self.min_qty + other.min_qty,
            self.max_qty + other.max_qty,
        )

    def __radd__(self, other: Union["RangedValue", Number]) -> "RangedValue":
        return self.__add__(other)

    def __sub__(self, other: Union["RangedValue", Number]) -> "RangedValue":
        if not isinstance(other, RangedValue):
            other = RangedValue(other, other, self.unit)

        return RangedValue(
            self.min_qty - other.max_qty,
            self.max_qty - other.min_qty,
        )

    def __rsub__(self, other: Union["RangedValue", Number]) -> "RangedValue":
        return self.__sub__(other)

    def __neg__(self) -> "RangedValue":
        return RangedValue(-self.max_qty, -self.min_qty)

    def within(self, other: "RangedValue") -> bool:
        """Check that this RangedValue completely falls within another."""
        return self.min_qty >= other.min_qty and other.max_qty >= self.max_qty

    # NOTE: we use the < and > operators interchangeably with the <= and >= operators
    def __lt__(self, other: "RangedValue") -> bool:
        return self.max_qty <= other.min_qty

    def __gt__(self, other: "RangedValue") -> bool:
        return self.min_qty >= other.max_qty

    def __eq__(self, other: Union["RangedValue", Number]) -> bool:
        # NOTE: realistically this is only useful for testing
        if not isinstance(other, RangedValue):
            other = RangedValue(other, other, self.unit)
        return self.min_qty == other.min_qty and self.max_qty == other.max_qty

    def __req__(self, other: Union["RangedValue", Number]) -> bool:
        return self.__eq__(other)


NumericishTypes = Union["Expression", RangedValue, Number, "Symbol"]


@define
class Symbol:
    """Represent a symbol."""
    addr: collections.abc.Hashable

    def __call__(self, context: Mapping) -> Any:
        """Return the value of the symbol."""
        return context[self.addr]


@define
class Expression:
    """Represent an expression."""

    symbols: set[Symbol]
    lambda_: Callable[[Mapping[str, NumericishTypes]], Any]

    def __call__(self, context: Mapping[str, NumericishTypes]) -> Any:
        return self.lambda_(context)


def _get_symbols(thing: NumericishTypes) -> set[Symbol]:
    if isinstance(thing, Expression):
        return thing.symbols
    elif isinstance(thing, Symbol):
        return {thing}
    else:
        return set()


def defer_operation_factory(
    lhs: NumericishTypes,
    operator: Callable,
    rhs: NumericishTypes,
    deffering_type: Type = Expression,
) -> NumericishTypes:
    """Create a deferred operation, using deffering_type as the base for teh callable."""
    if not isinstance(lhs, collections.abc.Callable) and not isinstance(
        rhs, collections.abc.Callable
    ):
        # in this case we can just do the operation now, skip ahead and merry christmas
        return operator(lhs, rhs)

    # if we're here, we need to create an expression
    symbols = _get_symbols(lhs) | _get_symbols(rhs)
    if isinstance(lhs, collections.abc.Callable) and isinstance(
        rhs, collections.abc.Callable
    ):
        def lambda_(context):
            return operator(lhs(context), rhs(context))

    elif isinstance(lhs, collections.abc.Callable):
        def lambda_(context):
            return operator(lhs(context), rhs)

    else:
        def lambda_(context):
            return operator(lhs, rhs(context))

    return deffering_type(symbols=symbols, lambda_=lambda_)
