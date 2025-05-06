# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from collections.abc import Generator
from typing import Any, TypeVar, cast, override

from faebryk.libs.sets.numeric_sets import (
    Number,
    NumberLike,
    NumberLikeR,
    Numeric_Interval,
    Numeric_Interval_Disjoint,
)
from faebryk.libs.sets.sets import BoolSet, P_Set, P_UnitSet
from faebryk.libs.units import (
    HasUnit,
    Quantity,
    Unit,
    dimensionless,
    quantity,
    to_si_str,
)
from faebryk.libs.util import (
    cast_assert,
    not_none,
    once,
    operator_type_check,
    round_str,
)

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

type QuantityLike = Quantity | NumberLike  # | Unit
QuantityLikeR = (Quantity, *NumberLikeR)


type Numeric = int | float

Quantity_Interval_DisjointT = TypeVar(
    "Quantity_Interval_DisjointT", bound="Quantity_Interval_Disjoint"
)

type QuantitySetLike = Quantity_Set | QuantityLike | tuple[QuantityLike, QuantityLike]

# Helpers ------------------------------------------------------------------------------


def base_units(units: Unit) -> Unit:
    return cast(Unit, Quantity(1, units).to_base_units().units)


# --------------------------------------------------------------------------------------


class Quantity_Set(P_UnitSet[QuantityLike]):
    def __init__(self, units: Unit):
        super().__init__()
        self.units = units
        self.interval_units = base_units(units)

    def base_to_units(self, value: Number) -> Quantity:
        return cast_assert(
            Quantity, quantity(value, self.interval_units).to(self.units)
        )

    def _format_number(self, number: Number, num_decimals: int = 12) -> str:
        if self.units.is_compatible_with(dimensionless):
            if math.isinf(number):
                return "∞" if number > 0 else "-∞"
            if number == 0:
                return "0"
            rel_dif = abs((number - round(number)) / number)
            if rel_dif < 1e-6:
                return round_str(number, 0)
            return round_str(number, num_decimals)

        # ignore num_decimals because si prefixes scale the number
        return to_si_str(self.base_to_units(number), self.units, num_decimals=3)

    @override
    def serialize_pset(self) -> dict:
        return Quantity_Interval_Disjoint.from_value(self).serialize_pset()

    @override
    @classmethod
    def deserialize_pset(cls, data: dict):
        return Quantity_Interval_Disjoint.deserialize(data)


QuantitySetLikeR = (Quantity_Set, *QuantityLikeR)


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

        super().__init__(not_none(units or min_unit or max_unit))

        if isinstance(min, Quantity):
            num_min = min.to_base_units().magnitude
            if not isinstance(num_min, (float, int, Number)):
                raise ValueError("min must be a float or int quantity")
        else:
            num_min = min

        if isinstance(max, Quantity):
            num_max = max.to_base_units().magnitude
            if not isinstance(num_max, (float, int, Number)):
                raise ValueError("max must be a float or int quantity")
        else:
            num_max = max

        is_int = isinstance(num_min, int) and isinstance(num_max, int)
        if not is_int:
            num_min = float(num_min) if num_min is not None else float("-inf")
            num_max = float(num_max) if num_max is not None else float("inf")
        assert num_min is not None and num_max is not None

        self._interval = Numeric_Interval(num_min, num_max)

    @staticmethod
    def from_center(center: QuantityLike, abs_tol: QuantityLike) -> "Quantity_Interval":
        if isinstance(center, float):
            center = Number(center)
        if isinstance(center, Quantity) and not isinstance(center.magnitude, Number):
            center = Quantity(Number(center.magnitude), center.units)  # type: ignore
            assert isinstance(center, Quantity)
        if isinstance(abs_tol, float):
            abs_tol = Number(abs_tol)
        if isinstance(abs_tol, Quantity) and not isinstance(abs_tol.magnitude, Number):
            abs_tol = Quantity(Number(abs_tol.magnitude), abs_tol.units)  # type: ignore
            assert isinstance(abs_tol, Quantity)
        left = cast_assert(QuantityLikeR, center - abs_tol)
        right = cast_assert(QuantityLikeR, center + abs_tol)
        return Quantity_Interval(left, right)

    @staticmethod
    def from_center_rel(
        center: QuantityLike, rel_tol: float | Number
    ) -> "Quantity_Interval":
        if isinstance(center, float):
            center = Number(center)
        if isinstance(center, Quantity) and not isinstance(center.magnitude, Number):
            center = Quantity(Number(center.magnitude), center.units)  # type: ignore
            assert isinstance(center, Quantity)
        if isinstance(rel_tol, float):
            rel_tol = Number(rel_tol)
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
        center = cast_assert(QuantityLikeR, (self.min_elem + self.max_elem)) / 2
        delta = (self.max_elem - self.min_elem) / 2
        if relative:
            delta /= center
        assert isinstance(center, QuantityLikeR)
        assert isinstance(delta, type(center))
        return center, delta  # type: ignore

    @property
    @once
    def min_elem(self) -> Quantity:
        return self.base_to_units(self._interval.min_elem)

    @property
    @once
    def max_elem(self) -> Quantity:
        return self.base_to_units(self._interval.max_elem)

    def is_empty(self) -> bool:
        return self._interval.is_empty()

    def is_unbounded(self) -> bool:
        return self._interval.is_unbounded()

    @override
    def is_finite(self) -> bool:
        return self._interval.is_finite()

    def is_subset_of(self, other: "Quantity_Interval") -> bool:
        return self._interval.is_subset_of(other._interval)

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
        if isinstance(item, (float, int, Number)):
            item = quantity(item)
        if isinstance(item, Quantity):
            if not item.units.is_compatible_with(self.units):
                return False
            item = item.to(self.interval_units).magnitude
        if not isinstance(item, float) and not isinstance(item, int):
            return False
        return self._interval.__contains__(item)

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
        return f"Quantity_Interval({self})"

    def __str__(self) -> str:
        min_ = self._format_number(self._interval._min)
        max_ = self._format_number(self._interval._max)
        if min_ == max_:
            return f"[{min_}]"
        center, rel = self._interval.as_center_rel()
        if rel < 0.5 and round(rel, 2) == rel:
            return f"[{self._format_number(center)} ± {rel * 100:.2f}%]"
        return f"[{min_}, {max_}]"

    # operators
    @operator_type_check
    def __add__(self, other: "Quantity_Interval"):
        return self.op_add_interval(other)

    @operator_type_check
    def __sub__(self, other: "Quantity_Interval"):
        return self.op_subtract_interval(other)

    @operator_type_check
    def __neg__(self):
        return self.op_negate()

    @operator_type_check
    def __mul__(self, other: "Quantity_Interval"):
        return self.op_mul_interval(other)

    @operator_type_check
    def __truediv__(self, other: "Quantity_Interval"):
        return self.op_div_interval(other)

    @operator_type_check
    def __and__(self, other: "Quantity_Interval"):
        return self.op_intersect_interval(other)

    @once
    def is_single_element(self) -> bool:
        return self.min_elem == self.max_elem  # type: ignore #TODO

    @override
    def any(self) -> Quantity:
        return self.min_elem


class Quantity_Singleton(Quantity_Interval):
    """
    Single value.
    Represented by a Quantity interval with min == max.
    """

    def __init__(self, value: QuantityLike):
        # FIXME: handle inf Quantity too
        if value == float("inf") or value == float("-inf"):
            raise ValueError("value cannot be infinity for quantity singleton")

        super().__init__(min=value, max=value)

    def get_value(self) -> Quantity:
        return self.min_elem

    def __iter__(self) -> Generator[Quantity]:
        yield self.min_elem

    @classmethod
    def cast(cls, value: Quantity_Interval) -> "Quantity_Singleton":
        if value.min_elem != value.max_elem:
            raise ValueError(f"Interval is not a singleton: {value}")
        return cls(value.min_elem)


class Quantity_Interval_Disjoint(Quantity_Set):
    """
    Quantity interval (min < max) with gaps. \n
    Represented by Set of multiple Quantity interval (without gaps).
    """

    def __init__(
        self,
        *intervals: "Quantity_Interval | Quantity_Interval_Disjoint | tuple[QuantityLike, QuantityLike]",  # noqa: E501
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

        super().__init__(units or interval_units[0])

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
        intervals: "Numeric_Interval_Disjoint",
        units: Unit,
    ) -> Quantity_Interval_DisjointT:
        r = cls.__new__(cls)
        r._intervals = intervals
        r.units = units
        r.interval_units = base_units(units)
        return r

    @classmethod
    def unbounded(
        cls: type[Quantity_Interval_DisjointT], units: Unit
    ) -> Quantity_Interval_DisjointT:
        return cls(Quantity_Interval(units=units))

    def is_empty(self) -> bool:
        return self._intervals.is_empty()

    @property
    @once
    def min_elem(self) -> Quantity:
        if self.is_empty():
            raise ValueError("empty interval cannot have min element")
        return self.base_to_units(self._intervals.min_elem)

    @property
    @once
    def max_elem(self) -> Quantity:
        if self.is_empty():
            raise ValueError("empty interval cannot have max element")
        return self.base_to_units(self._intervals.max_elem)

    def closest_elem(self, target: Quantity) -> Quantity:
        if not self.units.is_compatible_with(target.units):
            raise ValueError("incompatible units")
        return self.base_to_units(
            self._intervals.closest_elem(target.to(self.interval_units).magnitude)
        )

    def is_superset_of(self, other: "Quantity_Interval_Disjoint") -> bool:
        if not self.units.is_compatible_with(other.units):
            return False
        return self._intervals.is_superset_of(
            Quantity_Interval_Disjoint.from_value(other)._intervals
        )

    def is_subset_of(self, other: "Quantity_Interval_Disjoint") -> bool:
        if not self.units.is_compatible_with(other.units):
            return False
        return self._intervals.is_subset_of(
            Quantity_Interval_Disjoint.from_value(other)._intervals
        )

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

    def op_difference_intervals(
        self, other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._intervals.op_difference_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_symmetric_difference_intervals(
        self, other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._intervals.op_symmetric_difference_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_add_intervals(
        self, other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(other.units):
            raise ValueError("incompatible units")
        _interval = self._intervals.op_add_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

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
        _interval = self._intervals.op_div_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(
            _interval, cast(Unit, self.units / other.units)
        )

    def op_pow_intervals(
        self, other: "Quantity_Interval_Disjoint"
    ) -> "Quantity_Interval_Disjoint":
        if not other.units.is_compatible_with(dimensionless):
            raise ValueError("exponent must have dimensionless units")
        if other.min_elem != other.max_elem and not self.units.is_compatible_with(
            dimensionless
        ):
            raise ValueError(
                "base must have dimensionless units when exponent is interval"
            )
        units = self.units**other.min_elem.magnitude
        _interval = self._intervals.op_pow_intervals(other._intervals)
        return Quantity_Interval_Disjoint._from_intervals(_interval, units)

    def op_round(self, ndigits: int = 0) -> "Quantity_Interval_Disjoint":
        _interval = self._intervals.op_round(ndigits)
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_abs(self) -> "Quantity_Interval_Disjoint":
        _interval = self._intervals.op_abs()
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_log(self) -> "Quantity_Interval_Disjoint":
        _interval = self._intervals.op_log()
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_sqrt(self) -> "Quantity_Interval_Disjoint":
        return self**0.5

    def op_sin(self) -> "Quantity_Interval_Disjoint":
        if not self.units.is_compatible_with(dimensionless):
            raise ValueError("sin only defined for dimensionless quantities")
        _interval = self._intervals.op_sin()
        return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    def op_cos(self) -> "Quantity_Interval_Disjoint":
        return (self + quantity(math.pi / 2, self.units)).op_sin()

    def op_floor(self) -> "Quantity_Interval_Disjoint":
        return (self - quantity(0.5, self.units)).op_round()

    def op_ceil(self) -> "Quantity_Interval_Disjoint":
        return (self + quantity(0.5, self.units)).op_round()

    def op_total_span(self) -> Quantity:
        """Returns the sum of the spans of all intervals in this disjoint set.
        For a single interval, this is equivalent to max - min.
        For multiple intervals, this sums the spans of each disjoint interval."""
        return quantity(
            sum(abs(r.max_elem - r.min_elem) for r in self._intervals), self.units
        )

    def op_deviation_to(
        self, other: QuantitySetLike, relative: bool = False
    ) -> Quantity:
        try:
            other_qty = Quantity_Interval_Disjoint.from_value(other)
        except ValueError:
            return NotImplemented
        sym_diff = self.op_symmetric_difference_intervals(other_qty)
        deviation = sym_diff.op_total_span()
        if relative:
            deviation /= max(abs(self).max_elem, abs(other_qty).max_elem)
        return deviation

    def op_is_bit_set(self, other: QuantitySetLike) -> BoolSet:
        other_qty = Quantity_Interval_Disjoint.from_value(other)
        if not self.is_single_element() or not other_qty.is_single_element():
            return BoolSet(False, True)
        # TODO more checking
        return BoolSet((int(self.any()) >> int(other_qty.any())) & 1 == 1)

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, (float, int, Number)):
            item = quantity(item)
        if isinstance(item, Quantity):
            if not item.units.is_compatible_with(self.units):
                return False
            item = item.to(self.interval_units).magnitude
        if not isinstance(item, float) and not isinstance(item, int):
            return False
        return self._intervals.__contains__(item)

    @once
    def __hash__(self) -> int:
        return hash((self._intervals, self.interval_units))

    @once
    def __repr__(self) -> str:
        return f"Quantity_Interval_Disjoint({self})"

    @once
    def __str__(self) -> str:
        def _format_interval(r: Numeric_Interval) -> str:
            if r._min == r._max:
                return f"[{self._format_number(r._min)}]"
            try:
                center, rel = r.as_center_rel()
                if rel < 0.5 and round(rel, 2) == rel:
                    return f"[{self._format_number(center)} ± {rel * 100:.2f}%]"
            except ZeroDivisionError:
                pass

            return f"[{self._format_number(r._min)}, {self._format_number(r._max)}]"

        out = ", ".join(_format_interval(r) for r in self._intervals.intervals)

        return f"({out})"

    def __iter__(self) -> Generator[Quantity_Interval]:
        for r in self._intervals.intervals:
            yield Quantity_Interval._from_interval(r, self.units)

    def is_unbounded(self) -> bool:
        return self._intervals.is_unbounded()

    @override
    def is_finite(self) -> bool:
        return self._intervals.is_finite()

    # operators
    @staticmethod
    def from_value(other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        if isinstance(other, Quantity_Interval_Disjoint):
            return other
        if isinstance(other, Quantity_Singleton):
            return Quantity_Set_Discrete(other.get_value())
        if isinstance(other, Quantity_Interval):
            return Quantity_Interval_Disjoint(other)
        if isinstance(other, Quantity):
            return Quantity_Set_Discrete(other)
        if isinstance(other, tuple) and len(other) == 2:
            return Quantity_Interval_Disjoint(other)
        if isinstance(other, NumberLike):
            return Quantity_Set_Discrete(quantity(other))
        raise ValueError(f"unsupported type: {type(other)}")

    @staticmethod
    def intersect_all(*obj: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        if not obj:
            return Quantity_Set_Empty()
        intersected = Quantity_Interval_Disjoint.from_value(obj[0])
        for o in obj[1:]:
            intersected = intersected & Quantity_Interval_Disjoint.from_value(o)
        return intersected

    def __eq__(self, value: Any) -> bool:
        if value is None:
            return False
        if not isinstance(value, QuantitySetLikeR):
            return False
        value_q = Quantity_Interval_Disjoint.from_value(value)
        return self._intervals == value_q._intervals

    def __add__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        try:
            other_qty = Quantity_Interval_Disjoint.from_value(other)
        except ValueError:
            return NotImplemented
        return self.op_add_intervals(other_qty)

    def __radd__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        return self + other

    def __sub__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        try:
            other_qty = Quantity_Interval_Disjoint.from_value(other)
        except ValueError:
            return NotImplemented
        return self.op_subtract_intervals(other_qty)

    def __rsub__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        return -self + other

    def __neg__(self) -> "Quantity_Interval_Disjoint":
        return self.op_negate()

    def __mul__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        try:
            other_qty = Quantity_Interval_Disjoint.from_value(other)
        except ValueError:
            return NotImplemented
        return self.op_mul_intervals(other_qty)

    def __rmul__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        return self * other

    def __truediv__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        try:
            other_qty = Quantity_Interval_Disjoint.from_value(other)
        except ValueError:
            return NotImplemented
        return self.op_div_intervals(other_qty)

    def __rtruediv__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        return self.op_invert() * Quantity_Interval_Disjoint.from_value(other)

    def __pow__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        return self.op_pow_intervals(Quantity_Interval_Disjoint.from_value(other))

    def __and__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        try:
            other_qty = Quantity_Interval_Disjoint.from_value(other)
        except ValueError:
            return NotImplemented
        return self.op_intersect_intervals(other_qty)

    def __rand__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        return Quantity_Interval_Disjoint.from_value(other) & self

    def __or__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        try:
            other_qty = Quantity_Interval_Disjoint.from_value(other)
        except ValueError:
            return NotImplemented
        return self.op_union_intervals(other_qty)

    def __ror__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        return Quantity_Interval_Disjoint.from_value(other) | self

    def __xor__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        try:
            other_qty = Quantity_Interval_Disjoint.from_value(other)
        except ValueError:
            return NotImplemented
        return self.op_symmetric_difference_intervals(other_qty)

    def __rxor__(self, other: QuantitySetLike) -> "Quantity_Interval_Disjoint":
        return Quantity_Interval_Disjoint.from_value(other) ^ self

    def __ge__(self, other: QuantitySetLike) -> BoolSet:
        other_q = Quantity_Interval_Disjoint.from_value(other)
        if not self.units.is_compatible_with(other_q.units):
            raise ValueError("incompatible units")
        return self._intervals >= other_q._intervals

    def __gt__(self, other: QuantitySetLike) -> BoolSet:
        other_q = Quantity_Interval_Disjoint.from_value(other)
        if not self.units.is_compatible_with(other_q.units):
            raise ValueError("incompatible units")
        return self._intervals > other_q._intervals

    def __le__(self, other: QuantitySetLike) -> BoolSet:
        other_q = Quantity_Interval_Disjoint.from_value(other)
        if not self.units.is_compatible_with(other_q.units):
            raise ValueError("incompatible units")
        return self._intervals <= other_q._intervals

    def __lt__(self, other: QuantitySetLike) -> BoolSet:
        other_q = Quantity_Interval_Disjoint.from_value(other)
        if not self.units.is_compatible_with(other_q.units):
            raise ValueError("incompatible units")
        return self._intervals < other_q._intervals

    def __round__(self, ndigits: int = 0) -> "Quantity_Interval_Disjoint":
        return self.op_round(ndigits)

    def __abs__(self) -> "Quantity_Interval_Disjoint":
        return self.op_abs()

    @once
    def is_single_element(self) -> bool:
        if self.is_empty():
            return False
        return self.min_elem == self.max_elem  # type: ignore #TODO

    @property
    def is_integer(self) -> bool:
        return all(r.is_integer for r in self._intervals.intervals)

    def as_gapless(self) -> "Quantity_Interval":
        if self.is_empty():
            raise ValueError("empty interval cannot be gapless")
        return Quantity_Interval(self.min_elem, self.max_elem, units=self.units)

    @override
    def any(self) -> Quantity:
        return self.min_elem

    def serialize_pset(self) -> dict[str, Any]:
        return {
            "intervals": self._intervals.serialize(),
            "unit": str(self.units),
        }

    @override
    @classmethod
    def deserialize_pset(cls, data: dict):
        from faebryk.libs.units import P

        out = cls(units=getattr(P, data["unit"]))
        out._intervals = P_Set.deserialize(data["intervals"])
        return out

    def to_dimensionless(self) -> "Quantity_Interval_Disjoint":
        return Quantity_Interval_Disjoint._from_intervals(
            self._intervals, dimensionless
        )


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
