# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Protocol, Self

from faebryk.libs.units import HasUnit, Quantity, Unit, dimensionless
from faebryk.libs.util import groupby


class _SupportsRangeOps(Protocol):
    def __le__(self, __value) -> bool: ...
    def __lt__(self, __value) -> bool: ...
    def __ge__(self, __value) -> bool: ...
    def __gt__(self, __value) -> bool: ...

    def __sub__(self, __value: Self) -> Self: ...
    def __add__(self, __value: Self) -> Self: ...


class _SupportsArithmeticOpsWithFloatMul(_SupportsRangeOps, Protocol):
    def __mul__(self, __value: float | Self) -> Self: ...


class Set_[T](ABC, HasUnit):
    def __init__(self, empty: bool, units: Unit):
        self.empty = empty
        self.units = units

    @abstractmethod
    def __contains__(self, item: T):
        pass

    @abstractmethod
    def min_elem(self) -> T | None:
        pass


class Empty[T](Set_[T]):
    def __init__(self, units: Unit):
        super().__init__(True, units)

    def __contains__(self, item: T):
        return False

    def min_elem(self) -> T | None:
        return None


class Range[T: _SupportsRangeOps](Set_[T]):
    def __init__(
        self,
        min: T | None = None,
        max: T | None = None,
        empty: bool = False,
        units: Unit | None = None,
    ):
        if empty and (min is not None or max is not None):
            raise ValueError("empty range cannot have min or max")
        if min is None and max is None:
            if not empty:
                raise ValueError("must provide at least one of min or max")
            if units is None:
                raise ValueError("units must be provided for empyt and full ranges")
        else:
            min_unit = (
                None
                if min is None
                else min.units
                if isinstance(min, HasUnit)
                else dimensionless
            )
            max_unit = (
                None
                if max is None
                else max.units
                if isinstance(max, HasUnit)
                else dimensionless
            )
            if units and min_unit and not min_unit.is_compatible_with(units):
                raise ValueError("min incompatible with units")
            if units and max_unit and not max_unit.is_compatible_with(units):
                raise ValueError("max incompatible with units")
            if min_unit and max_unit and not min_unit.is_compatible_with(max_unit):
                raise ValueError("min and max must be compatible")
            units = units or min_unit or max_unit
            assert units is not None  # stop typer check from being annoying
        if not empty:
            is_float = isinstance(min, float) or isinstance(max, float)
            is_quantity = isinstance(min, Quantity) or isinstance(max, Quantity)
            if isinstance(min, Quantity):
                is_float = isinstance(min.magnitude, float)
            if isinstance(max, Quantity):
                is_float = isinstance(max.magnitude, float)
            if is_quantity and is_float:
                self.min = min if min else Quantity(float("-inf"), units=units)
                self.max = max if max else Quantity(float("inf"), units=units)
            elif is_float:
                self.min = min or float("-inf")
                self.max = max or float("inf")
            else:
                if min is None or max is None:
                    raise ValueError(
                        "must provide both min and max for types other than float and float quantity"  # noqa: E501
                    )
                self.min = min
                self.max = max
            if not self.min <= self.max:
                raise ValueError("min must be less than or equal to max")
        super().__init__(empty, units)

    def min_elem(self) -> T | None:
        if self.empty:
            return None
        return self.min

    def __contains__(self, item: T):
        if self.empty:
            return False
        return self.min <= item <= self.max

    @staticmethod
    def from_center(center: T, abs_tol: T) -> "Range[_SupportsRangeOps]":
        return Range[_SupportsRangeOps](center - abs_tol, center + abs_tol)

    @staticmethod
    def from_center_rel(
        center: _SupportsArithmeticOpsWithFloatMul, rel_tol: float
    ) -> "Range[_SupportsRangeOps]":
        return Range[_SupportsRangeOps](
            center - center * rel_tol, center + center * rel_tol
        )

    def range_intersection(self, other: "Range[T]") -> "Range[T]":
        if self.empty or other.empty:
            return Range(empty=True, units=self.units)

        _min = max(self.min, other.min)
        _max = min(self.max, other.max)

        if (
            _min not in self
            or _min not in other
            or _max not in self
            or _max not in other
        ):
            return Range(empty=True, units=self.units)

        return Range(_min, _max)

    # def __copy__(self) -> Self:
    #    r = Range.__new__(Range)
    #    r.min = self.min
    #    r.max = self.max
    #    r.empty = self.empty
    #    r.units = self.units
    #    return r

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, Range):
            return False
        if self.empty or value.empty:
            return self.empty and value.empty
        return self.min == value.min and self.max == value.max

    def __hash__(self) -> int:
        return hash((self.min, self.max, self.units, self.empty))

    def __repr__(self) -> str:
        return f"Range({self.min}, {self.max})"


class Single[T](Set_[T]):
    def __init__(self, value: T):
        self.value = value
        units = value.units if isinstance(value, HasUnit) else dimensionless
        super().__init__(False, units)

    def __contains__(self, item: T):
        return item == self.value

    def min_elem(self) -> T | None:
        return self.value

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, Single):
            return False
        return self.value == value.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"Single({self.value})"


class Union[T](Set_[T]):
    def __init__(self, *elements: Set_[T], units: Unit | None = None):
        def flat():
            for element in elements:
                if element.empty:
                    continue
                if isinstance(element, Union):
                    yield from element.elements
                else:
                    yield element

        self.elements = OrderedDict(
            (element, None) for element in sorted(flat(), key=lambda e: e.min_elem())
        )
        elem_units = [
            e.units if isinstance(e, HasUnit) else dimensionless for e in elements
        ]
        if len(elem_units) == 0 and units is None:
            raise ValueError("units must be provided for empty union")
        units = units or elem_units[0]
        if not all(units.is_compatible_with(u) for u in elem_units):
            raise ValueError("all elements must have compatible units")
        super().__init__(len(self.elements) == 0, units)

    def __contains__(self, item: T):
        for element in self.elements:
            if item in element:
                return True
            if item < element.min_elem():
                return False
        return False

    def min_elem(self) -> T | None:
        if not self.elements:
            return None
        return next(iter(self.elements)).min_elem()

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, Union):
            return False
        # TODO: need to simplify, {1} u [0, 2] == [0, 2]
        return self.elements == value.elements

    def __repr__(self) -> str:
        return f"Set({', '.join(repr(e) for e in self.elements)})"


class Set[T](Union[T]):
    def __init__(self, *elements: T, units: Unit | None = None):
        super().__init__(*(Single(e) for e in elements), units=units)

    def __contains__(self, item: T):
        return Single(item) in self.elements


def operation_add[T: _SupportsRangeOps, U: _SupportsRangeOps](
    *sets: Set_[T],
) -> Set_[_SupportsRangeOps]:
    def add_singles(*singles: Single[T]) -> T:
        if len(singles) == 0:
            return 0
        return sum(s.value for s in singles)

    def add_ranges(*ranges: Range[T], offset: T) -> list[Range[T]]:
        if len(ranges) == 0:
            return []
        return [
            Range(
                min=sum(r.min for r in ranges) + offset,
                max=sum(r.max for r in ranges) + offset,
            )
        ]

    if any(s.empty for s in sets):
        return Empty(units=sets[0].units)

    def group(set: Set_[T]) -> str:
        if isinstance(set, Single):
            return "single"
        if isinstance(set, Range):
            return "range"
        return "union"

    grouped_sets = groupby(sets, key=group)
    singles = grouped_sets["single"]
    ranges = grouped_sets["range"]
    unions = grouped_sets["union"]
    single_offset = add_singles(*singles)
    range_sum = add_ranges(*ranges, offset=single_offset)

    if len(range_sum) > 0:
        recursion_set = range_sum
    elif len(singles) > 0:
        recursion_set = [Single(single_offset)]
    else:
        recursion_set = []

    if len(unions) == 0:
        assert len(recursion_set) == 1
        return recursion_set[0]
    return Union(  # TODO this is exponential, we'll want to defer the computation
        *(operation_add(e, *unions[1:], *recursion_set) for e in unions[0].elements)
    )


def operation_negate[T: _SupportsRangeOps](
    *sets: Set_[T],
) -> list[Set_[_SupportsRangeOps]]:
    def negate(set: Set_[T]) -> Set_[T]:
        if isinstance(set, Single):
            return Single(-set.value)
        if isinstance(set, Range):
            return Range(-set.max, -set.min)
        return Union(*(negate(e) for e in set.elements))

    return [negate(e) for e in sets]


def operation_subtract[T: _SupportsRangeOps](
    first: Set_[T],
    *sets: Set_[T],
) -> Set_[_SupportsRangeOps]:
    return operation_add(first, *operation_negate(*sets))
