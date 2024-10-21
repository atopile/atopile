# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from collections.abc import Generator, Iterable
from typing import Any, Protocol, TypeVar, cast

from faebryk.libs.units import HasUnit, Quantity, Unit, dimensionless

# Protocols ----------------------------------------------------------------------------


class P_Set[T](Protocol):
    def is_empty(self) -> bool: ...

    def __contains__(self, item: T) -> bool: ...


class P_UnitSet[T](P_Set[T], Protocol):
    units: Unit


# --------------------------------------------------------------------------------------

# Types --------------------------------------------------------------------------------

NumericT = TypeVar("NumericT", int, float, contravariant=False, covariant=False)
QuantityT = TypeVar(
    "QuantityT", int, float, Quantity, contravariant=False, covariant=False
)


# --------------------------------------------------------------------------------------

# Helpers ------------------------------------------------------------------------------


def base_units(units: Unit) -> Unit:
    return cast(Unit, Quantity(1, units).to_base_units().units)


# --------------------------------------------------------------------------------------
# Generic ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class PlainSet[U](P_Set[U]):
    def __init__(self, *elements: U):
        self.elements = set(elements)

    def is_empty(self) -> bool:
        return len(self.elements) == 0

    def __contains__(self, item: U) -> bool:
        return item in self.elements

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, PlainSet):
            return False
        return self.elements == value.elements

    def __hash__(self) -> int:
        return sum(hash(e) for e in self.elements)

    def __repr__(self) -> str:
        return f"PlainSet({', '.join(repr(e) for e in self.elements)})"


# Numeric ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class _N_Range(P_Set[NumericT]):
    def __init__(self, min: NumericT, max: NumericT):
        if not min <= max:
            raise ValueError("min must be less than or equal to max")
        self.min = min
        self.max = max

    def is_empty(self) -> bool:
        return False

    def min_elem(self) -> NumericT:
        return self.min

    def op_add_range(self, other: "_N_Range[NumericT]") -> "_N_Range[NumericT]":
        return _N_Range(self.min + other.min, self.max + other.max)

    def op_negate(self) -> "_N_Range[NumericT]":
        return _N_Range(-self.max, -self.min)

    def op_subtract_range(self, other: "_N_Range[NumericT]") -> "_N_Range[NumericT]":
        return self.op_add_range(other.op_negate())

    def op_mul_range(self, other: "_N_Range[NumericT]") -> "_N_Range[NumericT]":
        return _N_Range(
            min(
                self.min * other.min,
                self.min * other.max,
                self.max * other.min,
                self.max * other.max,
            ),
            max(
                self.min * other.min,
                self.min * other.max,
                self.max * other.min,
                self.max * other.max,
            ),
        )

    def op_invert(self) -> "_N_Ranges[float]":
        if self.min == 0 == self.max:
            return _N_Empty()
        if self.min < 0 < self.max:
            return _N_Ranges(
                _N_Range(float("-inf"), 1 / self.min),
                _N_Range(1 / self.max, float("inf")),
            )
        elif self.min < 0 == self.max:
            return _N_Ranges(_N_Range(float("-inf"), 1 / self.min))
        elif self.min == 0 < self.max:
            return _N_Ranges(_N_Range(1 / self.max, float("inf")))
        else:
            return _N_Ranges(_N_Range(1 / self.max, 1 / self.min))

    def op_div_range(
        self: "_N_Range[float]", other: "_N_Range[float]"
    ) -> "_N_Ranges[float]":
        return _N_Ranges(*(self.op_mul_range(o) for o in other.op_invert().ranges))

    def op_intersect_range(self, other: "_N_Range[NumericT]") -> "_N_Ranges[NumericT]":
        min_ = max(self.min, other.min)
        max_ = min(self.max, other.max)
        if min_ <= max_:
            return _N_Ranges(_N_Range(min_, max_))
        return _N_Empty()

    def maybe_merge_range(
        self, other: "_N_Range[NumericT]"
    ) -> list["_N_Range[NumericT]"]:
        is_left = self.min <= other.min
        left = self if is_left else other
        right = other if is_left else self
        if right.min in self:
            return [_N_Range(left.min, max(left.max, right.max))]
        return [left, right]

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, _N_Range):
            return False
        return self.min == other.min and self.max == other.max

    def __contains__(self, item: NumericT) -> bool:
        return self.min <= item <= self.max

    def __hash__(self) -> int:
        return hash((self.min, self.max))

    def __repr__(self) -> str:
        return f"_Range({self.min}, {self.max})"


def _N_Single(value: NumericT) -> _N_Range[NumericT]:
    return _N_Range(value, value)


class _N_Ranges(P_Set[NumericT]):
    def __init__(self, *ranges: _N_Range[NumericT] | "_N_Ranges[NumericT]"):
        def gen_flat_non_empty() -> Generator[_N_Range[NumericT]]:
            for r in ranges:
                if r.is_empty():
                    continue
                if isinstance(r, _N_Ranges):
                    yield from r.ranges
                else:
                    assert isinstance(r, _N_Range)
                    yield r

        non_empty_ranges = list(gen_flat_non_empty())
        sorted_ranges = sorted(non_empty_ranges, key=lambda e: e.min_elem())

        def gen_merge():
            last = None
            for range in sorted_ranges:
                if last is None:
                    last = range
                else:
                    *prefix, last = last.maybe_merge_range(range)
                    yield from prefix
            if last is not None:
                yield last

        self.ranges = list(gen_merge())

    def is_empty(self) -> bool:
        return len(self.ranges) == 0

    def min_elem(self) -> NumericT:
        if self.is_empty():
            raise ValueError("empty range cannot have min element")
        return self.ranges[0].min_elem()

    def op_add_ranges(self, other: "_N_Ranges[NumericT]") -> "_N_Ranges[NumericT]":
        return _N_Ranges(
            *(r.op_add_range(o) for r in self.ranges for o in other.ranges)
        )

    def op_negate(self) -> "_N_Ranges[NumericT]":
        return _N_Ranges(*(r.op_negate() for r in self.ranges))

    def op_subtract_ranges(self, other: "_N_Ranges[NumericT]") -> "_N_Ranges[NumericT]":
        return self.op_add_ranges(other.op_negate())

    def op_mul_ranges(self, other: "_N_Ranges[NumericT]") -> "_N_Ranges[NumericT]":
        return _N_Ranges(
            *(r.op_mul_range(o) for r in self.ranges for o in other.ranges)
        )

    def op_invert(self) -> "_N_Ranges[float]":
        return _N_Ranges(*(r.op_invert() for r in self.ranges))

    def op_div_ranges(
        self: "_N_Ranges[float]", other: "_N_Ranges[float]"
    ) -> "_N_Ranges[float]":
        return self.op_mul_ranges(other.op_invert())

    def __contains__(self, item: NumericT) -> bool:
        from bisect import bisect

        index = bisect(self.ranges, item, key=lambda r: r.min_elem())

        if index == 0:
            return False
        return item in self.ranges[index - 1]

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, _N_Ranges):
            return False
        if len(self.ranges) != len(value.ranges):
            return False
        for r1, r2 in zip(self.ranges, value.ranges):
            if r1 != r2:
                return False
        return True

    def __hash__(self) -> int:
        return hash(tuple(hash(r) for r in self.ranges))

    def __repr__(self) -> str:
        return f"_RangeUnion({', '.join(f"[{r.min}, {r.max}]" for r in self.ranges)})"


class _N_RangesIterable(_N_Ranges[NumericT], Iterable[_N_Range[NumericT]]):
    def __iter__(self) -> Generator[_N_Range[NumericT]]:
        yield from self.ranges


class _N_Singles(_N_Ranges[NumericT], Iterable[NumericT]):
    def __init__(self, *values: NumericT):
        super().__init__(*(_N_Single(v) for v in values))

    def __iter__(self) -> Generator[NumericT]:
        for r in self.ranges:
            yield r.min


def _N_Empty() -> _N_Ranges:
    return _N_Ranges()


# Units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Range(P_UnitSet[QuantityT]):
    def __init__(
        self,
        min: QuantityT | None = None,
        max: QuantityT | None = None,
        units: Unit | None = None,
    ):
        if min is None and max is None:
            raise ValueError("must provide at least one of min or max")

        min_unit = (
            None
            if min is None
            else min.units
            if isinstance(min, Quantity)
            else dimensionless
        )
        max_unit = (
            None
            if max is None
            else max.units
            if isinstance(max, Quantity)
            else dimensionless
        )
        if units and min_unit and not min_unit.is_compatible_with(units):
            raise ValueError("min incompatible with units")
        if units and max_unit and not max_unit.is_compatible_with(units):
            raise ValueError("max incompatible with units")
        if min_unit and max_unit and not min_unit.is_compatible_with(max_unit):
            raise ValueError("min and max must be compatible")
        self.units = units or min_unit or max_unit
        self.range_units = base_units(self.units)

        if isinstance(min, Quantity):
            num_min = min.to_base_units().magnitude
            if not (isinstance(num_min, float) or isinstance(num_min, int)):
                raise ValueError("min must be a float or int quantity")
        else:
            num_min = min

        if isinstance(max, Quantity):
            num_max = max.to_base_units().magnitude
            if not (isinstance(num_max, float) or isinstance(num_max, int)):
                raise ValueError("max must be a float or int quantity")
        else:
            num_max = max

        is_float = isinstance(num_min, float) or isinstance(num_max, float)
        if is_float:
            num_min = float(num_min) if num_min is not None else float("-inf")
            num_max = float(num_max) if num_max is not None else float("inf")
        else:
            assert isinstance(num_min, int) or isinstance(num_max, int)
            if num_min is None or num_max is None:
                raise ValueError("min and max must be provided for ints")

        self._range = _N_Range(num_min, num_max)

    @staticmethod
    def from_center(center: QuantityT, abs_tol: QuantityT) -> "Range[QuantityT]":
        left = center - abs_tol
        right = center + abs_tol
        return Range(left, right)

    @staticmethod
    def from_center_rel(center: QuantityT, rel_tol: float) -> "Range[QuantityT]":
        return Range(center - center * rel_tol, center + center * rel_tol)

    @staticmethod
    def _from_range(range: _N_Range[NumericT], units: Unit) -> "Range[QuantityT]":
        return Range(
            min=Quantity(range.min, base_units(units)),
            max=Quantity(range.max, base_units(units)),
            units=units,
        )

    def base_to_units(self, value: NumericT) -> Quantity:
        return Quantity(value, self.range_units).to(self.units)

    def min_elem(self) -> Quantity:
        return self.base_to_units(self._range.min)

    def is_empty(self) -> bool:
        return self._range.is_empty()

    def op_intersect_range(self, other: "Range[QuantityT]") -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            return Ranges(units=self.units)
        _range = self._range.op_intersect_range(other._range)
        return Ranges._from_ranges(_range, self.units)

    def op_add_range(self, other: "Range[QuantityT]") -> "Range[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._range.op_add_range(other._range)
        return Range._from_range(_range, self.units)

    def op_negate(self) -> "Range[QuantityT]":
        _range = self._range.op_negate()
        return Range._from_range(_range, self.units)

    def op_subtract_range(self, other: "Range[QuantityT]") -> "Range[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._range.op_subtract_range(other._range)
        return Range._from_range(_range, self.units)

    def op_mul_range(self, other: "Range[QuantityT]") -> "Range[QuantityT]":
        _range = self._range.op_mul_range(other._range)
        return Range._from_range(_range, self.units * other.units)

    def op_invert(self) -> "Ranges[QuantityT]":
        _range = self._range.op_invert()
        return Ranges._from_ranges(_range, 1 / self.units)

    def op_div_range(self, other: "Range[QuantityT]") -> "Ranges[QuantityT]":
        _range = self._range.op_div_range(other._range)
        return Ranges._from_ranges(_range, self.units / other.units)

    # def __copy__(self) -> Self:
    #    r = Range.__new__(Range)
    #    r.min = self.min
    #    r.max = self.max
    #    r.empty = self.empty
    #    r.units = self.units
    #    return r

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, Quantity):
            if not item.units.is_compatible_with(self.units):
                return False
            item = item.to(self.range_units).magnitude
            if not isinstance(item, float) and not isinstance(item, int):
                return False
            return self._range.__contains__(item)
        return False

    # yucky with floats
    def __eq__(self, value: Any) -> bool:
        if not HasUnit.check(value):
            return False
        if not self.units.is_compatible_with(value.units):
            return False
        if isinstance(value, Range):
            return self._range == value._range
        if isinstance(value, Ranges) and len(value._ranges.ranges) == 1:
            return self._range == value._ranges.ranges[0]
        return False

    # TODO, convert to base unit first
    # def __hash__(self) -> int:
    #    return hash((self._range, self.units))

    def __repr__(self) -> str:
        if self.units.is_compatible_with(dimensionless):
            return f"Range({self._range.min}, {self._range.max})"
        return f"Range({self.base_to_units(self._range.min)}, {self.base_to_units(self._range.max)} | {self.units})"


def Single(value: QuantityT) -> Range[QuantityT]:
    return Range(value, value)


class Ranges(P_UnitSet[QuantityT]):
    def __init__(
        self,
        *ranges: Range[QuantityT] | "Ranges[QuantityT]",
        units: Unit | None = None,
    ):
        range_units = [HasUnit.get_units_or_dimensionless(r) for r in ranges]
        if len(range_units) == 0 and units is None:
            raise ValueError("units must be provided for empty union")
        self.units = units or range_units[0]
        self.range_units = base_units(self.units)
        if not all(self.units.is_compatible_with(u) for u in range_units):
            raise ValueError("all elements must have compatible units")

        def get_backing(r: Range[QuantityT] | "Ranges[QuantityT]"):
            if isinstance(r, Range):
                return r._range
            else:
                return r._ranges

        self._ranges = _N_Ranges(*(get_backing(r) for r in ranges))

    @staticmethod
    def _from_ranges(ranges: "_N_Ranges[NumericT]", units: Unit) -> "Ranges[QuantityT]":
        r = Ranges.__new__(Ranges)
        r._ranges = ranges
        r.units = units
        r.range_units = base_units(units)
        return r

    def is_empty(self) -> bool:
        return self._ranges.is_empty()

    def base_to_units(self, value: NumericT) -> Quantity:
        return Quantity(value, self.range_units).to(self.units)

    def min_elem(self) -> QuantityT:
        if self.is_empty():
            raise ValueError("empty range cannot have min element")
        return self.base_to_units(self._ranges.min_elem())

    def op_add_ranges(self, other: "Ranges[QuantityT]") -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_add_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units)

    def op_negate(self) -> "Ranges[QuantityT]":
        _range = self._ranges.op_negate()
        return Ranges._from_ranges(_range, self.units)

    def op_subtract_ranges(self, other: "Ranges[QuantityT]") -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_subtract_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units)

    def op_mul_ranges(self, other: "Ranges[QuantityT]") -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_mul_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units * other.units)

    def op_invert(self) -> "Ranges[QuantityT]":
        _range = self._ranges.op_invert()
        return Ranges._from_ranges(_range, 1 / self.units)

    def op_div_ranges(self, other: "Ranges[QuantityT]") -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_div_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units / other.units)

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, Quantity):
            if not item.units.is_compatible_with(self.units):
                return False
            item = item.to(self.range_units).magnitude
            if not isinstance(item, float) and not isinstance(item, int):
                return False
            return self._ranges.__contains__(item)
        return False

    def __eq__(self, value: Any) -> bool:
        if not HasUnit.check(value):
            return False
        if not self.units.is_compatible_with(value.units):
            return False
        if isinstance(value, Ranges):
            return self._ranges == value._ranges
        if isinstance(value, Range) and len(self._ranges.ranges) == 1:
            return self._ranges.ranges[0] == value._range
        return False

    def __repr__(self) -> str:
        if self.units.is_compatible_with(dimensionless):
            return f"_RangeUnion({', '.join(f"[{r.min}, {r.max}]" for r in self._ranges.ranges)})"
        return f"_RangeUnion({', '.join(f"[{self.base_to_units(r.min)}, {self.base_to_units(r.max)}]" for r in self._ranges.ranges)} | {self.units})"


def Empty(units: Unit | None = None) -> Ranges[QuantityT]:
    if units is None:
        units = dimensionless
    return Ranges(units=units)


def Singles(*values: QuantityT, units: Unit | None = None) -> Ranges[QuantityT]:
    return Ranges(*(Single(v) for v in values), units=units)
