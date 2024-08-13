# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from math import inf
from typing import Any, Generic, Protocol, TypeVar

from faebryk.core.core import Parameter
from faebryk.library.Constant import Constant
from faebryk.library.is_representable_by_single_value_defined import (
    is_representable_by_single_value_defined,
)
from faebryk.libs.exceptions import FaebrykException

X = TypeVar("X", bound="_SupportsRangeOps")


class _SupportsRangeOps(Protocol):
    def __add__(self, __value: X) -> X: ...

    def __sub__(self, __value: X) -> X: ...

    def __mul__(self, __value: X) -> X: ...

    def __le__(self, __value: X) -> bool: ...

    def __lt__(self, __value: X) -> bool: ...

    def __ge__(self, __value: X) -> bool: ...


PV = TypeVar("PV", bound=_SupportsRangeOps)


class Range(Generic[PV], Parameter[PV]):
    def __init__(self, bound1: PV, bound2: PV) -> None:
        super().__init__()

        # TODO this should not be here, but be dynamically resolved during comparison
        if isinstance(bound1, Range):
            bound1 = bound1.min

        if isinstance(bound2, Range):
            bound2 = bound2.max

        self.bounds = tuple(
            bound if isinstance(bound, Parameter) else Constant(bound)
            for bound in (bound1, bound2)
        )

    def _get_narrowed_bounds(self) -> tuple[PV, PV]:
        return [b.get_most_narrow() for b in self.bounds]

    @property
    def min(self) -> PV:
        return min(self._get_narrowed_bounds())

    @property
    def max(self) -> PV:
        return max(self._get_narrowed_bounds())

    def pick(self, value_to_check: PV):
        if not self.min <= value_to_check <= self.max:
            raise FaebrykException(
                f"Value not in range: {value_to_check} not in [{self.min},{self.max}]"
            )
        self.add_trait(is_representable_by_single_value_defined(value_to_check))

    def contains(self, value_to_check: PV) -> bool:
        return self.min <= value_to_check <= self.max

    def as_tuple(self) -> tuple[PV, PV]:
        return (self.min, self.max)

    def as_center_tuple(self) -> tuple[PV, PV]:
        return (self.min + self.max) / 2, (self.max - self.min) / 2

    @classmethod
    def from_center(cls, center: PV, delta: PV) -> "Range[PV]":
        return cls(center - delta, center + delta)

    @classmethod
    def from_center_rel(cls, center: PV, factor: PV) -> "Range[PV]":
        return cls.from_center(center, center * factor)

    @classmethod
    def lower_bound(cls, lower: PV) -> "Range[PV]":
        # TODO range should take params as bounds
        return cls(lower, inf)

    @classmethod
    def upper_bound(cls, upper: PV) -> "Range[PV]":
        # TODO range should take params as bounds
        return cls(0, upper)

    def __str__(self) -> str:
        bounds = self._get_narrowed_bounds()
        return super().__str__() + f"({bounds[0]} <-> {bounds[1]})"

    def __repr__(self):
        bounds = self._get_narrowed_bounds()
        return super().__repr__() + f"({bounds[0]!r} <-> {bounds[1]!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Range):
            return False
        return set(self.bounds) == set(other.bounds)

    def __hash__(self) -> int:
        return hash(self.bounds)

    # comparison operators
    def __le__(self, other) -> bool:
        return self.max <= other

    def __lt__(self, other) -> bool:
        return self.max < other

    def __ge__(self, other) -> bool:
        return self.min >= other

    def __gt__(self, other) -> bool:
        return self.min > other

    def __format__(self, format_spec):
        return (
            f"{super().__str__()}({format(self.bounds[0], format_spec)} <-> "
            f"{format(self.bounds[1], format_spec)})"
        )
