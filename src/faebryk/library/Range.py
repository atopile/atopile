# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from math import inf
from typing import Any, Protocol, Self

from faebryk.core.core import Parameter
from faebryk.library.Constant import Constant


class _SupportsRangeOps(Protocol):
    def __add__(self, __value) -> "_SupportsRangeOps": ...
    def __sub__(self, __value) -> "_SupportsRangeOps": ...
    def __mul__(self, __value) -> "_SupportsRangeOps": ...

    def __le__(self, __value) -> bool: ...
    def __lt__(self, __value) -> bool: ...
    def __ge__(self, __value) -> bool: ...


class Range[PV: _SupportsRangeOps](Parameter[PV]):
    type PV_or_PARAM = PV | Parameter[PV]

    class MinMaxError(Exception): ...

    def __init__(self, *bounds: PV | Parameter[PV]) -> None:
        super().__init__()

        self._bounds: list[Parameter[PV]] = [
            bound if isinstance(bound, Parameter) else Constant(bound)
            for bound in bounds
        ]

    def _get_narrowed_bounds(self) -> list[Parameter[PV]]:
        return list({b.get_most_narrow() for b in self._bounds})

    @property
    def min(self) -> Parameter[PV]:
        try:
            return min(self._get_narrowed_bounds())
        except TypeError:
            raise self.MinMaxError()

    @property
    def max(self) -> Parameter[PV]:
        try:
            return max(self._get_narrowed_bounds())
        except TypeError:
            raise self.MinMaxError()

    @property
    def bounds(self) -> list[Parameter[PV]]:
        try:
            return [self.min, self.max]
        except self.MinMaxError:
            return self._get_narrowed_bounds()

    def as_tuple(self) -> tuple[Parameter[PV], Parameter[PV]]:
        return (self.min, self.max)

    def as_center_tuple(self, relative=False) -> tuple[Parameter[PV], Parameter[PV]]:
        center = (self.min + self.max) / 2
        delta = (self.max - self.min) / 2
        if relative:
            delta /= center
        return center, delta

    @classmethod
    def from_center(cls, center: PV_or_PARAM, delta: PV_or_PARAM) -> "Range[PV]":
        return cls(center - delta, center + delta)

    @classmethod
    def from_center_rel(cls, center: PV, factor: PV) -> "Range[PV]":
        return cls.from_center(center, center * factor)

    @classmethod
    def _with_bound(cls, bound: PV_or_PARAM, other: float) -> "Range[PV]":
        from faebryk.core.util import with_same_unit

        try:
            other = with_same_unit(other, bound)
        except NotImplementedError:
            raise NotImplementedError("Specify zero/inf manually in params")

        return cls(bound, other)

    @classmethod
    def lower_bound(cls, lower: PV_or_PARAM) -> "Range[PV]":
        return cls._with_bound(lower, inf)

    @classmethod
    def upper_bound(cls, upper: PV_or_PARAM) -> "Range[PV]":
        return cls._with_bound(upper, 0)

    def __str__(self) -> str:
        bounds = map(str, self.bounds)
        return super().__str__() + f"({', '.join(bounds)})"

    def __repr__(self):
        bounds = map(repr, self.bounds)
        return super().__repr__() + f"({', '.join(bounds)})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Range):
            return False
        return self.bounds == other.bounds

    def __hash__(self) -> int:
        return sum(hash(b) for b in self._bounds)

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
        bounds = [format(b, format_spec) for b in self._get_narrowed_bounds()]
        return f"{super().__str__()}({', '.join(bounds)})"

    def __copy__(self) -> Self:
        return type(self)(*self._bounds)

    def get_most_narrow(self) -> Parameter[PV]:
        # out = super().get_most_narrow()
        ## compress into constant if possible
        # if out is self and len(set(map(id, self.bounds))) == 1:
        #    out.merge(self.bounds[0])
        return super().get_most_narrow()

    def __contains__(self, other: PV_or_PARAM) -> bool:
        return self.min <= other and self.max >= other
