"""
Work with expressions and ranged values.
"""

import collections.abc
from collections import ChainMap
from typing import Callable, Mapping, Optional, Union

import pint
from antlr4 import ParserRuleContext
from attrs import define, frozen
from pint.facets.plain import PlainUnit

from atopile import address, errors

_UNITLESS = pint.Unit("")


def _custom_float_format(value, max_decimals: int):
    """
    Format the float to have up to max_decimals places, but fewer if there's no more precision.
    """
    # Format with fixed-point notation, up to max_decimals
    formatted = f"{value:.{max_decimals}f}"
    # Remove trailing zeros and the decimal point if not needed
    return formatted.rstrip("0").rstrip(".")


_multiplier_map = {
    "femto": "f",
    "pico": "p",
    "nano": "n",
    "micro": "u",
    "milli": "m",
    "": "",
    "kilo": "k",
    "mega": "M",
    "giga": "G",
    "tera": "T",
}


_pretty_unit_map = {
    "": "",  # Dimensionless is desirable too
    "volt": "V",
    "ohm": "Ω",
    "ampere": "A",
    "watt": "W",
    "hertz": "Hz",
    "farad": "F",
    "henry": "H",
    "second": "s",
}


pretty_unit_map = {lm + lu: sm + su for lm, sm in _multiplier_map.items() for lu, su in  _pretty_unit_map.items()}
favorite_units_map = {pint.Unit(k).dimensionality: pint.Unit(k) for k in _pretty_unit_map}


def _convert_to_favorite_unit(qty: pint.Quantity) -> pint.Quantity:
    """Convert the quantity to the favorite unit for its dimensionality."""
    # If there's a favorite unit for this dimensionality, use it
    if qty.units.dimensionality in favorite_units_map:
        qty = qty.to(favorite_units_map[qty.units.dimensionality])

    # Compact the units to standardise them
    qty = qty.to_compact()

    return qty


def _best_units(qty_a: pint.Quantity, qty_b: pint.Quantity) -> PlainUnit:
    """Return the best unit for the two quantities."""
    a_fav = _convert_to_favorite_unit(qty_a)
    b_fav = _convert_to_favorite_unit(qty_b)

    # If converting b to a's units results in a shorter representation, use a's units
    # Otherwise, use b's units
    if len(str(qty_b.to(a_fav.units).magnitude)) < len(str(qty_a.to(b_fav.units).magnitude)):
        return a_fav.units
    return b_fav.units


def pretty_unit(qty: pint.Quantity) -> tuple[float, str]:
    """Return the most favorable magnitude and unit for the given quantity."""
    if qty.units.dimensionless:
        return qty.magnitude, ""

    qty = _convert_to_favorite_unit(qty)

    # Convert the units to a pretty string
    units = str(qty.units)
    pretty_unit = pretty_unit_map.get(units, units)
    return qty.magnitude, pretty_unit


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
        str_rep: Optional[str] = None,
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
        self.str_rep = str_rep
        self.min_val = min(val_a_mag, val_b_mag)
        self.max_val = max(val_a_mag, val_b_mag)

    def to(self, unit: str | PlainUnit | pint.Unit) -> "RangedValue":
        """Return a new RangedValue in the given unit."""
        return RangedValue(self.min_qty, self.max_qty, unit)

    def pretty_str(
        self,
        max_decimals: Optional[int] = 2,
        format_: Optional[str] = None,
    ) -> str:
        """Return a pretty string representation of the RangedValue."""
        def _f(val: float):
            if max_decimals is None:
                return str(val)
            return _custom_float_format(val, max_decimals)

        if self.str_rep and format_ is None:
            return self.str_rep

        # Single-ended
        if self.tolerance == 0 or (
            self.tolerance_pct and
            self.tolerance_pct * 1e4 < pow(10, -max_decimals)
        ):
            nom, unit = pretty_unit(self.nominal * self.unit)
            return f"{_f(nom)}{unit}"

        # Bound values
        if (self.tolerance_pct and self.tolerance_pct > 20) or format_ == "bound":
            min_val, min_unit = pretty_unit(self.min_qty)
            max_val, max_unit = pretty_unit(self.max_qty)

            if min_unit == max_unit or min_val == 0 or max_val == 0:
                return f"{_f(min_val)} to {_f(max_val)} {max_unit}"
            return f"{_f(min_val)}{min_unit} to {_f(max_val)}{max_unit}"

        # Bilateral values
        nom, unit = pretty_unit(self.nominal * self.unit)
        tol, tol_unit = pretty_unit(self.tolerance * self.unit)

        if nom == 0:
            return f"± {_f(tol)}{tol_unit}"
        if unit == tol_unit:
            return f"{_f(nom)} ± {_f(tol)} {unit}"
        return f"{_f(nom)}{unit} ± {_f(tol)}{tol_unit}"

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
        return abs(self.tolerance / self.nominal * 100)

    def to_dict(self) -> dict:
        """Convert the Physical instance to a dictionary."""
        min_qty = _convert_to_favorite_unit(self.min_qty)
        multiplier = min_qty.magnitude / self.min_val
        return {
            "unit": str(min_qty.units),
            "min_val": min_qty.magnitude,
            "max_val": self.max_val * multiplier,
            # TODO: remove these - we shouldn't be duplicating this kind of information
            "nominal": self.nominal * multiplier,
            "tolerance": self.tolerance * multiplier,
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
        return self.__class__(-self.max_qty, -self.min_qty, self.unit)

    def within(self, other: Union["RangedValue", float, int]) -> bool:
        """Check that this RangedValue completely falls within another."""
        if not isinstance(other, RangedValue):
            if not self.unit.dimensionless:
                raise ValueError(
                    "Can only compare RangedValue to a dimensionless quantity"
                )
            return self.min_val == self.max_val == other
        return self.min_qty >= other.min_qty and other.max_qty >= self.max_qty

    def __lt__(self, other: Union["RangedValue", float, int]) -> bool:
        other = self._ensure(other)
        return self.max_qty < other.min_qty

    def __gt__(self, other: Union["RangedValue", float, int]) -> bool:
        other = self._ensure(other)
        return self.min_qty > other.max_qty

    def __le__(self, other: Union["RangedValue", float, int]) -> bool:
        other = self._ensure(other)
        return self.max_qty <= other.min_qty

    def __ge__(self, other: Union["RangedValue", float, int]) -> bool:
        other = self._ensure(other)
        return self.min_qty >= other.max_qty

    def __eq__(self, other: object) -> bool:
        # NOTE: realistically this is only useful for testing
        if isinstance(other, RangedValue):
            return self.min_qty == other.min_qty and self.max_qty == other.max_qty

        # NOTE: this doesn't work for farenheit or kelvin, but everything else is okay
        if self.min_val == self.max_val == other and (
            self.unit.dimensionless or other == 0
        ):
            return True
        return False

    def __req__(self, other: Union["RangedValue", float, int]) -> bool:
        return self.__eq__(other)

    def __or__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        other = self._ensure(other)

        # make sure there's some overlap
        if self.max_qty < other.min_qty or other.max_qty < self.min_qty:
            raise errors.AtoValueError(f"Ranges ({self}, {other}) do not overlap")

        return self.__class__(
            min(self.min_qty, other.min_qty),
            max(self.max_qty, other.max_qty),
        )

    def __ror__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        return self.__or__(other)

    def __and__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        other = self._ensure(other)

        # make sure there's some overlap
        if self.max_qty < other.min_qty or other.max_qty < self.min_qty:
            raise errors.AtoValueError(f"Ranges ({self}, {other}) do not overlap")

        return self.__class__(
            max(self.min_qty, other.min_qty),
            min(self.max_qty, other.max_qty),
        )

    def __rand__(self, other: Union["RangedValue", float, int]) -> "RangedValue":
        return self.__and__(other)

    def min(self) -> "RangedValue":
        """Return a new RangedValue with the minimum value."""
        return self.__class__(self.min_qty, self.min_qty)

    def max(self) -> "RangedValue":
        """Return a new RangedValue with the maximum value."""
        return self.__class__(self.max_qty, self.max_qty)


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
    src_ctx: ParserRuleContext | None = None

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

    def substitute(
        self, substitutions: Mapping[str | Symbol, NumericishTypes]
    ) -> NumericishTypes:
        """Return a new expression with all the symbols substituted."""
        # Do a little data checky check
        if not all(symbol in self.symbols for symbol in substitutions):
            raise ValueError("Substitution contains symbols not in the expression")

        # Sort the substitutions into constants and expressions
        constants: Mapping[str, int | float | RangedValue] = {}
        constants_symbols = set()
        callables: Mapping[str, Expression | Symbol] = {}
        for symbol, value in substitutions.items():
            # FIXME: this is here because the context and expressions
            # hold reference to the values of attributes differently
            key = symbol.key if hasattr(symbol, "key") else symbol
            if callable(value):
                callables[key] = value
            else:
                constants[key] = value
                constants_symbols.add(symbol)

        # Create a new lambda function with the substitutions
        def _new_lambda(context):
            assert not (
                set(context) & set(constants)
            ), "Constants are being overwritten"
            new_context = {**context, **constants}
            for symbol, func in callables.items():
                new_context[symbol] = func(new_context)
            return self.lambda_(new_context)

        # Figure out what new symbols are required for this expression
        # Remove the constants we've substituted in, and add any new
        # symbols from the new expressions
        callables_symbols = set()
        for expr in callables.values():
            if isinstance(expr, Symbol):
                callables_symbols.add(expr)
                continue
            for symbol in expr.symbols:
                callables_symbols.add(symbol)
        new_symbols = self.symbols - set(substitutions.keys()) | callables_symbols

        # In the case we've completely substituted all the symbols
        # we can just return a new constant
        if not new_symbols:
            return _new_lambda({})

        return Expression(symbols=new_symbols, lambda_=_new_lambda)


def _get_symbols(thing: NumericishTypes) -> set[Symbol]:
    if isinstance(thing, Expression):
        return thing.symbols
    elif isinstance(thing, Symbol):
        return {thing}
    else:
        return set()


def defer_operation_factory(
    func: Callable,
    *args: NumericishTypes,
    src_ctx: ParserRuleContext | None = None,
) -> NumericishTypes:
    """Create a deferred operation, using deffering_type as the base for the callable."""
    if not any(map(callable, args)):
        # in this case we can just do the operation now, skip ahead and merry christmas
        try:
            return func(*args)
        except errors.AtoError as e:
            if src_ctx:
                e.set_src_from_ctx(src_ctx)
            raise

    # if we're here, we need to create an expression
    symbols = set.union(*map(_get_symbols, args))

    def _make_callable(not_callable):
        def _now_its_callable(_):
            return not_callable
        return _now_its_callable

    partials = [arg if callable(arg) else _make_callable(arg) for arg in args]

    def lambda_(context):
        try:
            return func(*(arg(context) for arg in partials))
        except errors.AtoError as e:
            if src_ctx:
                e.set_src_from_ctx(src_ctx)
            raise

    return Expression(symbols=symbols, lambda_=lambda_)


def simplify_expression_pool(
    pool: Mapping[str, NumericishTypes]
) -> Mapping[str, NumericishTypes]:
    """
    Simplify an expression, based on additional context we can give it.

    This is split from simplify_expression_pool, because we also need
    to simplify expressions that don't have symbols pointing to them.
    This is the case for the expressions in assertions, for example.

    # Usage

    The "pool" should contain a mapping of addresses to their assigned
    values. If something's declared, but not defined (eg. "A") in the
    below example, it should not be in the pool.

    # Problem Statement

    Take the example:
    A: int
    B = A + 1
    C = B + 2
    D = 3
    E = D + 4

    "A" remains a symbol, but we need to realise
    that it's a symbol, implying it's a strong, independent
    variable (who don't need no man)

    "B" is a simple expression, which we can't simplify,
    because it's already in terms of nothing other than constants
    and symbols.

    "C" is a more complex expression, so we can simplify it
    to "A + 3" or "(A + 1) + 2" for all I care.

    "D" is a constant, so it can't be simplified.

    "E" is an expression completely in terms of constants
    and defined symbols, so it can be simplified to "7".

    In summary:
    - Expressions or Symbols that are in terms of other
        expressions can be simplified
    - Expressions that are completely in terms of constants or
        defined symbols can be simplified
    - Nothing else can be simplified:
        - Constants and unassigned Symbols are independent, and
            can't be simplified
        - Expressions that are completely in independent terms
            can't be simplified further
    """

    # Expressions which we haven't got to yet
    touched = set()
    simplified = {}
    context = ChainMap(simplified, pool)

    def _visit(key: str, stack: list) -> NumericishTypes:
        if key in stack:
            loop = [key] + stack[:stack.index(key) + 1]
            loop = [address.get_instance_section(addr) for addr in loop]
            raise errors.AtoError(
                f"{' references '.join(loop)}",
                title="Circular dependency detected"
            )

        if key in touched:
            return context[key]  # no wakkas

        # Get the value from the pool
        value = context[key]

        # If this is something simple, just return it in the first place
        if not callable(value):
            touched.add(key)
            return value

        # If this thing points at something else, we can simplify it
        # For expressions, we find all the keys we have access to, and
        # go evaluate them first, before subbing them in
        if isinstance(value, Expression):
            simplified[key] = value.substitute(
                {
                    s: _visit(s.key, stack + [key])
                    for s in value.symbols
                    if s.key in pool
                }
            )
            touched.add(key)
            return simplified[key]

        # If it's a symbol, we simplify it by sticking the value in the
        # address there used to be a symbol instead
        elif isinstance(value, Symbol):
            if value.key in pool:
                simplified[key] = _visit(value.key, stack + [key])
                touched.add(key)
                return simplified[key]

            simplified[key] = value
            touched.add(key)
            return value

        raise ValueError("Unknown value type")

    # Iterate over the pool, simplifying as we go
    for key in pool:
        _visit(key, [])

    return simplified


def simplify_expression(
    expression: Expression,
    context: Mapping[str, NumericishTypes],
) -> Expression:
    """
    Simplify a single expression.
    This will only work if the context is already in its simplest forms.
    """
    substitutions = {symbol: context[symbol.key] for symbol in expression.symbols if symbol.key in context}
    expression = expression.substitute(substitutions)
    return expression
