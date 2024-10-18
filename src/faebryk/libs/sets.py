# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from collections.abc import Generator
from typing import Any, Protocol, TypeVar

from faebryk.libs.units import HasUnit, Quantity, Unit, dimensionless

# class _SupportsRangeOps(Protocol):
#    def __le__(self, __value) -> bool: ...
#    def __lt__(self, __value) -> bool: ...
#    def __ge__(self, __value) -> bool: ...
#    def __gt__(self, __value) -> bool: ...
#
#    def __sub__(self, __value: Self) -> Self: ...
#    def __add__(self, __value: Self) -> Self: ...
#
#
# class _SupportsArithmeticOpsWithFloatMul(_SupportsRangeOps, Protocol):
#    def __mul__(self, __value: float | Self) -> Self: ...


class _Set[T](Protocol):
    def is_empty(self) -> bool: ...

    def __contains__(self, item: T) -> bool: ...


T = TypeVar("T", int, float, contravariant=False, covariant=False)


class _Range(_Set[T]):
    def __init__(self, min: T, max: T):
        if not min <= max:
            raise ValueError("min must be less than or equal to max")
        self.min = min
        self.max = max

    def is_empty(self) -> bool:
        return False

    def min_elem(self) -> T:
        return self.min

    def op_add_range(self, other: "_Range[T]") -> "_Range[T]":
        return _Range(self.min + other.min, self.max + other.max)

    def op_negate(self) -> "_Range[T]":
        return _Range(-self.max, -self.min)

    def op_subtract_range(self, other: "_Range[T]") -> "_Range[T]":
        return self.op_add_range(other.op_negate())

    def op_mul_range(self, other: "_Range[T]") -> "_Range[T]":
        return _Range(
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

    def op_invert(self) -> "_RangeUnion[float]":
        if self.min == 0 == self.max:
            return _NumericEmpty()
        if self.min < 0 < self.max:
            return _RangeUnion(
                _Range(float("-inf"), 1 / self.min),
                _Range(1 / self.max, float("inf")),
            )
        elif self.min < 0 == self.max:
            return _RangeUnion(_Range(float("-inf"), 1 / self.min))
        elif self.min == 0 < self.max:
            return _RangeUnion(_Range(1 / self.max, float("inf")))
        else:
            return _RangeUnion(_Range(1 / self.max, 1 / self.min))

    def op_div_range(
        self: "_Range[float]", other: "_Range[float]"
    ) -> "_RangeUnion[float]":
        return _RangeUnion(*(self.op_mul_range(o) for o in other.op_invert().ranges))

    def op_intersect_range(self, other: "_Range[T]") -> "_RangeUnion[T]":
        min_ = max(self.min, other.min)
        max_ = min(self.max, other.max)
        if min_ <= max_:
            return _RangeUnion(_Range(min_, max_))
        return _NumericEmpty()

    def maybe_merge_range(self, other: "_Range[T]") -> list["_Range[T]"]:
        is_left = self.min <= other.min
        left = self if is_left else other
        right = other if is_left else self
        if right.min in self:
            return [_Range(left.min, max(left.max, right.max))]
        return [left, right]

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, _Range):
            return False
        return self.min == other.min and self.max == other.max

    def __contains__(self, item: T) -> bool:
        return self.min <= item <= self.max

    def __hash__(self) -> int:
        return hash((self.min, self.max))

    def __repr__(self) -> str:
        return f"_Range({self.min}, {self.max})"


def _Single(value: T) -> _Range[T]:
    return _Range(value, value)


class _RangeUnion(_Set[T]):
    def __init__(self, *ranges: _Range[T] | "_RangeUnion[T]"):
        def gen_flat_non_empty() -> Generator[_Range[T]]:
            for r in ranges:
                if r.is_empty():
                    continue
                if isinstance(r, _RangeUnion):
                    yield from r.ranges
                else:
                    assert isinstance(r, _Range)
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

    def min_elem(self) -> T:
        if self.is_empty():
            raise ValueError("empty range cannot have min element")
        return self.ranges[0].min_elem()

    def op_add_ranges(self, other: "_RangeUnion[T]") -> "_RangeUnion[T]":
        return _RangeUnion(
            *(r.op_add_range(o) for r in self.ranges for o in other.ranges)
        )

    def op_negate(self) -> "_RangeUnion[T]":
        return _RangeUnion(*(r.op_negate() for r in self.ranges))

    def op_subtract_ranges(self, other: "_RangeUnion[T]") -> "_RangeUnion[T]":
        return self.op_add_ranges(other.op_negate())

    def op_mul_ranges(self, other: "_RangeUnion[T]") -> "_RangeUnion[T]":
        return _RangeUnion(
            *(r.op_mul_range(o) for r in self.ranges for o in other.ranges)
        )

    def op_invert(self) -> "_RangeUnion[float]":
        return _RangeUnion(*(r.op_invert() for r in self.ranges))

    def op_div_ranges(
        self: "_RangeUnion[float]", other: "_RangeUnion[float]"
    ) -> "_RangeUnion[float]":
        return self.op_mul_ranges(other.op_invert())

    def __contains__(self, item: T) -> bool:
        from bisect import bisect

        index = bisect(self.ranges, item, key=lambda r: r.min_elem())

        if index == 0:
            return False
        return item in self.ranges[index - 1]

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, _RangeUnion):
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


def _Singles(*values: T) -> _RangeUnion[T]:
    return _RangeUnion(*(_Single(v) for v in values))


__numeric_empty = _RangeUnion()


def _NumericEmpty() -> _RangeUnion:
    return __numeric_empty


class _NonNumericSet[U](_Set[U]):
    def __init__(self, *elements: U):
        self.elements = set(elements)

    def is_empty(self) -> bool:
        return len(self.elements) == 0

    def __contains__(self, item: U) -> bool:
        return item in self.elements


# class Empty[T](Set_[T]):
#    def __init__(self, units: Unit):
#        super().__init__(True, units)
#
#    def __contains__(self, item: T):
#        return False
#
#    def min_elem(self) -> T | None:
#        return None


class UnitSet[T](_Set[T], HasUnit, Protocol): ...


TQuant = TypeVar("TQuant", int, float, Quantity, contravariant=False, covariant=False)


def base_units(units: Unit) -> Unit:
    return Quantity(1, units).to_base_units().units


class Range(UnitSet[TQuant]):
    def __init__(
        self,
        min: TQuant | None = None,
        max: TQuant | None = None,
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

        self._range = _Range(num_min, num_max)

    @staticmethod
    def from_center(center: TQuant, abs_tol: TQuant) -> "Range[TQuant]":
        left = center - abs_tol
        right = center + abs_tol
        return Range(left, right)

    @staticmethod
    def from_center_rel(center: TQuant, rel_tol: float) -> "Range[TQuant]":
        return Range(center - center * rel_tol, center + center * rel_tol)

    @staticmethod
    def _from_range(range: _Range[T], units: Unit) -> "Range[TQuant]":
        return Range(
            min=Quantity(range.min, base_units(units)),
            max=Quantity(range.max, base_units(units)),
            units=units,
        )

    def base_to_units(self, value: T) -> Quantity:
        return Quantity(value, self.range_units).to(self.units)

    def min_elem(self) -> Quantity:
        return self.base_to_units(self._range.min)

    def is_empty(self) -> bool:
        return self._range.is_empty()

    def op_intersect_range(self, other: "Range[TQuant]") -> "Ranges[TQuant]":
        if not self.units.is_compatible_with(other.units):
            return Ranges(units=self.units)
        _range = self._range.op_intersect_range(other._range)
        return Ranges._from_ranges(_range, self.units)

    def op_add_range(self, other: "Range[TQuant]") -> "Range[TQuant]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._range.op_add_range(other._range)
        return Range._from_range(_range, self.units)

    def op_negate(self) -> "Range[TQuant]":
        _range = self._range.op_negate()
        return Range._from_range(_range, self.units)

    def op_subtract_range(self, other: "Range[TQuant]") -> "Range[TQuant]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._range.op_subtract_range(other._range)
        return Range._from_range(_range, self.units)

    def op_mul_range(self, other: "Range[TQuant]") -> "Range[TQuant]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._range.op_mul_range(other._range)
        return Range._from_range(_range, self.units * other.units)

    def op_invert(self) -> "Ranges[TQuant]":
        _range = self._range.op_invert()
        return Ranges._from_ranges(_range, 1 / self.units)

    def op_div_range(self, other: "Range[TQuant]") -> "Ranges[TQuant]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
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
        if not isinstance(value, HasUnit):
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


def Single(value: TQuant) -> Range[TQuant]:
    return Range(value, value)


class Ranges(UnitSet[TQuant]):
    def __init__(
        self, *ranges: Range[TQuant] | "Ranges[TQuant]", units: Unit | None = None
    ):
        range_units = [
            r.units if isinstance(r, HasUnit) else dimensionless for r in ranges
        ]
        if len(range_units) == 0 and units is None:
            raise ValueError("units must be provided for empty union")
        self.units = units or range_units[0]
        self.range_units = base_units(self.units)
        if not all(self.units.is_compatible_with(u) for u in range_units):
            raise ValueError("all elements must have compatible units")

        def get_backing(r: Range[TQuant] | "Ranges[TQuant]"):
            if isinstance(r, Range):
                return r._range
            else:
                return r._ranges

        self._ranges = _RangeUnion(*(get_backing(r) for r in ranges))

    @staticmethod
    def _from_ranges(ranges: _RangeUnion[T], units: Unit) -> "Ranges[TQuant]":
        r = Ranges.__new__(Ranges)
        r._ranges = ranges
        r.units = units
        r.range_units = base_units(units)
        return r

    def is_empty(self) -> bool:
        return self._ranges.is_empty()

    def base_to_units(self, value: T) -> Quantity:
        return Quantity(value, self.range_units).to(self.units)

    def min_elem(self) -> TQuant:
        if self.is_empty():
            raise ValueError("empty range cannot have min element")
        return self.base_to_units(self._ranges.min_elem())

    def op_add_ranges(self, other: "Ranges[TQuant]") -> "Ranges[TQuant]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_add_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units)

    def op_negate(self) -> "Ranges[TQuant]":
        _range = self._ranges.op_negate()
        return Ranges._from_ranges(_range, self.units)

    def op_subtract_ranges(self, other: "Ranges[TQuant]") -> "Ranges[TQuant]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_subtract_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units)

    def op_mul_ranges(self, other: "Ranges[TQuant]") -> "Ranges[TQuant]":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _range = self._ranges.op_mul_ranges(other._ranges)
        return Ranges._from_ranges(_range, self.units * other.units)

    def op_invert(self) -> "Ranges[TQuant]":
        _range = self._ranges.op_invert()
        return Ranges._from_ranges(_range, 1 / self.units)

    def op_div_ranges(self, other: "Ranges[TQuant]") -> "Ranges[TQuant]":
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
        if not isinstance(value, HasUnit):
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


def UnitEmpty(units: Unit) -> Ranges[TQuant]:
    return Ranges(units=units)


def Singles(*values: TQuant, units: Unit | None = None) -> Ranges[TQuant]:
    return Ranges(*(Single(v) for v in values), units=units)


# class Set[T](Union[T]):
#    def __init__(self, *elements: T, units: Unit | None = None):
#        super().__init__(*(Single(e) for e in elements), units=units)
#
#    def __contains__(self, item: T):
#        return Single(item) in self.elements
#
#
# def operation_add[T: _SupportsRangeOps](
#    *sets: Set_[T],
# ) -> Set_[_SupportsRangeOps]:
#    def add_singles(*singles: Single[T]) -> T:
#        if len(singles) == 0:
#            return 0
#        return sum(s.value for s in singles)
#
#    def add_ranges(*ranges: Range[T], offset: T) -> list[Range[T]]:
#        if len(ranges) == 0:
#            return []
#        return [
#            Range(
#                min=sum(r.min for r in ranges) + offset,
#                max=sum(r.max for r in ranges) + offset,
#            )
#        ]
#
#    if any(s.empty for s in sets):
#        return Empty(units=sets[0].units)
#
#    def group(set: Set_[T]) -> str:
#        if isinstance(set, Single):
#            return "single"
#        if isinstance(set, Range):
#            return "range"
#        return "union"
#
#    grouped_sets = groupby(sets, key=group)
#    singles = grouped_sets["single"]
#    ranges = grouped_sets["range"]
#    unions = grouped_sets["union"]
#    single_offset = add_singles(*singles)
#    range_sum = add_ranges(*ranges, offset=single_offset)
#
#    if len(range_sum) > 0:
#        recursion_set = range_sum
#    elif len(singles) > 0:
#        recursion_set = [Single(single_offset)]
#    else:
#        recursion_set = []
#
#    if len(unions) == 0:
#        assert len(recursion_set) == 1
#        return recursion_set[0]
#    return Union(  # TODO this is exponential, we'll want to defer the computation
#        *(operation_add(e, *unions[1:], *recursion_set) for e in unions[0].elements)
#    )
#
#
# def operation_negate[T: _SupportsRangeOps](
#    *sets: Set_[T],
# ) -> list[Set_[_SupportsRangeOps]]:
#    def negate(set: Set_[T]) -> Set_[T]:
#        if isinstance(set, Single):
#            return Single(-set.value)
#        if isinstance(set, Range):
#            return Range(-set.max, -set.min)
#        return Union(*(negate(e) for e in set.elements))
#
#    return [negate(e) for e in sets]
#
#
# def operation_subtract[T: _SupportsRangeOps](
#    first: Set_[T],
#    *sets: Set_[T],
# ) -> Set_[_SupportsRangeOps]:
#    return operation_add(first, *operation_negate(*sets))
#
#
# def operation_mul[T: _SupportsRangeOps](
#    *sets: Set_[T],
# ) -> Set_[_SupportsRangeOps]:
#    def mul_singles(*singles: Single[T]) -> Single[T]:
#        return Single(math.prod((s.value for s in singles), start=1))
#
#    def mul_ranges(r1: Range[T], r2: Range[T]) -> Range[T]:
#        return Range(
#            min=min(r1.min * r2.min, r1.min * r2.max, r1.max * r2.min, r1.max * r2.max),
#            max=max(r1.min * r2.min, r1.min * r2.max, r1.max * r2.min, r1.max * r2.max),
#        )
#
#    def mul_single_range(single: Single[T], range: Range[T]) -> Range[T]:
#        if single.value < 0:
#            return Range(min=single.value * range.max, max=single.value * range.min)
#        return Range(min=single.value * range.min, max=single.value * range.max)
#
#    def mul_range_list(
#        *ranges: Range[T], factor: Single[T] = Single(1)
#    ) -> list[Range[T]]:
#        if len(ranges) == 0:
#            return []
#        first, *rest = ranges
#        first = mul_single_range(factor, first)
#        for r in rest:
#            first = mul_ranges(first, r)
#        return [first]
#
#    if any(s.empty for s in sets):
#        return Empty(units=sets[0].units)
#
#    def group(set: Set_[T]) -> str:
#        if isinstance(set, Single):
#            return "single"
#        if isinstance(set, Range):
#            return "range"
#        return "union"
#
#    grouped_sets = groupby(sets, key=group)
#    singles = grouped_sets["single"]
#    ranges = grouped_sets["range"]
#    unions = grouped_sets["union"]
#    single_product = mul_singles(*singles)
#    range_product = mul_range_list(*ranges, factor=single_product)
#
#    if len(range_product) > 0:
#        recursion_set = range_product
#    elif len(singles) > 0:
#        recursion_set = [single_product]
#    else:
#        recursion_set = []
#
#    if len(unions) == 0:
#        assert len(recursion_set) == 1
#        return recursion_set[0]
#    return Union(  # TODO this is exponential, we'll want to defer the computation
#        *(operation_mul(e, *unions[1:], *recursion_set) for e in unions[0].elements)
#    )
