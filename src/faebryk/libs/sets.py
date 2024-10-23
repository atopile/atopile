# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from bisect import bisect
from collections.abc import Generator, Iterable, Iterator
from typing import Any, Protocol, Type, TypeVar, cast

from faebryk.libs.units import HasUnit, Quantity, Unit, dimensionless

# Protocols ----------------------------------------------------------------------------


class P_Set[T](Protocol):
    def is_empty(self) -> bool: ...

    def __contains__(self, item: T) -> bool: ...


class P_IterableSet[T, IterT](P_Set[T], Iterable[IterT], Protocol): ...


class P_UnitSet[T](P_Set[T], Protocol):
    units: Unit


class P_IterableUnitSet[T, IterT](P_UnitSet[T], Iterable[IterT], Protocol): ...


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


class PlainSet[U](P_IterableSet[U, U]):
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

    def __iter__(self) -> Iterator[U]:
        return self.elements.__iter__()


# Numeric ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class _N_Range(P_Set[NumericT]):
    def __init__(self, min: NumericT, max: NumericT):
        if not min <= max:
            raise ValueError("min must be less than or equal to max")
        if min == float("inf") or max == float("-inf"):
            raise ValueError("min or max has bad infinite value")
        self._min = min
        self._max = max

    def is_empty(self) -> bool:
        return False

    def min_elem(self) -> NumericT:
        return self._min

    def max_elem(self) -> NumericT:
        return self._max

    def op_add_range(self, other: "_N_Range[NumericT]") -> "_N_Range[NumericT]":
        return _N_Range(self._min + other._min, self._max + other._max)

    def op_negate(self) -> "_N_Range[NumericT]":
        return _N_Range(-self._max, -self._min)

    def op_subtract_range(self, other: "_N_Range[NumericT]") -> "_N_Range[NumericT]":
        return self.op_add_range(other.op_negate())

    def op_mul_range(self, other: "_N_Range[NumericT]") -> "_N_Range[NumericT]":
        return _N_Range(
            min(
                self._min * other._min,
                self._min * other._max,
                self._max * other._min,
                self._max * other._max,
            ),
            max(
                self._min * other._min,
                self._min * other._max,
                self._max * other._min,
                self._max * other._max,
            ),
        )

    def op_invert(self) -> "_N_Ranges[float]":
        if self._min == 0 == self._max:
            return _N_Empty()
        if self._min < 0 < self._max:
            return _N_Ranges(
                _N_Range(float("-inf"), 1 / self._min),
                _N_Range(1 / self._max, float("inf")),
            )
        elif self._min < 0 == self._max:
            return _N_Ranges(_N_Range(float("-inf"), 1 / self._min))
        elif self._min == 0 < self._max:
            return _N_Ranges(_N_Range(1 / self._max, float("inf")))
        else:
            return _N_Ranges(_N_Range(1 / self._max, 1 / self._min))

    def op_div_range(
        self: "_N_Range[float]", other: "_N_Range[float]"
    ) -> "_N_Ranges[float]":
        return _N_Ranges(*(self.op_mul_range(o) for o in other.op_invert().ranges))

    def op_intersect_range(self, other: "_N_Range[NumericT]") -> "_N_Ranges[NumericT]":
        min_ = max(self._min, other._min)
        max_ = min(self._max, other._max)
        if min_ <= max_:
            return _N_Ranges(_N_Range(min_, max_))
        return _N_Empty()

    def maybe_merge_range(
        self, other: "_N_Range[NumericT]"
    ) -> list["_N_Range[NumericT]"]:
        is_left = self._min <= other._min
        left = self if is_left else other
        right = other if is_left else self
        if right._min in self:
            return [_N_Range(left._min, max(left._max, right._max))]
        return [left, right]

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, _N_Range):
            return False
        return self._min == other._min and self._max == other._max

    def __contains__(self, item: NumericT) -> bool:
        return self._min <= item <= self._max

    def __hash__(self) -> int:
        return hash((self._min, self._max))

    def __repr__(self) -> str:
        return f"_Range({self._min}, {self._max})"


def _N_Single(value: NumericT) -> _N_Range[NumericT]:
    return _N_Range(value, value)


class _N_NonIterableRanges(P_Set[NumericT]):
    def __init__(self, *ranges: _N_Range[NumericT] | "_N_NonIterableRanges[NumericT]"):
        def gen_flat_non_empty() -> Generator[_N_Range[NumericT]]:
            for r in ranges:
                if r.is_empty():
                    continue
                if isinstance(r, _N_NonIterableRanges):
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

    def max_elem(self) -> NumericT:
        if self.is_empty():
            raise ValueError("empty range cannot have max element")
        return self.ranges[-1].max_elem()

    def closest_elem(self, target: NumericT) -> NumericT:
        if self.is_empty():
            raise ValueError("empty range cannot have closest element")
        index = bisect(self.ranges, target, key=lambda r: r.min_elem())
        left = self.ranges[index - 1] if index > 0 else None
        if left and target in left:
            return target
        left_bound = left.max_elem() if left else None
        right_bound = (
            self.ranges[index].min_elem() if index < len(self.ranges) else None
        )
        try:
            [one] = [b for b in [left_bound, right_bound] if b is not None]
            return one
        except ValueError:
            assert left_bound and right_bound
            if target - left_bound < right_bound - target:
                return left_bound
            return right_bound
        assert False  # unreachable

    def op_intersect_range(
        self, other: "_N_Range[NumericT]"
    ) -> "_N_NonIterableRanges[NumericT]":
        return _N_NonIterableRanges(*(r.op_intersect_range(other) for r in self.ranges))

    def op_intersect_ranges(
        self, other: "_N_NonIterableRanges[NumericT]"
    ) -> "_N_NonIterableRanges[NumericT]":
        # TODO currently quadratic
        # lists are sorted, so this could be linear
        return _N_NonIterableRanges(
            *(r.op_intersect_range(o) for r in self.ranges for o in other.ranges)
        )

    def op_union_ranges(
        self, other: "_N_NonIterableRanges[NumericT]"
    ) -> "_N_NonIterableRanges[NumericT]":
        return _N_NonIterableRanges(*self.ranges, *other.ranges)

    def op_add_ranges(
        self, other: "_N_NonIterableRanges[NumericT]"
    ) -> "_N_NonIterableRanges[NumericT]":
        return _N_NonIterableRanges(
            *(r.op_add_range(o) for r in self.ranges for o in other.ranges)
        )

    def op_negate(self) -> "_N_NonIterableRanges[NumericT]":
        return _N_NonIterableRanges(*(r.op_negate() for r in self.ranges))

    def op_subtract_ranges(
        self, other: "_N_NonIterableRanges[NumericT]"
    ) -> "_N_NonIterableRanges[NumericT]":
        return self.op_add_ranges(other.op_negate())

    def op_mul_ranges(
        self, other: "_N_NonIterableRanges[NumericT]"
    ) -> "_N_NonIterableRanges[NumericT]":
        return _N_NonIterableRanges(
            *(r.op_mul_range(o) for r in self.ranges for o in other.ranges)
        )

    def op_invert(self) -> "_N_NonIterableRanges[float]":
        return _N_NonIterableRanges(*(r.op_invert() for r in self.ranges))

    def op_div_ranges(
        self: "_N_NonIterableRanges[float]", other: "_N_NonIterableRanges[float]"
    ) -> "_N_NonIterableRanges[float]":
        return self.op_mul_ranges(other.op_invert())

    def __contains__(self, item: NumericT) -> bool:
        index = bisect(self.ranges, item, key=lambda r: r.min_elem())

        if index == 0:
            return False
        return item in self.ranges[index - 1]

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, _N_NonIterableRanges):
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
        return f"_N_Ranges({', '.join(f"[{r._min}, {r._max}]" for r in self.ranges)})"


class _N_Ranges(_N_NonIterableRanges[NumericT], Iterable[_N_Range[NumericT]]):
    def __iter__(self) -> Generator[_N_Range[NumericT]]:
        yield from self.ranges


class _N_Singles(_N_NonIterableRanges[NumericT], Iterable[NumericT]):
    def __init__(self, *values: NumericT):
        super().__init__(*(_N_Single(v) for v in values))

    def __iter__(self) -> Generator[NumericT]:
        for r in self.ranges:
            yield r._min


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
            min=Quantity(range._min, base_units(units)),
            max=Quantity(range._max, base_units(units)),
            units=units,
        )

    def base_to_units(self, value: NumericT) -> Quantity:
        return Quantity(value, self.range_units).to(self.units)

    def min_elem(self) -> Quantity:
        return self.base_to_units(self._range.min_elem())

    def max_elem(self) -> Quantity:
        return self.base_to_units(self._range.max_elem())

    def is_empty(self) -> bool:
        return self._range.is_empty()

    def op_intersect_range(
        self, other: "Range[QuantityT]"
    ) -> "NonIterableRanges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            return NonIterableRanges(units=self.units)
        _range = self._range.op_intersect_range(other._range)
        return NonIterableRanges._from_ranges(_range, self.units)

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

    def op_div_range(self, other: "Range[QuantityT]") -> "NonIterableRanges[QuantityT]":
        _range = self._range.op_div_range(other._range)
        return NonIterableRanges._from_ranges(_range, self.units / other.units)

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
        if isinstance(value, NonIterableRanges) and len(value._ranges.ranges) == 1:
            return self._range == value._ranges.ranges[0]
        return False

    # TODO, convert to base unit first
    # def __hash__(self) -> int:
    #    return hash((self._range, self.units))

    def __repr__(self) -> str:
        if self.units.is_compatible_with(dimensionless):
            return f"Range({self._range._min}, {self._range._max})"
        return f"Range({self.base_to_units(self._range._min)}, {self.base_to_units(self._range._max)} | {self.units})"


class Single(Range[QuantityT]):
    def __init__(self, value: QuantityT):
        super().__init__(value, value)

    def __iter__(self) -> Generator[Quantity]:
        yield self.min_elem()


NonIterableRangesT = TypeVar("NonIterableRangesT", bound="NonIterableRanges")


class NonIterableRanges(P_UnitSet[QuantityT]):
    def __init__(
        self,
        *ranges: Range[QuantityT]
        | "NonIterableRanges[QuantityT]"
        | tuple[QuantityT, QuantityT],
        units: Unit | None = None,
    ):
        proper_ranges = [
            Range(r[0], r[1]) if isinstance(r, tuple) else r for r in ranges
        ]
        range_units = [HasUnit.get_units_or_dimensionless(r) for r in proper_ranges]
        if len(range_units) == 0 and units is None:
            raise ValueError("units must be provided for empty union")
        self.units = units or range_units[0]
        self.range_units = base_units(self.units)
        if not all(self.units.is_compatible_with(u) for u in range_units):
            raise ValueError("all elements must have compatible units")

        def get_backing(r: Range[QuantityT] | "NonIterableRanges[QuantityT]"):
            if isinstance(r, Range):
                return r._range
            else:
                return r._ranges

        self._ranges = _N_Ranges(*(get_backing(r) for r in proper_ranges))

    @classmethod
    def _from_ranges(
        cls: Type[NonIterableRangesT],
        ranges: "_N_NonIterableRanges[NumericT]",
        units: Unit,
    ) -> NonIterableRangesT:
        r = cls.__new__(cls)
        r._ranges = ranges
        r.units = units
        r.range_units = base_units(units)
        return r

    def is_empty(self) -> bool:
        return self._ranges.is_empty()

    def base_to_units(self, value: NumericT) -> Quantity:
        return Quantity(value, self.range_units).to(self.units)

    def min_elem(self) -> Quantity:
        if self.is_empty():
            raise ValueError("empty range cannot have min element")
        return self.base_to_units(self._ranges.min_elem())

    def max_elem(self) -> Quantity:
        if self.is_empty():
            raise ValueError("empty range cannot have max element")
        return self.base_to_units(self._ranges.max_elem())

    def closest_elem(self, target: Quantity) -> Quantity:
        if not self.units.is_compatible_with(target.units):
            raise ValueError("incompatible units")
        return self.base_to_units(
            self._ranges.closest_elem(target.to(self.range_units).magnitude)
        )

    def op_intersect_range(self, other: "Range[QuantityT]") -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_intersect_range(other._range)
        return Ranges._from_ranges(_range, self.units)

    def op_intersect_ranges(
        self, other: "NonIterableRanges[QuantityT]"
    ) -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_intersect_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units)

    def op_union_ranges(
        self, other: "NonIterableRanges[QuantityT]"
    ) -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_union_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units)

    def op_add_ranges(
        self, other: "NonIterableRanges[QuantityT]"
    ) -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_add_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units)

    def op_negate(self) -> "Ranges[QuantityT]":
        _range = self._ranges.op_negate()
        return Ranges._from_ranges(_range, self.units)

    def op_subtract_ranges(
        self, other: "NonIterableRanges[QuantityT]"
    ) -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_subtract_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units)

    def op_mul_ranges(
        self, other: "NonIterableRanges[QuantityT]"
    ) -> "Ranges[QuantityT]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_mul_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units * other.units)

    def op_invert(self) -> "Ranges[QuantityT]":
        _range = self._ranges.op_invert()
        return Ranges._from_ranges(_range, 1 / self.units)

    def op_div_ranges(
        self, other: "NonIterableRanges[QuantityT]"
    ) -> "Ranges[QuantityT]":
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
        if isinstance(value, NonIterableRanges):
            return self._ranges == value._ranges
        if isinstance(value, Range) and len(self._ranges.ranges) == 1:
            return self._ranges.ranges[0] == value._range
        return False

    def __hash__(self) -> int:
        return hash((self._ranges, self.units))

    def __repr__(self) -> str:
        if self.units.is_compatible_with(dimensionless):
            return f"_RangeUnion({', '.join(f"[{r._min}, {r._max}]" for r in self._ranges.ranges)})"
        return f"_RangeUnion({', '.join(f"[{self.base_to_units(r._min)}, {self.base_to_units(r._max)}]" for r in self._ranges.ranges)} | {self.units})"


class Ranges(NonIterableRanges[QuantityT], Iterable[Range[QuantityT]]):
    def __iter__(self) -> Generator[Range[QuantityT]]:
        for r in self._ranges.ranges:
            yield Range._from_range(r, self.units)


def Empty(units: Unit | None = None) -> Ranges[QuantityT]:
    if units is None:
        units = dimensionless
    return Ranges(units=units)


class Singles(NonIterableRanges[QuantityT]):
    def __init__(self, *values: QuantityT, units: Unit | None = None):
        super().__init__(*(Single(v) for v in values), units=units)

    def __iter__(self) -> Generator[Quantity]:
        for r in self._ranges.ranges:
            yield self.base_to_units(r._min)
