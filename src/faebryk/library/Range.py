# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from math import inf
from typing import Any, Protocol, Self

from faebryk.core.parameter import Parameter
from faebryk.libs.units import UnitsContainer, to_si_str


class _SupportsRangeOps(Protocol):
    def __add__(self, __value) -> "_SupportsRangeOps": ...
    def __sub__(self, __value) -> "_SupportsRangeOps": ...
    def __mul__(self, __value) -> "_SupportsRangeOps": ...

    def __le__(self, __value) -> bool: ...
    def __lt__(self, __value) -> bool: ...
    def __ge__(self, __value) -> bool: ...


class Range[PV: _SupportsRangeOps](Parameter[PV], Parameter[PV].SupportsSetOps):
    type LIT_OR_PARAM = Parameter[PV].LIT_OR_PARAM

    class MinMaxError(Exception): ...

    def __init__(self, *bounds: PV | Parameter[PV]) -> None:
        super().__init__()

        self._bounds: list[Parameter[PV]] = [
            Parameter[PV].from_literal(b) for b in bounds
        ]

    def _get_narrowed_bounds(self) -> list[Parameter[PV]]:
        return list({b.get_most_narrow() for b in self._bounds})

    @property
    def min(self) -> Parameter[PV]:
        try:
            return min(self._get_narrowed_bounds())
        except (TypeError, ValueError):
            raise self.MinMaxError()

    @property
    def max(self) -> Parameter[PV]:
        try:
            return max(self._get_narrowed_bounds())
        except (TypeError, ValueError):
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
    def from_center(cls, center: LIT_OR_PARAM, delta: LIT_OR_PARAM) -> "Range[PV]":
        return cls(center - delta, center + delta)

    @classmethod
    def from_center_rel(cls, center: PV, factor: PV) -> "Range[PV]":
        return cls.from_center(center, center * factor)

    @classmethod
    def _with_bound(cls, bound: LIT_OR_PARAM, other: float) -> "Range[PV]":
        try:
            other_with_unit = Parameter.with_same_unit(bound, other)
        except NotImplementedError:
            raise NotImplementedError("Specify zero/inf manually in params")

        return cls(bound, other_with_unit)

    @classmethod
    def lower_bound(cls, lower: LIT_OR_PARAM) -> "Range[PV]":
        return cls._with_bound(lower, inf)

    @classmethod
    def upper_bound(cls, upper: LIT_OR_PARAM) -> "Range[PV]":
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

    def try_compress(self) -> Parameter[PV]:
        # compress into constant if possible
        if len(set(map(id, self.bounds))) == 1:
            return Parameter.from_literal(self.bounds[0])
        return super().try_compress()

    def __contains__(self, other: LIT_OR_PARAM) -> bool:
        return self.min <= other and self.max >= other

    def _max(self):
        return max(p.get_max() for p in self._get_narrowed_bounds())

    def _as_unit(self, unit: UnitsContainer, base: int, required: bool) -> str:
        return (
            self.min.as_unit(unit, base=base)
            + " - "
            + self.max.as_unit(unit, base=base, required=True)
        )

    def _as_unit_with_tolerance(
        self, unit: UnitsContainer, base: int, required: bool
    ) -> str:
        center, delta = self.as_center_tuple(relative=True)
        delta_percent_str = f"±{to_si_str(delta.value, "%", 0)}"
        return (
            f"{center.as_unit(unit, base=base, required=required)} {delta_percent_str}"
        )

    def _enum_parameter_representation(self, required: bool) -> str:
        return (
            f"{self.min.enum_parameter_representation(required)} - "
            f"{self.max.enum_parameter_representation(required)}"
        )
