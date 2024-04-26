"""
Work with expressions and ranged values.
"""

import collections.abc
from typing import Callable, Mapping, Optional, Type, Union

import pint
from attrs import define, frozen
from pint.facets.plain import PlainUnit

_UNITLESS = pint.Unit("")


def _custom_float_format(value, max_decimals: int):
    """
    Format the float to have up to max_decimals places, but fewer if there's no more precision.
    """
    # Format with fixed-point notation, up to max_decimals
    formatted = f"{value:.{max_decimals}f}"
    # Remove trailing zeros and the decimal point if not needed
    return formatted.rstrip("0").rstrip(".")


def _best_units(qty_a: pint.Quantity, qty_b: pint.Quantity) -> PlainUnit:
    """Return the best unit for the two quantities."""
    if str(qty_a.to(qty_b.units).magnitude) < str(qty_b.to(qty_a.units).magnitude):
        return qty_a.units
    return qty_b.units


_favourable_units = [
    pint.Unit("V"),
    pint.Unit("ohm"),
    pint.Unit("A"),
    pint.Unit("W"),
    pint.Unit("Hz"),
    pint.Unit("F"),
    pint.Unit("H"),
]


def _favourable_unit(unit: PlainUnit) -> PlainUnit:
    """Return the most favourable unit for the given unit."""
    for fav_unit in _favourable_units:
        if unit.is_compatible_with(fav_unit):
            return fav_unit
    return unit


class RangedValue:
    """
    Let's get physical!

    Ranged values are designed to represent a range of physical values, such as
    a voltage or current, including tolerances.
    """

    def __init__(
        self,
        val_a: Union[float, int, pint.Quantity],
        val_b: Optional[Union[float, int, pint.Quantity]] = None,
        unit: Optional[str | PlainUnit | pint.Unit] = None,
        pretty_unit: Optional[str] = None,
    ):
        # This is a bit of a hack, but simplifies upstream code marginally
        if val_b is None:
            val_b = val_a

        # If we're given a unit, use it. Otherwise, try to infer the unit from the inputs.
        if unit:
            self.unit = pint.Unit(unit)
        elif isinstance(val_a, pint.Quantity) and isinstance(val_b, pint.Quantity):
            self.unit = _best_units(val_a, val_b)
        elif isinstance(val_a, pint.Quantity):
            self.unit = val_a.units
        elif isinstance(val_a, pint.Quantity):
            self.unit = val_b.units
        else:
            self.unit = _UNITLESS

        # If the inputs are pint Quantities, convert them to the same unit
        if isinstance(val_a, pint.Quantity):
            val_a_mag = val_a.to(self.unit).magnitude
        else:
            val_a_mag = val_a

        if isinstance(val_b, pint.Quantity):
            val_b_mag = val_b.to(self.unit).magnitude
        else:
            val_b_mag = val_b

        assert isinstance(val_a_mag, (float, int))
        assert isinstance(val_b_mag, (float, int))

        # Make the noise
        self.pretty_unit = pretty_unit
        self.min_val = min(val_a_mag, val_b_mag)
        self.max_val = max(val_a_mag, val_b_mag)

    @property
    def best_usr_unit(self) -> str:
        """Return a pretty string representation of the unit."""
        if self.pretty_unit:
            return self.pretty_unit
        return str(self.unit)

    def to(self, unit: str | PlainUnit | pint.Unit) -> "RangedValue":
        """Return a new RangedValue in the given unit."""
        return RangedValue(
            self.min_qty,
            self.max_qty,
            unit
        )

    def to_compact(self) -> "RangedValue":
        """Return a new RangedValue in the most compact unit."""
        return RangedValue(
            # FIXME: still shit
            self.min_qty.to_compact(),
            self.max_qty.to_compact(),
        )

    def pretty_str(
        self,
        max_decimals: Optional[int] = 2,
        unit: Optional[pint.Unit] = None
    ) -> str:
        """Return a pretty string representation of the RangedValue."""
        if unit is not None:
            val = self.to(unit)
        else:
            val = self.to(_favourable_unit(self.unit)).to_compact()

        if max_decimals is None:
            nom = str(val.nominal)
            if val.tolerance != 0:
                nom += f' +/- {str(val.tolerance)}'
                if val.tolerance_pct is not None:
                    nom += f' ({str(val.tolerance_pct)}%)'
        else:
            nom = _custom_float_format(val.nominal, max_decimals)
            if val.tolerance != 0:
                nom += f' +/- {_custom_float_format(val.tolerance, max_decimals)}'
                if val.tolerance_pct is not None:
                    nom += f' ({_custom_float_format(val.tolerance_pct, max_decimals)}%)'

        return f"{nom} {val.best_usr_unit}"

    def __str__(self) -> str:
        return self.pretty_str()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.min_val}, {self.max_val}, '{self.unit}')"
        )

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

    @classmethod
    def _ensure(cls, thing) -> "RangedValue":
        if isinstance(thing, RangedValue):
            return thing
        return cls(thing, thing, _UNITLESS)

    def __mul__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        other = self._ensure(other)

        new_values = [
            self.min_qty * other.min_qty,
            self.min_qty * other.max_qty,
            self.max_qty * other.min_qty,
            self.max_qty * other.max_qty,
        ]

        return self.__class__(
            min(new_values),
            max(new_values),
        )

    def __rmul__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        return self.__mul__(other)

    def __pow__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        if isinstance(other, RangedValue):
            if not (other.unit.dimensionless and other.min_val == other.max_val):
                raise ValueError("Exponent must be a constant valueless quantity")
            other = other.min_val

        return self.__class__(self.min_qty**other, self.max_qty**other)

    @classmethod
    def _do_truediv(
        cls,
        numerator: Union["RangedValue", float, int],
        denominator: Union["RangedValue", float, int],
    ) -> "RangedValue":
        numerator = cls._ensure(numerator)
        denominator = cls._ensure(denominator)

        new_values = [
            numerator.min_qty / denominator.min_qty,
            numerator.min_qty / denominator.max_qty,
            numerator.max_qty / denominator.min_qty,
            numerator.max_qty / denominator.max_qty,
        ]

        return cls(
            min(new_values),
            max(new_values),
        )

    def __truediv__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        return self._do_truediv(self, other)

    def __rtruediv__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        return self._do_truediv(other, self)

    def __add__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        other = self._ensure(other)

        return self.__class__(
            self.min_qty + other.min_qty,
            self.max_qty + other.max_qty,
        )

    def __radd__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        return self.__add__(other)

    def __sub__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        other = self._ensure(other)

        return self.__class__(
            self.min_qty - other.max_qty,
            self.max_qty - other.min_qty,
        )

    def __rsub__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        return self.__sub__(other)

    def __neg__(self) -> "RangedValue":
        return self.__class__(
            -self.max_qty, -self.min_qty, self.unit, self.pretty_unit
        )

    def within(self, other: Union["RangedValue", float, int]) -> bool:
        """Check that this RangedValue completely falls within another."""
        if not isinstance(other, RangedValue):
            if not self.unit.dimensionless:
                raise ValueError(
                    "Can only compare RangedValue to a dimensionless quantity"
                )
            return self.min_val == self.max_val == other
        return self.min_qty >= other.min_qty and other.max_qty >= self.max_qty

    # NOTE: we use the < and > operators interchangeably with the <= and >= operators
    def __lt__(self, other: Union["RangedValue", float, int]) -> bool:
        other = self._ensure(other)
        return self.max_qty <= other.min_qty

    def __gt__(self, other: Union["RangedValue", float, int]) -> bool:
        other = self._ensure(other)
        return self.min_qty >= other.max_qty

    def __eq__(self, other: object) -> bool:
        # NOTE: realistically this is only useful for testing
        if isinstance(other, RangedValue):
            return self.min_qty == other.min_qty and self.max_qty == other.max_qty
        if self.min_val == self.max_val == other and self.unit.dimensionless:
            return True
        return False

    def __req__(self, other: Union["RangedValue", float, int]) -> bool:
        return self.__eq__(other)


NumericishTypes = Union["Expression", RangedValue, float, int, "Symbol"]


@frozen
class Symbol:
    """Represent a symbol."""

    key: collections.abc.Hashable

    def __call__(self, context: Mapping) -> RangedValue:
        """Return the value of the symbol."""
        thing = context[self.key]
        if callable(thing):
            return thing(context)
        return thing


# TODO: figure out how to pretty print these with the symbols etc...
@define
class Expression:
    """Represent an expression."""

    symbols: set[Symbol]
    lambda_: Callable[[Mapping[str, NumericishTypes]], RangedValue]

    @classmethod
    def from_expr(cls, expr: "Expression") -> "Expression":
        """Create an expression from another expression."""
        return cls(symbols=expr.symbols, lambda_=expr.lambda_)

    @classmethod
    def from_numericish(cls, thing: NumericishTypes) -> "Expression":
        """Create an expression from a numericish thing."""
        if isinstance(thing, Expression):
            return cls.from_expr(thing)
        if isinstance(thing, RangedValue):
            return cls(symbols=set(), lambda_=lambda context: thing)
        if isinstance(thing, Symbol):
            return cls(symbols={thing}, lambda_=thing)
        return cls(symbols=set(), lambda_=lambda context: RangedValue(thing, thing))

    def __call__(self, context: Mapping[str, NumericishTypes]) -> RangedValue:
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
    if not callable(lhs) and not callable(rhs):
        # in this case we can just do the operation now, skip ahead and merry christmas
        return operator(lhs, rhs)

    # if we're here, we need to create an expression
    symbols = _get_symbols(lhs) | _get_symbols(rhs)
    if callable(lhs) and callable(rhs):

        def lambda_(context):
            return operator(lhs(context), rhs(context))

    elif callable(lhs):

        def lambda_(context):
            return operator(lhs(context), rhs)

    else:

        def lambda_(context):
            return operator(lhs, rhs(context))

    return deffering_type(symbols=symbols, lambda_=lambda_)
