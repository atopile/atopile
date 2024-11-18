# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections.abc import Generator
from typing import Any, TypeVar, cast

from faebryk.libs.sets.numeric_sets import (
    Numeric_Interval,
    Numeric_Interval_Disjoint,
    NumericT,
)
from faebryk.libs.sets.sets import P_UnitSet
from faebryk.libs.units import (
    HasUnit,
    Quantity,
    Unit,
    dimensionless,
    quantity,
)
from faebryk.libs.util import cast_assert, not_none

logger = logging.getLogger(__name__)

# Types --------------------------------------------------------------------------------


QuantityT = TypeVar(
    "QuantityT",
    int,
    float,
    Quantity,
    # Unit,
    contravariant=False,
    covariant=False,
)

type QuantityLike = Quantity | int | float  # | Unit
QuantityLikeR = (Quantity, int, float)


type Numeric = int | float

Quantity_Interval_DisjointT = TypeVar(
    "Quantity_Interval_DisjointT", bound="Quantity_Interval_Disjoint"
)

# Helpers ------------------------------------------------------------------------------


def base_units(units: Unit) -> Unit:
    return cast(Unit, Quantity(1, units).to_base_units().units)


# --------------------------------------------------------------------------------------


class Quantity_Set(P_UnitSet[QuantityLike]):
    pass


class Quantity_Interval(Quantity_Set):
    """
    Continuous interval (min < max) with min, max having the same units.
    """

    def __init__(
        self,
        min: QuantityLike | None = None,
        max: QuantityLike | None = None,
        units: Unit | None = None,
    ):
        if min is None and max is None:
            raise ValueError("must provide at least one of min or max")

        min_unit = None
        if min is not None:
            min_unit = HasUnit.get_units_or_dimensionless(min)
            if units and not min_unit.is_compatible_with(units):
                raise ValueError("min incompatible with units")
        max_unit = None
        if max is not None:
            max_unit = HasUnit.get_units_or_dimensionless(max)
            if units and not max_unit.is_compatible_with(units):
                raise ValueError("max incompatible with units")

        if (
            min_unit is not None
            and max_unit is not None
            and not min_unit.is_compatible_with(max_unit)
        ):
            raise ValueError("min and max must have the same units")

        self.units = not_none(units or min_unit or max_unit)
        self.interval_units = base_units(self.units)

        if isinstance(min, Quantity):
            num_min = min.to_base_units().magnitude
            if not isinstance(num_min, (float, int)):
                raise ValueError("min must be a float or int quantity")
        else:
            num_min = min

        if isinstance(max, Quantity):
            num_max = max.to_base_units().magnitude
            if not isinstance(num_max, (float, int)):
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

        self._interval = Numeric_Interval(num_min, num_max)

    @staticmethod
    def from_center(center: QuantityLike, abs_tol: QuantityLike) -> "Quantity_Interval":
        left = cast_assert(QuantityLikeR, center - abs_tol)
        right = cast_assert(QuantityLikeR, center + abs_tol)
        return Quantity_Interval(left, right)

    @staticmethod
    def from_center_rel(center: QuantityLike, rel_tol: float) -> "Quantity_Interval":
        return Quantity_Interval(
            cast_assert(QuantityLikeR, center - center * rel_tol),
            cast_assert(QuantityLikeR, center + center * rel_tol),
        )

    @staticmethod
    def _from_interval(interval: Numeric_Interval, units: Unit) -> "Quantity_Interval":
        return Quantity_Interval(
            min=quantity(interval._min, base_units(units)),
            max=quantity(interval._max, base_units(units)),
            units=units,
        )

    def as_center_tuple(self, relative: bool = False) -> tuple[QuantityT, QuantityT]:
        center = cast_assert(QuantityLikeR, (self.min_elem() + self.max_elem())) / 2
        delta = (self.max_elem() - self.min_elem()) / 2
        if relative:
            delta /= center
        assert isinstance(center, QuantityLikeR)
        assert isinstance(delta, type(center))
        return center, delta  # type: ignore

    def base_to_units(self, value: NumericT) -> Quantity:
        return cast_assert(
            Quantity, quantity(value, self.interval_units).to(self.units)
        )

    def min_elem(self) -> Quantity:
        return self.base_to_units(self._interval.min_elem())

    def max_elem(self) -> Quantity:
        return self.base_to_units(self._interval.max_elem())

    def is_empty(self) -> bool:
        return self._interval.is_empty()

    def is_unbounded(self) -> bool:
        return self._interval.is_unbounded()

    def op_intersect_interval(
        self, other: "Quantity_Interval"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            return Quantity_Interval_Disjoint(units=self.units)
        _interval = self._interval.op_intersect_interval(other._interval)
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_add_interval(self, other: "Quantity_Interval") -> "Quantity_Interval":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._interval.op_add_interval(other._interval)
        return Quantity_Interval._from_interval(_interval, self.units)

    def op_negate(self) -> "Quantity_Interval":
        _interval = self._interval.op_negate()
        return Quantity_Interval._from_interval(_interval, self.units)

    def op_subtract_interval(self, other: "Quantity_Interval") -> "Quantity_Interval":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._interval.op_subtract_interval(other._interval)
        return Quantity_Interval._from_interval(_interval, self.units)

    def op_mul_interval(self, other: "Quantity_Interval") -> "Quantity_Interval":
        _interval = self._interval.op_mul_interval(other._interval)
        return Quantity_Interval._from_interval(
            _interval, cast(Unit, self.units * other.units)
        )

    def op_invert(self) -> "Quantity_Interval_Disjoint":
        _interval = self._interval.op_invert()
        return Quantity_Interval_Disjoint._from_intervals(_interval, 1 / self.units)

    def op_div_interval(
        self, other: "Quantity_Interval"
    ) -> "Quantity_Interval_Disjoint":
        _interval = self._interval.op_div_interval(other._interval)
        return Quantity_Interval_Disjoint._from_intervals(
            _interval, cast(Unit, self.units / other.units)
        )

    # def __copy__(self) -> Self:
    #    r = Quantity_interval.__new__(Quantity_interval)
    #    r.min = self.min
    #    r.max = self.max
    #    r.empty = self.empty
    #    r.units = self.units
    #    return r

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, Quantity):
            if not item.units.is_compatible_with(self.units):
                return False
            item = item.to(self.interval_units).magnitude
            if not isinstance(item, float) and not isinstance(item, int):
                return False
            return self._interval.__contains__(item)
        return False

    # yucky with floats
    def __eq__(self, value: Any) -> bool:
        if not HasUnit.check(value):
            return False
        if not self.units.is_compatible_with(value.units):
            return False
        if isinstance(value, Quantity_Interval):
            return self._interval == value._interval
        if (
            isinstance(value, Quantity_Interval_Disjoint)
            and len(value._intervals.intervals) == 1
        ):
            return self._interval == value._intervals.intervals[0]
        return False

    # TODO, convert to base unit first
    def __hash__(self) -> int:
        return hash((self._interval, self.interval_units))

    def __repr__(self) -> str:
        if self.units.is_compatible_with(dimensionless):
            return f"Quantity_interval({self._interval._min}, {self._interval._max})"
        return (
            f"Quantity_interval({self.base_to_units(self._interval._min)}, "
            f"{self.base_to_units(self._interval._max)} | {self.units})"
        )


class Quantity_Singleton(Quantity_Interval):
    """
    Single value.
    Represented by a Quantity interval with min == max.
    """

    def __init__(self, value: QuantityLike):
        super().__init__(min=value, max=value)

    def get_value(self) -> Quantity:
        return self.min_elem()

    def __iter__(self) -> Generator[Quantity]:
        yield self.min_elem()

    @classmethod
    def cast(cls, value: Quantity_Interval) -> "Quantity_Singleton":
        if value.min_elem() != value.max_elem():
            raise ValueError(f"Interval is not a singleton: {value}")
        return cls(value.min_elem())


class Quantity_Interval_Disjoint(Quantity_Set):
    """
    Quantity interval (min < max) with gaps. \n
    Represented by Set of multiple Quantity interval (without gaps).
    """

    def __init__(
        self,
        *intervals: "Quantity_Interval | Quantity_Interval_Disjoint | tuple[QuantityLike, QuantityLike]",
        units: Unit | None = None,
    ):
        proper_intervals = [
            Quantity_Interval(r[0], r[1]) if isinstance(r, tuple) else r
            for r in intervals
        ]
        interval_units = [
            HasUnit.get_units_or_dimensionless(r) for r in proper_intervals
        ]
        if len(interval_units) == 0 and units is None:
            raise ValueError("units must be provided for empty union")
        self.units = units or interval_units[0]
        self.interval_units = base_units(self.units)
        if not all(self.units.is_compatible_with(u) for u in interval_units):
            raise ValueError("all elements must have compatible units")

        def get_backing(r: "Quantity_Interval | Quantity_Interval_Disjoint"):
            if isinstance(r, Quantity_Interval):
                return r._interval
            else:
                return r._intervals

        self._intervals = Numeric_Interval_Disjoint(
            *(get_backing(r) for r in proper_intervals)
        )

    @classmethod
    def _from_intervals(
        cls: type[Quantity_Interval_DisjointT],
        intervals: "Numeric_Interval_Disjoint[NumericT]",
        units: Unit,
    ) -> Quantity_Interval_DisjointT:
        r = cls.__new__(cls)
        r._intervals = intervals
        r.units = units
        r.interval_units = base_units(units)
        return r

    def is_empty(self) -> bool:
        return self._intervals.is_empty()

    def base_to_units(self, value: NumericT) -> Quantity:
        return cast_assert(
            Quantity, quantity(value, self.interval_units).to(self.units)
        )

    def min_elem(self) -> Quantity:
        if self.is_empty():
            raise ValueError("empty interval cannot have min element")
        return self.base_to_units(self._intervals.min_elem())

    def max_elem(self) -> Quantity:
        if self.is_empty():
            raise ValueError("empty interval cannot have max element")
        return self.base_to_units(self._intervals.max_elem())

    def closest_elem(self, target: Quantity) -> Quantity:
        if not self.units.is_compatible_with(target.units):
            raise ValueError("incompatible units")
        return self.base_to_units(
            self._intervals.closest_elem(target.to(self.interval_units).magnitude)
        )

    def is_superset_of(self, other: "Quantity_Interval_Disjoint") -> bool:
        if not self.units.is_compatible_with(other.units):
            return False
        return self._intervals.is_superset_of(other._intervals)

    def is_subset_of(self, other: "Quantity_Interval_Disjoint") -> bool:
        return other.is_superset_of(self)

    def op_intersect_interval(
        self, other: "Quantity_Interval"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._intervals.op_intersect_interval(other._interval)
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_intersect_intervals(
        self, *other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        # TODO make pretty
        def single(left, right):
            if not left.units.is_compatible_with(right.units):
                raise ValueError("incompatible units")
            _interval = left._intervals.op_intersect_intervals(right._intervals)
            return Quantity_Interval_Disjoint._from_intervals(_interval, left.units)

        out = Quantity_Interval_Disjoint(self)

        for o in other:
            out = single(out, o)

        return out

    def op_union_intervals(
        self, other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._intervals.op_union_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_add_intervals(
        self, other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._intervals.op_add_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def __add__(self, other) -> "Quantity_Interval_Disjoint":
        if isinstance(other, Quantity_Interval_Disjoint):
            return self.op_add_intervals(other)
        elif isinstance(other, Quantity_Interval):
            return self.op_add_intervals(Quantity_Interval_Disjoint(other))
        elif isinstance(other, Quantity):
            return self.op_add_intervals(Quantity_Set_Discrete(other))
        elif isinstance(other, int) or isinstance(other, float):
            return self.op_add_intervals(
                Quantity_Set_Discrete(cast_assert(Quantity, other * dimensionless))
            )
        return NotImplemented

    def __radd__(self, other) -> "Quantity_Interval_Disjoint":
        return self + other

    def op_negate(self) -> "Quantity_Interval_Disjoint":
        _interval = self._intervals.op_negate()
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_subtract_intervals(
        self, other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._intervals.op_subtract_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_mul_intervals(
        self, other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._intervals.op_mul_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(
            _interval, cast(Unit, self.units * other.units)
        )

    def op_invert(self) -> "Quantity_Interval_Disjoint":
        _interval = self._intervals.op_invert()
        return Quantity_Interval_Disjoint._from_intervals(_interval, 1 / self.units)

    def op_div_intervals(
        self, other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._intervals.op_div_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(
            _interval, cast(Unit, self.units / other.units)
        )

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, Quantity):
            if not item.units.is_compatible_with(self.units):
                return False
            item = item.to(self.interval_units).magnitude
            if not isinstance(item, float) and not isinstance(item, int):
                return False
            return self._intervals.__contains__(item)
        return False

    def __eq__(self, value: Any) -> bool:
        if not HasUnit.check(value):
            return False
        if not self.units.is_compatible_with(value.units):
            return False
        if isinstance(value, Quantity_Interval_Disjoint):
            return self._intervals == value._intervals
        if isinstance(value, Quantity_Interval) and len(self._intervals.intervals) == 1:
            return self._intervals.intervals[0] == value._interval
        return False

    def __hash__(self) -> int:
        return hash((self._intervals, self.interval_units))

    def __repr__(self) -> str:
        if self.units.is_compatible_with(dimensionless):
            inner = ", ".join(
                f"[{r._min}, {r._max}]" for r in self._intervals.intervals
            )
            return f"Quantity_intervals({inner})"
        inner = ", ".join(
            f"[{self.base_to_units(r._min)}, {self.base_to_units(r._max)}]"
            for r in self._intervals.intervals
        )
        return f"Quantity_intervals({inner} | {self.units})"

    def __iter__(self) -> Generator[Quantity_Interval]:
        for r in self._intervals.intervals:
            yield Quantity_Interval._from_interval(r, self.units)

    def is_unbounded(self) -> bool:
        if self.is_empty():
            return False
        return next(iter(self)).is_unbounded()


class Quantity_Set_Discrete(Quantity_Interval_Disjoint):
    """
    Quantity Set of single values. \n
    Represented by Set of multiple Quantity Interval
    (each containing only a single value, aka a Quantity Singleton).
    """

    def __init__(self, *values: QuantityLike, units: Unit | None = None):
        super().__init__(*(Quantity_Singleton(v) for v in values), units=units)

    def iter_singles(self) -> Generator[Quantity]:
        for r in self._intervals.intervals:
            yield self.base_to_units(r._min)


def Quantity_Set_Empty(
    units: Unit | None = None,
) -> Quantity_Interval_Disjoint:
    """
    Empty Quantity Set.
    Represented by empty Quantity_Interval_Disjoint.
    """

    if units is None:
        units = dimensionless
    return Quantity_Interval_Disjoint(units=units)
