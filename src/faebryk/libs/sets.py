# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Any, Protocol, Self

from faebryk.libs.units import Quantity, Unit


class _SupportsRangeOps(Protocol):
    def __le__(self, __value) -> bool: ...
    def __lt__(self, __value) -> bool: ...
    def __ge__(self, __value) -> bool: ...
    def __gt__(self, __value) -> bool: ...

    def __mul__(self, __value: float | Self) -> Self: ...
    def __sub__(self, __value: Self) -> Self: ...
    def __add__(self, __value: Self) -> Self: ...


class Set_[T](ABC):
    def __init__(self):
        pass

    @abstractmethod
    def __contains__(self, item: T):
        pass

    @abstractmethod
    def is_compatible_with_unit(self, unit: Unit | Quantity) -> bool:
        pass


class Range[T: _SupportsRangeOps](Set_[T]):
    def __init__(self, min: T | None = None, max: T | None = None, empty: bool = False):
        self.empty = empty
        self.min = min
        self.max = max
        if empty and (min is not None or max is not None):
            raise ValueError("empty range cannot have min or max")
        if min is not None and max is not None and not min <= max:
            raise ValueError("min must be less than or equal to max")

    def __contains__(self, item: T):
        if self.min is not None and not self.min <= item:
            return False
        if self.max is not None and not item <= self.max:
            return False
        return True

    def is_compatible_with_unit(self, unit: Unit | Quantity) -> bool:
        for m in [self.min, self.max]:
            if isinstance(m, Quantity) and not unit.is_compatible_with(m.units):
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
            return Range(empty=True)

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

    def __contains__(self, item: T):
        return item == self.value

    def is_compatible_with_unit(self, unit: Unit | Quantity) -> bool:
        if isinstance(self.value, Quantity) and not unit.is_compatible_with(
            self.value.units
        ):
            return False
        return True


class Set[T](Set_[T]):
    def __init__(self, *elements: T):
        self.elements = set(elements)

    def __contains__(self, item: T):
        return item in self.elements
