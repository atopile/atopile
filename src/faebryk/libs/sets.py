# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Any, Protocol, Self

from faebryk.libs.units import HasUnit, P, Unit, dimensionless


class _SupportsRangeOps(Protocol):
    def __le__(self, __value) -> bool: ...
    def __lt__(self, __value) -> bool: ...
    def __ge__(self, __value) -> bool: ...
    def __gt__(self, __value) -> bool: ...

    def __mul__(self, __value: float | Self) -> Self: ...
    def __sub__(self, __value: Self) -> Self: ...
    def __add__(self, __value: Self) -> Self: ...


class Set_[T](ABC, HasUnit):
    def __init__(self):
        pass

    @abstractmethod
    def __contains__(self, item: T):
        pass


class Range[T: _SupportsRangeOps](Set_[T]):
    def __init__(
        self,
        min: T | None = None,
        max: T | None = None,
        empty: bool = False,
        units: Unit | None = None,
    ):
        self.empty = empty
        self.min = min
        self.max = max
        if empty and (min is not None or max is not None):
            raise ValueError("empty range cannot have min or max")
        if min is not None and max is not None and not min <= max:
            raise ValueError("min must be less than or equal to max")
        if min is None and max is None:
            if units is None:
                raise ValueError("units must be provided for empyt and full ranges")
            self.units = units
        else:
            min_unit = min.units if isinstance(min, HasUnit) else dimensionless
            max_unit = max.units if isinstance(max, HasUnit) else dimensionless
            if units and not min_unit.is_compatible_with(units):
                raise ValueError("min incompatible with units")
            if units and not max_unit.is_compatible_with(units):
                raise ValueError("max incompatible with units")
            self.units = units or min_unit

    def __contains__(self, item: T):
        if self.min is not None and not self.min <= item:
            return False
        if self.max is not None and not item <= self.max:
            return False
        return True

    @classmethod
    def from_center(cls, center: T, abs_tol: T) -> "Range[T]":
        return cls(center - abs_tol, center + abs_tol)

    @classmethod
    def from_center_rel(cls, center: T, rel_tol: float) -> "Range[T]":
        return cls(center - center * rel_tol, center + center * rel_tol)

    def intersection(self, other: "Range[T]") -> "Range[T]":
        if self.empty or other.empty:
            return Range(empty=True)

        if self.min is None:
            _min = other.min
        elif other.min is None:
            _min = self.min
        else:
            _min = max(self.min, other.min)

        if self.max is None:
            _max = other.max
        elif other.max is None:
            _max = self.max
        else:
            _max = min(self.max, other.max)

        if (_min is not None and (_min not in self or _min not in other)) or (
            _max is not None and (_max not in self or _max not in other)
        ):
            return Range(empty=True, units=self.units)

        return Range(_min, _max)

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, Range):
            return False
        if self.empty or value.empty:
            return self.empty and value.empty
        return self.min == value.min and self.max == value.max


class Single[T](Set_[T]):
    def __init__(self, value: T):
        self.value = value
        self.units = value.units if isinstance(value, HasUnit) else dimensionless

    def __contains__(self, item: T):
        return item == self.value


class Set[T](Set_[T]):
    def __init__(self, *elements: T):
        self.elements = set(elements)
        units = [e.units if isinstance(e, HasUnit) else dimensionless for e in elements]
        self.units = units[0]
        if not all(u.is_compatible_with(self.units) for u in units):
            raise ValueError("all elements must have compatible units")

    def __contains__(self, item: T):
        return item in self.elements
