from faebryk.libs.units import Quantity, Unit
import math

from typing import Protocol

class _SupportsRangeOps(Protocol):
    def __le__(self, __value) -> bool: ...
    def __lt__(self, __value) -> bool: ...
    def __ge__(self, __value) -> bool: ...
    def __gt__(self, __value) -> bool: ...


class RangeInclusive[T: _SupportsRangeOps]:
    def __init__(self, min: T | None = None, max: T | None = None):
        self.min = min
        self.max = max
        if min is not None and max is not None and not min <= max:
            raise ValueError("min must be less than or equal to max")

    def __contains__(self, item: T):
        if self.min is not None and not self.min <= item:
            return False
        if self.max is not None and not item <= self.max:
            return False
        return True

    def intersection(self, other: "RangeInclusive[T]") -> "RangeInclusive[T]":
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

        return RangeInclusive(_min, _max)