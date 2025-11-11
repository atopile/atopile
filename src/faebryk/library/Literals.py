from enum import Enum
from typing import TYPE_CHECKING, Self

import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.library.Units as Units

if TYPE_CHECKING:
    import faebryk.library.Units as Units


class is_literal(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()


# --------------------------------------------------------------------------------------


class Strings(fabll.Node):
    _is_literal = is_literal.MakeChild()

    def setup(self, *values: str) -> Self:
        # TODO
        return self


class Numbers(fabll.Node):
    _is_literal = is_literal.MakeChild()

    def setup(self, *intervals: fabll.NodeT, unit: fabll.NodeT) -> Self:
        # TODO
        return self

    def setup_from_interval(
        self,
        lower: float | None,
        upper: float | None,
        unit: type[fabll.NodeT] = Units.Dimensionless,
    ) -> Self:
        # TODO
        return self

    @classmethod
    def bind_from_interval(cls, tg: fabll.TypeGraph, g: fabll.GraphView):
        class NumbersBound:
            def __init__(self, tg: fabll.TypeGraph, g: fabll.GraphView):
                self.tg = tg
                self.g = g

            def setup_from_interval(
                self,
                lower: float | None,
                upper: float | None,
                unit: type[fabll.NodeT] = Units.Dimensionless,
            ) -> Self:
                return (
                    cls.bind_typegraph(tg=tg)
                    .create_instance(g=g)
                    .setup_from_interval(lower=lower, upper=upper, unit=unit)
                )

        return NumbersBound(tg=tg, g=g).setup_from_interval

    @classmethod
    def unbounded(cls, units: fabll.NodeT) -> "Numbers": ...
    def is_empty(self) -> bool: ...
    def min_elem(self) -> "Numbers": ...
    def max_elem(self) -> "Numbers": ...
    def closest_elem(self, target: "Numbers") -> "Numbers": ...
    def is_superset_of(self, other: "Numbers") -> bool: ...
    def is_subset_of(self, other: "Numbers") -> bool: ...

    def op_intersect_intervals(self, *other: "Numbers") -> "Numbers": ...
    def op_union_intervals(self, other: "Numbers") -> "Numbers": ...
    def op_difference_intervals(self, other: "Numbers") -> "Numbers": ...
    def op_symmetric_difference_intervals(self, other: "Numbers") -> "Numbers": ...
    def op_add_intervals(self, other: "Numbers") -> "Numbers": ...
    def op_negate(self) -> "Numbers": ...
    def op_subtract_intervals(self, other: "Numbers") -> "Numbers": ...
    def op_mul_intervals(self, other: "Numbers") -> "Numbers": ...
    def op_invert(self) -> "Numbers": ...
    def op_div_intervals(self, other: "Numbers") -> "Numbers": ...
    def op_pow_intervals(self, other: "Numbers") -> "Numbers": ...
    def op_round(self, ndigits: int = 0) -> "Numbers": ...
    def op_abs(self) -> "Numbers": ...
    def op_log(self) -> "Numbers": ...
    def op_sqrt(self) -> "Numbers": ...
    def op_sin(self) -> "Numbers": ...
    def op_cos(self) -> "Numbers": ...
    def op_floor(self) -> "Numbers": ...
    def op_ceil(self) -> "Numbers": ...
    def op_deviation_to(
        self, other: "Numbers", relative: bool = False
    ) -> "Numbers": ...
    def op_is_bit_set(self, other: "Numbers") -> "Booleans": ...
    def op_total_span(self) -> "Numbers":
        """Returns the sum of the spans of all intervals in this disjoint set.
        For a single interval, this is equivalent to max - min.
        For multiple intervals, this sums the spans of each disjoint interval."""
        ...

    def is_unbounded(self) -> bool: ...
    def is_finite(self) -> bool: ...

    # operators
    @staticmethod
    def intersect_all(*obj: "Numbers") -> "Numbers": ...

    def is_single_element(self) -> bool: ...
    def is_integer(self) -> bool: ...
    def as_gapless(self) -> "Numbers": ...
    def to_dimensionless(self) -> "Numbers": ...

    def has_compatible_units_with(self, other: "Numbers") -> bool: ...
    def are_units_compatible(self, unit: fabll.NodeT) -> bool: ...


class Booleans(fabll.Node):
    _is_literal = is_literal.MakeChild()

    def setup(self, *values: bool) -> Self:
        # TODO
        return self

    def get_single(self) -> bool: ...


class Enums(fabll.Node):
    _is_literal = is_literal.MakeChild()

    def setup[T: Enum](self, enum: type[T], *values: T) -> Self:
        # TODO
        return self


# --------------------------------------------------------------------------------------

LiteralNodes = Numbers | Booleans | Enums | Strings
LiteralValues = float | bool | Enum | str


# TODO
def make_lit(value: LiteralValues) -> LiteralNodes: ...
