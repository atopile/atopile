import math
from bisect import bisect
from collections.abc import Generator
from dataclasses import dataclass
from enum import Enum
from operator import ge
from typing import TYPE_CHECKING, ClassVar, Iterable, Self, cast
from warnings import deprecated

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none, once

if TYPE_CHECKING:
    from faebryk.library.Units import is_unit

REL_DIGITS = 7  # 99.99999% precision
ABS_DIGITS = 15  # femto
EPSILON_REL = 10 ** -(REL_DIGITS - 1)
EPSILON_ABS = 10**-ABS_DIGITS

# TODO all creating functions need g as param


class is_literal(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def is_subset_of(self, other: "is_literal") -> bool:
        if obj := fabll.Traits(self).get_obj_raw().try_cast(Booleans):
            return set(obj.get_values()).issubset(
                set(fabll.Traits(other).get_obj(Booleans).get_values())
            )

        # TODO
        return None

    def op_intersect_intervals(self, other: "LiteralNodes") -> "LiteralNodes":
        # TODO
        pass

    def op_union_intervals(self, other: "LiteralNodes") -> "LiteralNodes":
        # TODO
        pass

    def op_symmetric_difference_intervals(
        self, other: "LiteralNodes"
    ) -> "LiteralNodes":
        # TODO
        pass

    def op_is_equal(self, other: "LiteralNodes") -> "Booleans":
        # TODO
        pass

    def in_container(self, other: Iterable["is_literal"]) -> bool:
        return any(self.equals(other) for other in other)

    @staticmethod
    def intersect_all(*objs: "is_literal") -> "is_literal":
        # TODO
        pass

    def equals(self, *others: "is_literal") -> tuple[int, "is_literal"] | None:
        self_c = self.switch_cast()
        for i, other in enumerate(others):
            other_c = other.switch_cast()
            if type(self_c) is not type(other_c):
                continue
            if self_c.equals(other_c):
                return i, other_c
        return None

    def equals_singleton(self, singleton: "LiteralValues") -> bool:
        is_singleton = self.switch_cast().is_singleton()
        if is_singleton is None:
            return False
        return singleton == is_singleton

    def is_single_element(self) -> bool:
        # TODO
        pass

    def is_empty(self) -> bool:
        # TODO
        pass

    def as_operand(self) -> "F.Parameters.can_be_operand":
        from faebryk.library.Parameters import can_be_operand

        return self.get_sibling_trait(can_be_operand)

    def any(self) -> "LiteralValues":
        # TODO
        pass

    def __hash__(self) -> int:
        return super().__hash__()

    def __eq__(self, other) -> bool:
        if not isinstance(other, fabll.Node):
            raise TypeError("DO NOT USE `==` on literals!")
        # No operator overloading!
        return super().__eq__(other)

    def switch_cast(self) -> "LiteralNodes":
        types = [Strings, Numbers, Booleans, AbstractEnums]
        obj = fabll.Traits(self).get_obj_raw()
        for t in types:
            if obj.isinstance(t):
                return obj.cast(t)
        raise ValueError(f"Cannot cast literal {self} of type {obj} to any of {types}")

    def pretty_repr(self) -> str:
        # TODO
        lit = self.switch_cast()
        return f"{lit.get_type_name()}({lit.get_values()})"

    def pretty_str(self) -> str:
        # TODO
        lit = self.switch_cast()
        return f"{lit.get_values()[0]}"

    def is_not_correlatable(self) -> bool:
        return not self.is_single_element() and not self.is_empty()


# --------------------------------------------------------------------------------------
LiteralValues = float | bool | Enum | str


@dataclass(frozen=True)
class LiteralsAttributes(fabll.NodeAttributes):
    value: LiteralValues


@dataclass(frozen=True)
class StringLiteralSingletonAttributes(fabll.NodeAttributes):
    value: str


class StringLiteralSingleton(fabll.Node[StringLiteralSingletonAttributes]):
    Attributes = StringLiteralSingletonAttributes

    def get_value(self) -> str:
        return self.attributes().value

    @classmethod
    def MakeChild(cls, value: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(
            cls, attributes=StringLiteralSingletonAttributes(value=value)
        )
        return out


class Strings(fabll.Node):
    from faebryk.library.Parameters import can_be_operand

    is_literal = fabll.Traits.MakeEdge(is_literal.MakeChild())
    as_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    values = F.Collections.PointerSet.MakeChild()

    def setup_from_values(self, *values: str) -> Self:
        StirngLitT = StringLiteralSingleton.bind_typegraph(tg=self.tg)
        for value in values:
            self.values.get().append(
                StirngLitT.create_instance(
                    g=self.instance.g(),
                    attributes=StringLiteralSingletonAttributes(value=value),
                )
            )
        return self

    def get_values(self) -> list[str]:
        return [
            lit.cast(StringLiteralSingleton).get_value()
            for lit in self.values.get().as_list()
        ]

    @classmethod
    def MakeChild(cls, *values: str) -> fabll._ChildField[Self]:  # type: ignore
        out = fabll._ChildField(cls)
        lits = [StringLiteralSingleton.MakeChild(value=value) for value in values]
        out.add_dependant(
            *F.Collections.PointerSet.MakeEdges(
                [out, cls.values], [[lit] for lit in lits]
            )
        )
        out.add_dependant(*lits, before=True)

        return out

    @classmethod
    def MakeChild_ConstrainToLiteral(
        cls, ref: fabll.RefPath, *values: str
    ) -> fabll._ChildField[Self]:
        from faebryk.library.Expressions import Is

        lit = cls.MakeChild(*values)
        out = Is.MakeChild_Constrain([ref, [lit]])
        out.add_dependant(lit, before=True)
        return out

    # TODO fix calling sites and remove this
    @deprecated("Use get_values() instead")
    def get_value(self) -> str:
        values = self.get_values()
        if len(values) != 1:
            raise ValueError(f"Expected 1 value, got {len(values)}")
        return values[0]

    def is_singleton(self) -> str | None:
        elements = self.get_values()
        if not len(elements) == 1:
            return None
        return next(iter(elements))


@dataclass(frozen=True)
class NumericAttributes(fabll.NodeAttributes):
    value: float


class Numeric(fabll.Node[NumericAttributes]):
    Attributes = NumericAttributes

    @classmethod
    def MakeChild(cls, value: float) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls, attributes=NumericAttributes(value=value))
        return out

    @classmethod
    def create_instance(
        cls, g: graph.GraphView, tg: fbrk.TypeGraph, value: float
    ) -> "Numeric":
        return Numeric.bind_typegraph(tg).create_instance(
            g=g, attributes=NumericAttributes(value=value)
        )

    def get_value(self) -> float:
        value = self.instance.node().get_dynamic_attrs().get("value", None)
        if value is None:
            raise ValueError("Numeric literal has no value")
        return float(value)

    @staticmethod
    def float_round(value: float, digits: int = 0) -> float:
        if value in [math.inf, -math.inf]:
            return value
        out = round(value, digits)
        return float(out)


class TestNumeric:
    def test_make_child(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        expected_value = 1.0

        class App(fabll.Node):
            numeric = Numeric.MakeChild(value=expected_value)

        app = App.bind_typegraph(tg=tg).create_instance(g=g)

        assert app.numeric.get().get_value() == expected_value

    def test_create_instance(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        expected_value = 1.0
        numeric = Numeric.create_instance(g=g, tg=tg, value=expected_value)
        assert numeric.get_value() == expected_value


class NumericInterval(fabll.Node):
    _min_identifier: ClassVar[str] = "min"
    _max_identifier: ClassVar[str] = "max"

    @classmethod
    def MakeChild(cls, min: float, max: float) -> fabll._ChildField[Self]:
        if not NumericInterval.validate_bounds(min, max):
            raise ValueError(f"Invalid interval: {min} > {max}")
        out = fabll._ChildField(cls)
        min_numeric = Numeric.MakeChild(Numeric.float_round(min, ABS_DIGITS))
        max_numeric = Numeric.MakeChild(Numeric.float_round(max, ABS_DIGITS))
        out.add_dependant(min_numeric, identifier=cls._min_identifier)
        out.add_dependant(max_numeric, identifier=cls._max_identifier)
        out.add_dependant(
            fabll.MakeEdge(
                lhs=[out],
                rhs=[min_numeric],
                edge=fbrk.EdgeComposition.build(child_identifier=cls._min_identifier),
            ),
            identifier=cls._min_identifier,
        )
        out.add_dependant(
            fabll.MakeEdge(
                lhs=[out],
                rhs=[max_numeric],
                edge=fbrk.EdgeComposition.build(child_identifier=cls._max_identifier),
            ),
            identifier=cls._max_identifier,
        )
        return out

    def get_min(self) -> Numeric:
        numeric_instance = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._min_identifier
        )
        assert numeric_instance is not None
        return Numeric.bind_instance(numeric_instance)

    def get_max(self) -> Numeric:
        numeric_instance = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._max_identifier
        )
        assert numeric_instance is not None
        return Numeric.bind_instance(numeric_instance)

    def get_value(self) -> float:
        if self.is_single_element():
            return self.get_min_value()
        raise ValueError(
            "NumericInterval is not a singleton: "
            f"{self.get_min_value()} != {self.get_max_value()}"
        )

    def get_min_value(self) -> float:
        return self.get_min().get_value()

    def get_max_value(self) -> float:
        return self.get_max().get_value()

    @classmethod
    def create_instance(
        cls, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> "NumericInterval":
        return NumericInterval.bind_typegraph(tg=tg).create_instance(g=g)

    @classmethod
    def validate_bounds(cls, min: float, max: float) -> bool:
        if not isinstance(min, (int, float)):
            return False
        if not isinstance(max, (int, float)):
            return False
        if min > max:
            return False
        return True

    def setup(  # type: ignore
        self, min: float, max: float
    ) -> "NumericInterval":
        if not NumericInterval.validate_bounds(min, max):
            raise ValueError(f"Invalid interval: {min} > {max}")
        g = self.g
        tg = self.tg
        #  Add numeric literals to the node min and max fields
        min_numeric = Numeric.create_instance(g=g, tg=tg, value=min)
        max_numeric = Numeric.create_instance(g=g, tg=tg, value=max)
        _ = fbrk.EdgeComposition.add_child(
            bound_node=self.instance,
            child=min_numeric.instance.node(),
            child_identifier=self._min_identifier,
        )
        _ = fbrk.EdgeComposition.add_child(
            bound_node=self.instance,
            child=max_numeric.instance.node(),
            child_identifier=self._max_identifier,
        )
        return self

    def setup_from_singleton(self, value: float) -> "NumericInterval":
        return self.setup(min=value, max=value)

    def is_empty(self) -> bool:
        return False

    def is_unbounded(self) -> bool:
        return self.get_min_value() == -math.inf and self.get_max_value() == math.inf

    def is_finite(self) -> bool:
        return self.get_min_value() != -math.inf and self.get_max_value() != math.inf

    def is_single_element(self) -> bool:
        return self.get_min_value() == self.get_max_value()

    def is_integer(self) -> bool:
        min_value = self.get_min_value()

        return self.is_single_element() and min_value == int(min_value)

    def as_center_rel(self) -> tuple[float, float]:
        if self.get_min_value() == self.get_max_value():
            return self.get_min_value(), 0.0
        if not self.is_finite():
            return self.get_min_value(), math.inf

        center = (self.get_min_value() + self.get_max_value()) / 2
        if center == 0:
            rel = math.inf
        else:
            rel = (self.get_max_value() - self.get_min_value()) / 2 / center
        rel = abs(rel)
        return center, rel  # type: ignore

    def is_subset_of(self, other: "NumericInterval") -> bool:
        return ge(self.get_min_value(), other.get_min_value()) and ge(
            other.get_max_value(), self.get_max_value()
        )

    def op_add(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericInterval"
    ) -> "NumericInterval":
        """
        Arithmetically adds two intervals.
        """
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(
            min=self.get_min_value() + other.get_min_value(),
            max=self.get_max_value() + other.get_max_value(),
        )
        return numeric_interval

    def op_negate(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericInterval":
        """
        Arithmetically negates a interval.
        """
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(
            min=-self.get_max_value(),
            max=-self.get_min_value(),
        )
        return numeric_interval

    def op_subtract(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericInterval"
    ) -> "NumericInterval":
        """
        Arithmetically subtracts a interval from another interval.
        """
        return self.op_add(g=g, tg=tg, other=other.op_negate(g=g, tg=tg))

    def op_multiply(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericInterval"
    ) -> "NumericInterval":
        """
        Arithmetically multiplies two intervals.
        """
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)

        self_min = self.get_min_value()
        self_max = self.get_max_value()
        other_min = other.get_min_value()
        other_max = other.get_max_value()

        def guarded_mul(a: float, b: float) -> list:
            """
            0 * inf -> 0
            0 * -inf -> 0
            """
            if 0.0 in [a, b]:
                return [0.0]  # type: ignore
            prod = a * b
            assert not math.isnan(prod)
            return [prod]

        values = [
            res
            for a, b in [
                (self_min, other_min),
                (self_min, other_max),
                (self_max, other_min),
                (self_max, other_max),
            ]
            for res in guarded_mul(a, b)
        ]
        _min = min(values)
        _max = max(values)

        numeric_interval.setup(
            min=_min,
            max=_max,
        )
        return numeric_interval

    def op_invert(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericSet":
        """
        Arithmetically inverts a interval (1/x).
        """
        _min = self.get_min_value()
        _max = self.get_max_value()

        numeric_set = NumericSet.create_instance(g=g, tg=tg)

        # Case 1
        if _min == 0 == _max:
            return numeric_set
        # Case 2
        if _min < 0 < _max:
            return numeric_set.setup_from_values(
                values=[(-math.inf, 1 / _min), (1 / _max, math.inf)]
            )
        # Case 3
        elif _min < 0 == _max:
            return numeric_set.setup_from_values(values=[(-math.inf, 1 / _min)])
        # Case 4
        elif _min == 0 < _max:
            return numeric_set.setup_from_values(values=[(1 / _max, math.inf)])
        # Case 5
        else:
            return numeric_set.setup_from_values(values=[(1 / _max, 1 / _min)])

    def op_pow(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericInterval"
    ) -> "NumericSet":
        base = self
        exp = other
        base_min = self.get_min_value()
        base_max = self.get_max_value()
        exp_min = other.get_min_value()
        exp_max = other.get_max_value()

        if exp_max < 0:
            return base.op_pow(g=g, tg=tg, other=exp.op_negate(g=g, tg=tg)).op_invert(
                g=g, tg=tg
            )
        if exp_min < 0:
            raise NotImplementedError("crossing zero in exp not implemented yet")
        if base_min < 0 and not other.is_integer():
            raise NotImplementedError(
                "cannot raise negative base to fractional exponent (complex result)"
            )

        def _pow(x, y):
            try:
                return x**y
            except OverflowError:
                return math.inf if x > 0 else -math.inf

        a, b = base_min, base_max
        c, d = exp_min, exp_max

        # see first two guards above
        assert c >= 0

        values = [
            _pow(a, c),
            _pow(a, d),
            _pow(b, c),
            _pow(b, d),
        ]

        if a < 0 < b:
            # might be 0 exp, so just in case applying exponent
            values.extend((0.0**c, 0.0**d))

            # d odd
            if d % 2 == 1:
                # c < k < d
                if (k := d - 1) > c:
                    values.append(_pow(a, k))

        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(min(values), max(values))])
        return numeric_set

    def op_divide(
        self: "NumericInterval",
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        other: "NumericInterval",
    ) -> "NumericSet":
        """
        Arithmetically divides a interval by another interval.
        """
        other_intervals = other.op_invert(g=g, tg=tg).get_intervals()
        products = []
        for other_interval in other_intervals:
            products.append(self.op_multiply(g=g, tg=tg, other=other_interval))

        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup(intervals=products)

        return numeric_set

    def op_intersect(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericInterval"
    ) -> "NumericSet":
        """
        Set intersects two intervals.
        """
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        min_ = max(self.get_min_value(), other.get_min_value())
        max_ = min(self.get_max_value(), other.get_max_value())
        if min_ <= max_:
            return numeric_set.setup_from_values(values=[(min_, max_)])
        if min_ == max_:
            return numeric_set.setup_from_values(values=[(min_, min_)])
        return numeric_set

    def op_difference(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericInterval"
    ) -> "NumericSet":
        """
        Set difference of two intervals.
        """
        numeric_set = NumericSet.create_instance(g=g, tg=tg)

        # no overlap
        if (
            self.get_max_value() < other.get_min_value()
            or self.get_min_value() > other.get_max_value()
        ):
            return numeric_set.setup(intervals=[self])
        # fully covered
        if (
            other.get_min_value() <= self.get_min_value()
            and other.get_max_value() >= self.get_max_value()
        ):
            return numeric_set
        # inner overlap
        if (
            self.get_min_value() < other.get_min_value()
            and self.get_max_value() > other.get_max_value()
        ):
            return numeric_set.setup_from_values(
                values=[
                    (self.get_min_value(), other.get_min_value()),
                    (other.get_max_value(), self.get_max_value()),
                ],
            )
        # right overlap
        if self.get_min_value() < other.get_min_value():
            return numeric_set.setup_from_values(
                values=[(self.get_min_value(), other.get_min_value())],
            )
        # left overlap
        return numeric_set.setup_from_values(
            values=[(other.get_max_value(), self.get_max_value())],
        )

    def op_round(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, ndigits: int = 0
    ) -> "NumericInterval":
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(
            min=Numeric.float_round(self.get_min_value(), ndigits),
            max=Numeric.float_round(self.get_max_value(), ndigits),
        )
        return numeric_interval

    def op_abs(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericInterval":
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        # case 1: crosses zero
        if self.get_min_value() < 0 < self.get_max_value():
            numeric_interval.setup(
                min=0,
                max=self.get_max_value(),
            )
            return numeric_interval
        # case 2: negative only
        if self.get_min_value() < 0 and self.get_max_value() < 0:
            numeric_interval.setup(
                min=-self.get_max_value(),
                max=-self.get_min_value(),
            )
            return numeric_interval
        # case 3: max = 0 and min < 0
        if self.get_min_value() < 0 and self.get_max_value() == 0:
            numeric_interval.setup(
                min=0,
                max=-self.get_min_value(),
            )
            return numeric_interval

        assert self.get_min_value() >= 0 and self.get_max_value() >= 0
        return self

    def op_log(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericInterval":
        if self.get_min_value() <= 0:
            raise ValueError(f"invalid log of {self}")
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(
            min=math.log(self.get_min_value()),
            max=math.log(self.get_max_value()),
        )
        return numeric_interval

    @classmethod
    def sine_on_interval(
        cls,
        interval: tuple[float, float],
    ) -> tuple[float, float]:
        """
        Computes the overall sine range on the given x-interval.

        The extreme values occur either at the endpoints or at turning points
        of sine (x = π/2 + π*k).
        """
        start, end = interval
        if start > end:
            raise ValueError("Invalid interval: start must be <= end")
        if math.isinf(start) or math.isinf(end):
            return (-1, 1)
        if end - start > 2 * math.pi:
            return (-1, 1)

        # Evaluate sine at the endpoints
        xs = [start, end]

        # Include turning points within the interval
        k_start = math.ceil((start - math.pi / 2) / math.pi)
        k_end = math.floor((end - math.pi / 2) / math.pi)
        for k in range(k_start, k_end + 1):
            xs.append(math.pi / 2 + math.pi * k)

        sine_values = [math.sin(x) for x in xs]
        return (min(sine_values), max(sine_values))

    def op_sine(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericInterval":
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min, max = NumericInterval.sine_on_interval(
            (float(self.get_min_value()), float(self.get_max_value()))
        )
        numeric_interval.setup(min=min, max=max)
        return numeric_interval

    def maybe_merge_interval(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericInterval"
    ) -> list["NumericInterval"]:
        """
        Attempts to merge two intervals if they overlap or are adjacent.

        Example:
            - [1,5] and [3,7] merge to [1,7] since 3 falls within [1,5]
            - [1,2] and [4,5] stay separate since 4 doesn't fall within [1,2]

        Returns:
            List containing either:
            - Single merged interval if intervals overlap
            - Both intervals in order if they don't overlap
        """
        is_left = self.get_min_value() <= other.get_min_value()
        left = self if is_left else other
        right = other if is_left else self
        if self.contains(right.get_min_value()):
            numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
            numeric_interval.setup(
                min=left.get_min_value(),
                max=max(left.get_max_value(), right.get_max_value()),
            )
            return [numeric_interval]
        return [left, right]

    def contains(self, item: float) -> bool:
        """
        Set checks if a number is in a interval.
        """
        if not isinstance(item, float):
            return False
        return ge(self.get_max_value(), item) and ge(item, self.get_min_value())

    def equals(self, other: "NumericInterval") -> bool:
        return (
            self.get_min_value() == other.get_min_value()
            and self.get_max_value() == other.get_max_value()
        )

    def __repr__(self) -> str:
        return f"_interval({self.get_min_value()}, {self.get_max_value()})"

    def __str__(self) -> str:
        if self.get_min_value() == self.get_max_value():
            return f"[{self.get_min_value()}]"
        center, rel = self.as_center_rel()
        if rel < 1:
            return f"{center} ± {rel * 100}%"
        return f"[{self.get_min_value()}, {self.get_max_value()}]"

    def any(self) -> float:
        return self.get_min_value()

    def serialize(self) -> dict:
        return {
            "type": "Numeric_Interval",
            "data": {
                "min": None
                if math.isinf(self.get_min_value())
                else float(self.get_min_value()),
                "max": None
                if math.isinf(self.get_max_value())
                else float(self.get_max_value()),
            },
        }


class TestNumericInterval:
    def test_make_child(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        expected_min = 1.0
        expected_max = 2.0

        class App(fabll.Node):
            numeric_interval = NumericInterval.MakeChild(
                min=expected_min, max=expected_max
            )

        app = App.bind_typegraph(tg=tg).create_instance(g=g)

        assert app.numeric_interval.get().get_min().get_value() == expected_min
        assert app.numeric_interval.get().get_max().get_value() == expected_max

    def test_instance_setup(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        expected_min = 1.0
        expected_max = 2.0

        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(min=expected_min, max=expected_max)
        assert numeric_interval.get_min().get_value() == expected_min
        assert numeric_interval.get_max().get_value() == expected_max

    def test_is_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        assert not numeric_interval.is_empty()

    def test_is_unbounded_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -math.inf
        max_value = math.inf
        numeric_interval.setup(min=min_value, max=max_value)
        assert numeric_interval.is_unbounded()

    def test_is_unbounded_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        assert not numeric_interval.is_unbounded()

    def test_is_finite_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        assert numeric_interval.is_finite()

    def test_is_finite_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -math.inf
        max_value = math.inf
        numeric_interval.setup(min=min_value, max=max_value)
        assert not numeric_interval.is_finite()

    def test_is_single_element_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 0.0
        numeric_interval.setup(min=min_value, max=max_value)
        assert numeric_interval.is_single_element()

    def test_is_single_element_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        assert not numeric_interval.is_single_element()

    def test_is_integer_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 2.0
        max_value = 2.0
        numeric_interval.setup(min=min_value, max=max_value)
        assert numeric_interval.is_integer()

    def test_is_integer_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 1.5
        max_value = 1.5
        numeric_interval.setup(min=min_value, max=max_value)
        assert not numeric_interval.is_integer()

    def test_as_center_rel(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        assert numeric_interval.as_center_rel() == (0.5, 1.0)

    def test_is_subset_of_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        other = NumericInterval.create_instance(g=g, tg=tg)
        other_min_value = -0.5
        other_max_value = 1.5
        other.setup(min=other_min_value, max=other_max_value)
        assert numeric_interval.is_subset_of(other=other)

    def test_is_subset_of_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        other = NumericInterval.create_instance(g=g, tg=tg)
        other_min_value = 1.5
        other_max_value = 2.5
        other.setup(min=other_min_value, max=other_max_value)
        assert not numeric_interval.is_subset_of(other=other)

    def test_op_add(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        other = NumericInterval.create_instance(g=g, tg=tg)
        other_min_value = 0.5
        other_max_value = 1.5
        other.setup(min=other_min_value, max=other_max_value)
        result = numeric_interval.op_add(g=g, tg=tg, other=other)
        assert result.get_min_value() == 0.5
        assert result.get_max_value() == 2.5

    def test_op_negate(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_negate(g=g, tg=tg)
        assert result.get_min_value() == -1.0
        assert result.get_max_value() == -0.0

    def test_op_subtract(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        other = NumericInterval.create_instance(g=g, tg=tg)
        other_min_value = 0.5
        other_max_value = 1.5
        other.setup(min=other_min_value, max=other_max_value)
        result = numeric_interval.op_subtract(g=g, tg=tg, other=other)
        assert result.get_min_value() == -1.5
        assert result.get_max_value() == 0.5

    def test_op_multiply(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 3.0
        max_value = 4.0
        numeric_interval.setup(min=min_value, max=max_value)
        other = NumericInterval.create_instance(g=g, tg=tg)
        other_min_value = 0.5
        other_max_value = 1.5
        other.setup(min=other_min_value, max=other_max_value)
        result = numeric_interval.op_multiply(g=g, tg=tg, other=other)
        assert result.get_min_value() == 1.5
        assert result.get_max_value() == 6.0

    def test_op_multiply_negative_values(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -3.0
        max_value = -2.0
        numeric_interval.setup(min=min_value, max=max_value)
        other = NumericInterval.create_instance(g=g, tg=tg)
        other_min_value = 0.5
        other_max_value = 3.5
        other.setup(min=other_min_value, max=other_max_value)
        result = numeric_interval.op_multiply(g=g, tg=tg, other=other)
        assert result.get_min_value() == -10.5
        assert result.get_max_value() == -1.0

    def test_op_multiply_zero_values(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 1.0
        max_value = 2.0
        numeric_interval.setup(min=min_value, max=max_value)
        other = NumericInterval.create_instance(g=g, tg=tg)
        other_min_value = 0.0
        other_max_value = 0.0
        other.setup(min=other_min_value, max=other_max_value)
        result = numeric_interval.op_multiply(g=g, tg=tg, other=other)
        assert result.get_min_value() == 0.0
        assert result.get_max_value() == 0.0

    def test_op_invert_case_1(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 0.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_invert(g=g, tg=tg)
        assert result.is_empty()

    def test_op_invert_case_2(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -1.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_invert(g=g, tg=tg)
        result_intervals = result.get_intervals()
        assert len(result_intervals) == 2
        assert result_intervals[0].get_min_value() == -math.inf
        assert result_intervals[0].get_max_value() == -1.0
        assert result_intervals[1].get_min_value() == 1.0
        assert result_intervals[1].get_max_value() == math.inf

    def test_op_invert_case_3(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -1.0
        max_value = 0.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_invert(g=g, tg=tg)
        assert len(result.get_intervals()) == 1
        assert result.get_intervals()[0].get_min_value() == -math.inf
        assert result.get_intervals()[0].get_max_value() == -1.0

    def test_op_invert_case_4(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 1.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_invert(g=g, tg=tg)
        assert len(result.get_intervals()) == 1
        assert result.get_intervals()[0].get_min_value() == 1.0
        assert result.get_intervals()[0].get_max_value() == math.inf

    def test_op_invert_case_5(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 2.0
        max_value = 4.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_invert(g=g, tg=tg)
        assert len(result.get_intervals()) == 1
        assert result.get_intervals()[0].get_min_value() == 0.25
        assert result.get_intervals()[0].get_max_value() == 0.5

    def test_op_pow_positive_base_positive_exponent(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        base = NumericInterval.create_instance(g=g, tg=tg)
        base_min_value = 2.0
        base_max_value = 4.0
        base.setup(min=base_min_value, max=base_max_value)
        exp = NumericInterval.create_instance(g=g, tg=tg)
        exp_min_value = 1.0
        exp_max_value = 2.0
        exp.setup(min=exp_min_value, max=exp_max_value)
        result = base.op_pow(g=g, tg=tg, other=exp)
        assert len(result.get_intervals()) == 1
        assert result.get_intervals()[0].get_min_value() == 2.0
        assert result.get_intervals()[0].get_max_value() == 16.0

    def test_op_divide_positive_numerator_positive_denominator(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 1.0
        max_value = 2.0
        numeric_interval.setup(min=min_value, max=max_value)
        other = NumericInterval.create_instance(g=g, tg=tg)
        other_min_value = 0.5
        other_max_value = 1.5
        other.setup(min=other_min_value, max=other_max_value)
        result = numeric_interval.op_divide(g=g, tg=tg, other=other)
        assert len(result.get_intervals()) == 1
        assert result.get_intervals()[0].get_min_value() == 1.0 / 1.5
        assert result.get_intervals()[0].get_max_value() == 4.0

    def test_op_intersect_no_overlap(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        self_min_value = 1.0
        self_max_value = 2.0
        self_interval = NumericInterval.create_instance(g=g, tg=tg)
        self_interval.setup(min=self_min_value, max=self_max_value)
        other_min_value = 3.0
        other_max_value = 4.0
        other_interval = NumericInterval.create_instance(g=g, tg=tg)
        other_interval.setup(min=other_min_value, max=other_max_value)
        result = self_interval.op_intersect(g=g, tg=tg, other=other_interval)
        assert result.is_empty()

    def test_op_intersect_partially_covered(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        self_min_value = 1.0
        self_max_value = 2.0
        self_interval = NumericInterval.create_instance(g=g, tg=tg)
        self_interval.setup(min=self_min_value, max=self_max_value)
        other_min_value = 1.5
        other_max_value = 2.5
        other_interval = NumericInterval.create_instance(g=g, tg=tg)
        other_interval.setup(min=other_min_value, max=other_max_value)
        result = self_interval.op_intersect(g=g, tg=tg, other=other_interval)
        result_intervals = result.get_intervals()
        assert len(result_intervals) == 1
        assert result_intervals[0].get_min_value() == 1.5
        assert result_intervals[0].get_max_value() == 2.0

    def test_op_difference_no_overlap(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        self_min_value = 1.0
        self_max_value = 2.0
        self_interval = NumericInterval.create_instance(g=g, tg=tg)
        self_interval.setup(min=self_min_value, max=self_max_value)
        other_min_value = 3.0
        other_max_value = 4.0
        other_interval = NumericInterval.create_instance(g=g, tg=tg)
        other_interval.setup(min=other_min_value, max=other_max_value)
        result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
        result_intervals = result.get_intervals()
        assert len(result_intervals) == 1
        assert result_intervals[0].get_min_value() == 1.0
        assert result_intervals[0].get_max_value() == 2.0

    def test_op_difference_fully_covered(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        self_min_value = 1.0
        self_max_value = 5.0
        self_interval = NumericInterval.create_instance(g=g, tg=tg)
        self_interval.setup(min=self_min_value, max=self_max_value)
        other_min_value = 1.0
        other_max_value = 5.0
        other_interval = NumericInterval.create_instance(g=g, tg=tg)
        other_interval.setup(min=other_min_value, max=other_max_value)
        result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
        assert result.is_empty()

    def test_op_difference_inner_overlap(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        self_min_value = 1.0
        self_max_value = 10.0
        self_interval = NumericInterval.create_instance(g=g, tg=tg)
        self_interval.setup(min=self_min_value, max=self_max_value)
        other_min_value = 2.5
        other_max_value = 6.5
        other_interval = NumericInterval.create_instance(g=g, tg=tg)
        other_interval.setup(min=other_min_value, max=other_max_value)
        result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
        result_intervals = result.get_intervals()
        assert len(result_intervals) == 2
        assert result_intervals[0].get_min_value() == 1.0
        assert result_intervals[0].get_max_value() == 2.5
        assert result_intervals[1].get_min_value() == 6.5
        assert result_intervals[1].get_max_value() == 10.0

    def test_op_difference_right_overlap(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        self_min_value = 1.0
        self_max_value = 10.0
        self_interval = NumericInterval.create_instance(g=g, tg=tg)
        self_interval.setup(min=self_min_value, max=self_max_value)
        other_min_value = 6.5
        other_max_value = 10.0
        other_interval = NumericInterval.create_instance(g=g, tg=tg)
        other_interval.setup(min=other_min_value, max=other_max_value)
        result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
        result_intervals = result.get_intervals()
        assert len(result_intervals) == 1
        assert result_intervals[0].get_min_value() == 1.0
        assert result_intervals[0].get_max_value() == 6.5

    def test_op_difference_left_overlap(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        self_min_value = 1.0
        self_max_value = 10.0
        self_interval = NumericInterval.create_instance(g=g, tg=tg)
        self_interval.setup(min=self_min_value, max=self_max_value)
        other_min_value = 1.0
        other_max_value = 6.5
        other_interval = NumericInterval.create_instance(g=g, tg=tg)
        other_interval.setup(min=other_min_value, max=other_max_value)
        result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
        result_intervals = result.get_intervals()
        assert len(result_intervals) == 1
        assert result_intervals[0].get_min_value() == 6.5
        assert result_intervals[0].get_max_value() == 10.0

    def test_op_round(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 1.9524377865952437
        max_value = 2.4983529411764706
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_round(g=g, tg=tg, ndigits=3)
        assert result.get_min_value() == 1.952
        assert result.get_max_value() == 2.498

    def test_op_abs(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -1.0
        max_value = 2.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_abs(g=g, tg=tg)
        assert result.get_min_value() == 0.0
        assert result.get_max_value() == 2.0

    def test_op_abs_crosses_zero(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -1.0
        max_value = 2.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_abs(g=g, tg=tg)
        assert result.get_min_value() == 0.0
        assert result.get_max_value() == 2.0

    def test_op_abs_negative_only(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -1.0
        max_value = 0.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_abs(g=g, tg=tg)
        assert result.get_min_value() == 0.0
        assert result.get_max_value() == 1.0

    def test_op_abs_max_zero_min_negative(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -1.0
        max_value = 0.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_abs(g=g, tg=tg)
        assert result.get_min_value() == 0.0
        assert result.get_max_value() == 1.0

    def test_op_log_positive_interval(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 1.0
        max_value = 2.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_log(g=g, tg=tg)
        assert result.get_min_value() == math.log(1.0)
        assert result.get_max_value() == math.log(2.0)

    def test_op_log_negative_value(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = -1.0
        max_value = 2.0
        numeric_interval.setup(min=min_value, max=max_value)
        with pytest.raises(ValueError):
            numeric_interval.op_log(g=g, tg=tg)

    def test_op_sine(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 0.5
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_sine(g=g, tg=tg)
        assert result.get_min_value() == 0.0
        assert result.get_max_value() == math.sin(0.5)

    def test_op_sine_wide_interval(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min_value = 0.0
        max_value = 10.0
        numeric_interval.setup(min=min_value, max=max_value)
        result = numeric_interval.op_sine(g=g, tg=tg)
        assert result.get_min_value() == -1.0
        assert result.get_max_value() == 1.0

    def test_eq_numeric_set(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set_1.equals(numeric_set_2)


class NumericSet(fabll.Node):
    intervals = F.Collections.PointerSet.MakeChild()

    @classmethod
    def MakeChild(cls, min: float, max: float) -> fabll._ChildField:  # type: ignore
        out = fabll._ChildField(cls)

        _intervals = [NumericInterval.MakeChild(min=min, max=max)]
        out.add_dependant(
            *F.Collections.PointerSet.MakeEdges(
                [out, cls.intervals], [[interval] for interval in _intervals]
            )
        )
        out.add_dependant(*_intervals, before=True)

        return out

    @classmethod
    def sort_merge_intervals(
        cls,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        intervals: list["NumericInterval | NumericSet"],
    ) -> list[NumericInterval]:
        def gen_flat_non_empty() -> Generator[NumericInterval]:
            for r in intervals:
                if r.is_empty():
                    continue
                if isinstance(r, NumericSet):
                    yield from r.get_intervals()
                else:
                    assert isinstance(r, NumericInterval)
                    yield r

        non_empty_intervals = list(gen_flat_non_empty())
        sorted_intervals = sorted(non_empty_intervals, key=lambda e: e.get_min_value())

        def gen_merge() -> Generator[NumericInterval]:
            last = None
            for interval in sorted_intervals:
                if last is None:
                    last = interval
                else:
                    assert isinstance(last, NumericInterval)
                    *prefix, last = last.maybe_merge_interval(
                        g=g, tg=tg, other=interval
                    )
                    yield from prefix
            if last is not None:
                yield last

        return list(gen_merge())

    @classmethod
    def sort_merge_values(
        cls,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        values: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        intervals = []
        for value in values:
            intervals.append(
                NumericInterval.create_instance(g=g, tg=tg).setup(
                    min=value[0], max=value[1]
                )
            )
        return_values = []
        for interval in intervals:
            return_values.append((interval.get_min_value(), interval.get_max_value()))
        return return_values

    def get_intervals(self) -> list[NumericInterval]:
        return [
            interval.cast(NumericInterval)
            for interval in self.intervals.get().as_list()
        ]

    def get_min_value(self) -> float:
        return self.get_intervals()[0].get_min_value()

    def get_max_value(self) -> float:
        return self.get_intervals()[-1].get_max_value()

    def closest_elem(self, target: float) -> float:
        assert isinstance(target, float)
        if self.is_empty():
            raise ValueError("empty interval cannot have closest element")
        index = bisect(self.get_intervals(), target, key=lambda r: r.get_min_value())
        left = self.get_intervals()[index - 1] if index > 0 else None
        if left is not None and left.contains(target):
            return target
        left_bound = left.get_max_value() if left is not None else None
        right_bound = (
            self.get_intervals()[index].get_min_value()
            if index < len(self.get_intervals())
            else None
        )
        try:
            [one] = [b for b in [left_bound, right_bound] if b is not None]
            return one
        except ValueError:
            assert left_bound and right_bound
            if target - left_bound < right_bound - target:
                return left_bound
            return right_bound
        assert False  # unreachable

    def setup_from_interval(self, interval: tuple[float, float]) -> "NumericSet":
        return self.setup_from_values(values=[interval])

    def setup_from_singleton(self, value: float) -> "NumericSet":
        return self.setup_from_values(values=[(value, value)])

    def setup_from_values(self, values: list[tuple[float, float]]) -> "NumericSet":
        assert self.is_empty()
        g = self.g
        tg = self.tg
        sorted_and_merged_values = NumericSet.sort_merge_values(
            g=g, tg=tg, values=values
        )
        for value in sorted_and_merged_values:
            self.intervals.get().append(
                NumericInterval.create_instance(g=g, tg=tg).setup(
                    min=value[0], max=value[1]
                )
            )
        return self

    def setup(  # type: ignore
        self,
        intervals: list["NumericInterval | NumericSet"],
    ) -> "NumericSet":
        assert self.is_empty()
        g = self.g
        tg = self.tg
        sorted_and_merged_intervals = NumericSet.sort_merge_intervals(
            g=g, tg=tg, intervals=intervals
        )
        for interval in sorted_and_merged_intervals:
            self.intervals.get().append(interval)
        return self

    @classmethod
    def create_instance(cls, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericSet":
        return NumericSet.bind_typegraph(tg=tg).create_instance(g=g)

    def is_empty(self) -> bool:
        return len(self.get_intervals()) == 0

    def is_superset_of(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> bool:
        return other.equals(other.op_intersect_intervals(g=g, tg=tg, other=self))

    def is_subset_of(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> bool:
        return other.is_superset_of(g=g, tg=tg, other=self)

    def op_intersect(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericInterval"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_intersect(g=g, tg=tg, other=other))
        return numeric_set.setup(intervals=intervals)

    def op_intersect_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        self_intervals = self.get_intervals()
        other_intervals = other.get_intervals()
        result = []
        s, o = 0, 0
        while s < len(self_intervals) and o < len(other_intervals):
            rs, ro = self_intervals[s], other_intervals[o]
            rs_min, rs_max = rs.get_min_value(), rs.get_max_value()
            ro_min, ro_max = ro.get_min_value(), ro.get_max_value()
            intersect = rs.op_intersect(g=g, tg=tg, other=ro)
            if not intersect.is_empty():
                result.append(intersect)

            if rs_max < ro_min:
                # no remaining element in other list can intersect with rs
                s += 1
            elif ro_max < rs_min:
                # no remaining element in self list can intersect with ro
                o += 1
            elif rs_max < ro_max:
                # rs ends before ro, so move to next in self list
                s += 1
            elif ro_max < rs_max:
                # ro ends before rs, so move to next in other list
                o += 1
            else:
                # rs and ro end on approximately same number, move to next in both lists
                s += 1
                o += 1

        return numeric_set.setup(intervals=result)

    def op_union(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = self.get_intervals() + other.get_intervals()
        return numeric_set.setup(intervals=list(intervals))

    def op_difference_interval(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericInterval"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_difference(g=g, tg=tg, other=other))
        return numeric_set.setup(intervals=intervals)

    def op_difference_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        # TODO there is probably a more efficient way to do this
        out = self
        for o in other.get_intervals():
            out = out.op_difference_interval(g=g, tg=tg, other=o)
        return out

    def op_symmetric_difference_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        return self.op_union(g=g, tg=tg, other=other).op_difference_intervals(
            g=g, tg=tg, other=self.op_intersect_intervals(g=g, tg=tg, other=other)
        )

    def op_pow(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)

        self_intervals = self.get_intervals()
        other_intervals = other.get_intervals()

        out = []
        for self_interval in self_intervals:
            for other_interval in other_intervals:
                out.append(self_interval.op_pow(g=g, tg=tg, other=other_interval))

        return numeric_set.setup(intervals=out)

    def op_add(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for self_interval in self.get_intervals():
            for other_interval in other.get_intervals():
                intervals.append(self_interval.op_add(g=g, tg=tg, other=other_interval))
        return numeric_set.setup(intervals=intervals)

    def op_negate(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_negate(g=g, tg=tg))
        return numeric_set.setup(intervals=intervals)

    def op_subtract(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        return self.op_add(g=g, tg=tg, other=other.op_negate(g=g, tg=tg))

    def op_multiply(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for self_interval in self.get_intervals():
            for other_interval in other.get_intervals():
                intervals.append(
                    self_interval.op_multiply(g=g, tg=tg, other=other_interval)
                )
        return numeric_set.setup(intervals=intervals)

    def op_invert(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_invert(g=g, tg=tg))
        return numeric_set.setup(intervals=intervals)

    def op_div_intervals(
        self: "NumericSet",
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        other: "NumericSet",
    ) -> "NumericSet":
        return self.op_multiply(g=g, tg=tg, other=other.op_invert(g=g, tg=tg))

    def op_ge_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "Booleans":
        if self.is_empty() or other.is_empty():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[])
            )
        if self.get_min_value() >= other.get_max_value():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[True])
            )
        if self.get_max_value() < other.get_min_value():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[False])
            )
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True, False])
        )

    def op_gt_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "Booleans":
        if self.is_empty() or other.is_empty():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[])
            )
        if self.get_min_value() > other.get_max_value():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[True])
            )
        if self.get_max_value() <= other.get_min_value():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[False])
            )
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True, False])
        )

    def op_le_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "Booleans":
        if self.is_empty() or other.is_empty():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[])
            )
        if self.get_max_value() <= other.get_min_value():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[True])
            )
        if self.get_min_value() > other.get_max_value():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[False])
            )
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True, False])
        )

    def op_lt_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "NumericSet"
    ) -> "Booleans":
        if self.is_empty() or other.is_empty():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[])
            )
        if self.get_max_value() < other.get_min_value():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[True])
            )
        if self.get_min_value() >= other.get_max_value():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[False])
            )
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True, False])
        )

    def op_round(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, ndigits: int = 0
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_round(g=g, tg=tg, ndigits=ndigits))
        return numeric_set.setup(intervals=intervals)

    def op_abs(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_abs(g=g, tg=tg))
        return numeric_set.setup(intervals=intervals)

    def op_log(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_log(g=g, tg=tg))
        return numeric_set.setup(intervals=intervals)

    def op_sin(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_sine(g=g, tg=tg))
        return numeric_set.setup(intervals=intervals)

    def contains(self, item: float) -> bool:
        if not isinstance(item, float):
            return False
        for interval in self.get_intervals():
            if interval.contains(item):
                return True
        return False

    def equals(self, value: "NumericSet") -> bool:
        """Check if all intervals in this set are equal
        to the intervals in the other set."""
        if not isinstance(value, NumericSet):
            return False
        self_intervals = self.get_intervals()
        value_intervals = value.get_intervals()
        print(self_intervals, value_intervals)
        if len(self_intervals) != len(value_intervals):
            return False
        for r1, r2 in zip(self_intervals, value_intervals):
            if not r1.equals(r2):
                return False
        return True

    def __repr__(self) -> str:
        return f"_N_intervals({
            ', '.join(
                f'[{r.get_min_value()}, {r.get_max_value()}]'
                for r in self.get_intervals()
            )
        })"

    def __iter__(self) -> Generator["NumericInterval"]:
        yield from self.get_intervals()

    def is_single_element(self) -> bool:
        if self.is_empty():
            return False
        return self.get_min_value() == self.get_max_value()

    def any(self) -> float:
        return self.get_min_value()

    def serialize(self) -> dict:
        return {
            # legacy name for backwards compatibility
            "type": "Numeric_Interval_Disjoint",
            "data": {"intervals": [r.serialize() for r in self.get_intervals()]},
        }


class TestNumericSet:
    def test_sort_merge_intervals(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_interval_1 = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval_1.setup(min=1.8, max=2.2)
        numeric_interval_2 = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval_2.setup(min=1.5, max=1.6)
        numeric_interval_3 = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval_3.setup(min=2.0, max=3.0)

        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup(
            intervals=[numeric_interval_1, numeric_interval_2, numeric_interval_3],
        )
        intervals = numeric_set.get_intervals()
        assert len(intervals) == 2
        assert intervals[0].get_min_value() == 1.5
        assert intervals[0].get_max_value() == 1.6
        assert intervals[1].get_min_value() == 1.8
        assert intervals[1].get_max_value() == 3.0

    def test_make_child(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        interval_1_min = 0.0
        interval_1_max = 1.0

        class App(fabll.Node):
            numeric_set = NumericSet.MakeChild(
                min=interval_1_min,
                max=interval_1_max,
            )

        app = App.bind_typegraph(tg=tg).create_instance(g=g)
        intervals = app.numeric_set.get().get_intervals()
        assert len(intervals) == 1
        assert intervals[0].get_min_value() == interval_1_min
        assert intervals[0].get_max_value() == interval_1_max

    def test_instance_setup_from_values(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        interval_1_min = 0.0
        interval_1_max = 1.0
        interval_2_min = 1.0
        interval_2_max = 2.0
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(
            values=[(interval_1_min, interval_1_max), (interval_2_min, interval_2_max)],
        )
        assert numeric_set.get_intervals()[0].get_min_value() == interval_1_min
        assert numeric_set.get_intervals()[0].get_max_value() == interval_1_max
        assert numeric_set.get_intervals()[1].get_min_value() == interval_2_min
        assert numeric_set.get_intervals()[1].get_max_value() == interval_2_max

    def test_instance_setup_from_intervals(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        interval_1 = NumericInterval.create_instance(g=g, tg=tg)
        interval_1.setup(min=0.0, max=1.0)
        interval_2 = NumericInterval.create_instance(g=g, tg=tg)
        interval_2.setup(min=1.0, max=2.0)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup(intervals=[interval_1, interval_2])
        intervals = numeric_set.get_intervals()
        assert len(intervals) == 1
        assert intervals[0].get_min_value() == 0.0
        assert intervals[0].get_max_value() == 2.0

    def test_instance_setup_from_singleton(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_singleton(value=1.0)
        assert numeric_set.get_intervals()[0].get_min_value() == 1.0
        assert numeric_set.get_intervals()[0].get_max_value() == 1.0

    def test_instance_setup_from_interval(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_interval(interval=(0.0, 1.0))
        assert numeric_set.get_intervals()[0].get_min_value() == 0.0
        assert numeric_set.get_intervals()[0].get_max_value() == 1.0

    def test_is_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        assert numeric_set.is_empty()
        numeric_set.setup_from_values(values=[(0.0, 1.0), (1.0, 2.0)])
        assert not numeric_set.is_empty()

    def test_is_superset_of_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set_1.is_superset_of(g=g, tg=tg, other=numeric_set_2)

    def test_is_superset_of_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.5), (2.0, 3.0)])
        assert not numeric_set_1.is_superset_of(g=g, tg=tg, other=numeric_set_2)

    def test_is_subset_of_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set_1.is_subset_of(g=g, tg=tg, other=numeric_set_2)

    def test_is_subset_of_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.5), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert not numeric_set_1.is_subset_of(g=g, tg=tg, other=numeric_set_2)

    def test_op_intersect_intervals_partially_covered(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.5, 1.5), (1.7, 3.6)])
        result = numeric_set_1.op_intersect_intervals(g=g, tg=tg, other=numeric_set_2)
        intervals = result.get_intervals()
        assert len(intervals) == 2
        assert intervals[0].get_min_value() == 0.5
        assert intervals[0].get_max_value() == 1.0
        assert intervals[1].get_min_value() == 2.0
        assert intervals[1].get_max_value() == 3.0

    def test_op_union_intervals(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.5, 1.5), (1.7, 3.6)])
        result = numeric_set_1.op_union(g=g, tg=tg, other=numeric_set_2)
        intervals = result.get_intervals()
        assert len(intervals) == 2
        assert intervals[0].get_min_value() == 0.0
        assert intervals[0].get_max_value() == 1.5
        assert intervals[1].get_min_value() == 1.7
        assert intervals[1].get_max_value() == 3.6

    def test_op_difference_intervals(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(min=0.5, max=2.5)
        result = numeric_set.op_difference_interval(g=g, tg=tg, other=numeric_interval)
        intervals = result.get_intervals()
        assert len(intervals) == 2
        assert intervals[0].get_min_value() == 0.0
        assert intervals[0].get_max_value() == 0.5
        assert intervals[1].get_min_value() == 2.5
        assert intervals[1].get_max_value() == 3.0

    def test_op_symmetric_difference_intervals(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.5, 1.5), (1.7, 3.6)])
        result = numeric_set_1.op_symmetric_difference_intervals(
            g=g, tg=tg, other=numeric_set_2
        )
        intervals = result.get_intervals()
        assert len(intervals) == 4
        assert intervals[0].get_min_value() == 0.0
        assert intervals[0].get_max_value() == 0.5
        assert intervals[1].get_min_value() == 1.0
        assert intervals[1].get_max_value() == 1.5
        assert intervals[2].get_min_value() == 1.7
        assert intervals[2].get_max_value() == 2.0
        assert intervals[3].get_min_value() == 3.0
        assert intervals[3].get_max_value() == 3.6

    def test_op_pow_intervals(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (1.0, 2.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (1.0, 2.0)])
        result = numeric_set_1.op_pow(g=g, tg=tg, other=numeric_set_2)
        intervals = result.get_intervals()
        assert len(intervals) == 1
        assert intervals[0].get_min_value() == 0.0
        assert intervals[0].get_max_value() == 4.0

    def test_op_add_intervals(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.5, 1.5), (1.7, 3.6)])
        result = numeric_set_1.op_add(g=g, tg=tg, other=numeric_set_2)
        intervals = result.get_intervals()
        assert len(intervals) == 1
        assert intervals[0].get_min_value() == 0.5
        assert intervals[0].get_max_value() == 6.6

    def test_op_negate(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        result = numeric_set.op_negate(g=g, tg=tg)
        intervals = result.get_intervals()
        assert len(intervals) == 2
        assert intervals[0].get_min_value() == -3.0
        assert intervals[0].get_max_value() == -2.0
        assert intervals[1].get_min_value() == -1.0
        assert intervals[1].get_max_value() == 0.0

    def test_op_subtract_intervals(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.5, 1.5), (1.7, 3.6)])
        result = numeric_set_1.op_subtract(g=g, tg=tg, other=numeric_set_2)
        intervals = result.get_intervals()
        assert len(intervals) == 1
        assert intervals[0].get_min_value() == -3.6
        assert intervals[0].get_max_value() == 2.5

    def test_op_multiply(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.5, 1.5), (1.7, 3.6)])
        result = numeric_set_1.op_multiply(g=g, tg=tg, other=numeric_set_2)
        intervals = result.get_intervals()
        assert len(intervals) == 1
        assert intervals[0].get_min_value() == 0.0
        assert intervals[0].get_max_value() == 10.8

    def test_op_invert(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        result = numeric_set.op_invert(g=g, tg=tg)
        intervals = result.get_intervals()
        assert len(intervals) == 2
        assert intervals[0].get_min_value() == 1 / 3
        assert intervals[0].get_max_value() == 1 / 2
        assert intervals[1].get_min_value() == 1
        assert intervals[1].get_max_value() == math.inf

    def test_op_div_intervals(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.5, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.5, 1.5), (1.7, 3.6)])
        result = numeric_set_1.op_div_intervals(g=g, tg=tg, other=numeric_set_2)
        intervals = result.get_intervals()
        assert len(intervals) == 1
        assert intervals[0].get_min_value() == 0.5 / 3.6
        assert intervals[0].get_max_value() == 6

    def test_op_ge_intervals_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)

        assert numeric_set_1.op_ge_intervals(g=g, tg=tg, other=numeric_set_2).is_empty()

    def test_op_ge_intervals_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(3.5, 4.5), (5.0, 6.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set_1.op_ge_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [True]

    def test_op_ge_intervals_true_equal(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(3.5, 4.5), (5.0, 6.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(1.5, 2.5), (3.0, 3.5)])
        assert numeric_set_1.op_ge_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [True]

    def test_op_ge_intervals_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(3.5, 4.5), (5.0, 6.0)])
        assert numeric_set_1.op_ge_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [False]

    def test_op_gt_intervals_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        assert numeric_set_1.op_gt_intervals(g=g, tg=tg, other=numeric_set_2).is_empty()

    def test_op_gt_intervals_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(3.5, 4.5), (5.0, 6.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set_1.op_gt_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [True]

    def test_op_gt_intervals_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(3.5, 4.5), (5.0, 6.0)])
        assert numeric_set_1.op_gt_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [False]

    def test_op_gt_intervals_true_equal(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(1.5, 2.5), (3.0, 3.5)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(1.5, 2.5), (3.0, 3.5)])
        assert numeric_set_1.op_gt_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [True, False]

    def test_op_le_intervals_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        assert numeric_set_1.op_le_intervals(g=g, tg=tg, other=numeric_set_2).is_empty()

    def test_op_le_intervals_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(3.5, 4.5), (5.0, 6.0)])
        assert numeric_set_1.op_le_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [True]

    def test_op_le_intervals_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(3.5, 4.5), (5.0, 6.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set_1.op_le_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [False]

    def test_op_lt_intervals_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        assert numeric_set_1.op_lt_intervals(g=g, tg=tg, other=numeric_set_2).is_empty()

    def test_op_lt_intervals_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(3.5, 4.5), (5.0, 6.0)])
        assert numeric_set_1.op_lt_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [True]

    def test_op_lt_intervals_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(3.5, 4.5), (5.0, 6.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set_1.op_lt_intervals(
            g=g, tg=tg, other=numeric_set_2
        ).get_boolean_values() == [False]

    def test_op_round(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(
            values=[(0.0001, 1.0123456789), (2.4532450, 3.432520)]
        )
        result = numeric_set.op_round(g=g, tg=tg, ndigits=3)
        intervals = result.get_intervals()
        assert len(intervals) == 2
        assert intervals[0].get_min_value() == 0.0
        assert intervals[0].get_max_value() == 1.012
        assert intervals[1].get_min_value() == 2.453
        assert intervals[1].get_max_value() == 3.433

    def test_op_abs(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(-10.0, -5.0), (1.0, 3.0)])
        result = numeric_set.op_abs(g=g, tg=tg)
        intervals = result.get_intervals()
        assert len(intervals) == 2
        assert intervals[0].get_min_value() == 1.0
        assert intervals[0].get_max_value() == 3.0
        assert intervals[1].get_min_value() == 5.0
        assert intervals[1].get_max_value() == 10.0

    def test_op_log(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(0.1, 1.0), (2.0, 3.0)])
        result = numeric_set.op_log(g=g, tg=tg)
        intervals = result.get_intervals()
        assert len(intervals) == 2
        assert intervals[0].get_min_value() == math.log(0.1)
        assert intervals[0].get_max_value() == math.log(1.0)
        assert intervals[1].get_min_value() == math.log(2.0)
        assert intervals[1].get_max_value() == math.log(3.0)

    def test_op_sin(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        result = numeric_set.op_sin(g=g, tg=tg)
        intervals = result.get_intervals()
        assert len(intervals) == 1
        assert intervals[0].get_min_value() == math.sin(0.0)
        assert intervals[0].get_max_value() == math.sin(2.0)

    def test_contains(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set.contains(0.5)
        assert numeric_set.contains(0.0)
        assert numeric_set.contains(1.0)
        assert numeric_set.contains(2.0)
        assert numeric_set.contains(3.0)
        assert not numeric_set.contains(4.0)

    def test_eq(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_1.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_2.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set_1.equals(numeric_set_2)
        numeric_set_3 = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_3.setup_from_values(values=[(0.0, 1.0), (2.0, 4.0)])
        assert not numeric_set_1.equals(numeric_set_3)

    def test_repr(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert repr(numeric_set) == "_N_intervals([0.0, 1.0], [2.0, 3.0])"

    def test_iter(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])

        for interval in numeric_set:
            assert interval.get_min_value() >= 0.0
            assert interval.get_max_value() <= 3.0

    def test_is_single_element(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set_single_element = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_single_element.setup_from_values(values=[(1.0, 1.0)])
        assert numeric_set_single_element.is_single_element()

        numeric_set_multiple_elements = NumericSet.create_instance(g=g, tg=tg)
        numeric_set_multiple_elements.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert not numeric_set_multiple_elements.is_single_element()

    def test_any(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        numeric_set.setup_from_values(values=[(0.0, 1.0), (2.0, 3.0)])
        assert numeric_set.any() == 0.0


class Numbers(fabll.Node):
    from faebryk.library.Parameters import can_be_operand

    is_literal = fabll.Traits.MakeEdge(is_literal.MakeChild())
    as_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())
    _numeric_set_identifier: ClassVar[str] = "numeric_set"
    _has_unit_identifier: ClassVar[str] = "has_unit"

    @classmethod
    def MakeChild(  # type: ignore
        cls,
        min: float,
        max: float,
        unit: type[fabll.NodeT],
    ) -> fabll._ChildField:
        """
        Create a Numbers literal as a child field at type definition time.

        Args:
            min: Minimum value of the interval
            max: Maximum value of the interval
            unit: Unit type for the quantity. If None, no has_unit trait is added.
                  Useful for internal scalar values like unit multipliers/offsets
                  that don't have dimensional meaning. For user-facing quantities,
                  explicitly pass Dimensionless if the quantity is dimensionless.
        """
        if not NumericInterval.validate_bounds(min, max):
            raise ValueError(f"Invalid interval: {min} > {max}")
        out = fabll._ChildField(cls)
        numeric_set = NumericSet.MakeChild(min=min, max=max)
        out.add_dependant(numeric_set, identifier=cls._numeric_set_identifier)
        out.add_dependant(
            fabll.MakeEdge(
                [out],
                [numeric_set],
                edge=fbrk.EdgeComposition.build(
                    child_identifier=cls._numeric_set_identifier
                ),
            ),
            identifier=cls._numeric_set_identifier,
        )
        from faebryk.library.Units import has_unit

        out.add_dependant(
            fabll.Traits.MakeEdge(has_unit.MakeChild(unit), [out]),
            identifier=cls._has_unit_identifier,
        )

        return out

    @classmethod
    def MakeChild_SingleValue(
        cls,
        value: float,
        unit: type[fabll.NodeT],
    ) -> fabll._ChildField:
        return cls.MakeChild(min=value, max=value, unit=unit)

    @classmethod
    def MakeChild_ConstrainToLiteral(
        cls,
        param_ref: fabll.RefPath,
        min: float,
        max: float,
        unit: type[fabll.NodeT],
    ) -> fabll._ChildField["F.Expressions.Is"]:
        """
        Create a Numbers literal and constrain a parameter to it.
        Works at type definition time (no g/tg needed).

        Args:
            param_ref: Reference path to the parameter to constrain
            min: Minimum value of the interval (or the singleton value if max is None)
            max: Maximum value of the interval (if None, uses min for singleton)
            unit: Unit type for the quantity (if None, no has_unit trait is added)

        Returns:
            A _ChildField representing the Is constraint expression
        """
        from faebryk.library.Expressions import Is

        lit = cls.MakeChild(min=min, max=max, unit=unit)
        out = Is.MakeChild_Constrain([param_ref, [lit]])
        out.add_dependant(lit, identifier="lit", before=True)
        return out

    @classmethod
    def MakeChild_FromCenterRel(
        cls,
        center: float,
        rel: float,
        unit: type[fabll.NodeT],
    ) -> fabll._ChildField["F.Literals.Numbers"]:
        return cls.MakeChild(
            min=center - rel * center, max=center + rel * center, unit=unit
        )

    @classmethod
    def MakeChild_ConstrainToSingleton(
        cls,
        param_ref: fabll.RefPath,
        value: float,
        unit: type[fabll.NodeT],
    ) -> fabll._ChildField["F.Expressions.Is"]:
        """
        Create a singleton Numbers literal and constrain a parameter to it.
        Works at type definition time (no g/tg needed).

        Args:
            param_ref: Reference path to the parameter to constrain
            value: Single value for the quantity
            unit: Unit type for the quantity (if None, no has_unit trait is added)

        Returns:
            A _ChildField representing the Is constraint expression
        """
        return cls.MakeChild_ConstrainToLiteral(
            param_ref=param_ref, min=value, max=value, unit=unit
        )

    @classmethod
    def create_instance(cls, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        return cls.bind_typegraph(tg=tg).create_instance(g=g)

    def setup(  # type: ignore
        self,
        numeric_set: NumericSet,
        unit: "is_unit",
    ) -> "Numbers":
        g = self.g
        tg = self.tg
        _ = fbrk.EdgeComposition.add_child(
            bound_node=self.instance,
            child=numeric_set.instance.node(),
            child_identifier=self._numeric_set_identifier,
        )

        from faebryk.library.Units import has_unit

        has_unit_instance = (
            has_unit.bind_typegraph(tg=tg).create_instance(g=g).setup(unit=unit)
        )

        _ = fbrk.EdgeTrait.add_trait_instance(
            bound_node=self.instance,
            trait_instance=has_unit_instance.instance.node(),
        )

        return self

    def setup_from_center_rel(
        self,
        center: float,
        rel: float,
        unit: "is_unit",
    ) -> "Numbers":
        """
        Create a Numbers literal from a center and relative tolerance.
        """
        g = self.g
        tg = self.tg
        numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
            values=[(center - rel * center, center + rel * center)]
        )
        return self.setup(numeric_set=numeric_set, unit=unit)

    def setup_from_min_max(
        self,
        min: float,
        max: float,
        unit: "is_unit",
    ) -> "Numbers":
        g = self.g
        tg = self.tg
        numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
            values=[(min, max)]
        )
        return self.setup(numeric_set=numeric_set, unit=unit)

    @classmethod
    def unbounded(
        cls, g: graph.GraphView, tg: fbrk.TypeGraph, unit: "is_unit"
    ) -> "Numbers":
        """Create an unbounded quantity set (-∞, +∞) with the given unit."""
        quantity_set = cls.create_instance(g=g, tg=tg)
        return quantity_set.setup_from_min_max(min=-math.inf, max=math.inf, unit=unit)

    def setup_from_singleton(self, value: float, unit: "is_unit") -> "Numbers":
        return self.setup_from_min_max(min=value, max=value, unit=unit)

    def get_numeric_set(self) -> NumericSet:
        numeric_set = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._numeric_set_identifier
        )
        assert numeric_set is not None
        return NumericSet.bind_instance(numeric_set)

    def get_is_unit(self) -> "is_unit":
        from faebryk.library.Units import has_unit

        return self.get_trait(has_unit).get_is_unit()

    def get_unit_node(self) -> fabll.Node:
        from faebryk.library.Units import has_unit

        return self.get_trait(has_unit).unit.get().deref()

    def is_empty(self) -> bool:
        return self.get_numeric_set().is_empty()

    def get_value(self) -> float:
        """
        Get the singleton value from this Numbers literal.
        Raises ValueError if this is not a singleton (min != max).

        This is a convenience method for extracting scalar values
        like unit multipliers and offsets.
        """
        numeric_set = self.get_numeric_set()
        if not numeric_set.is_single_element():
            raise ValueError(
                f"Expected singleton value, got interval: "
                f"[{numeric_set.get_min_value()}, {numeric_set.get_max_value()}]"
            )
        return numeric_set.get_min_value()

    def get_values(self) -> list[float]:
        # TODO: Implement this as needed
        numeric_set = self.get_numeric_set()
        return [numeric_set.get_min_value(), numeric_set.get_max_value()]

    def get_min_value(self) -> float:
        if self.is_empty():
            raise ValueError("empty interval cannot have min element")
        return self.get_numeric_set().get_min_value()

    def get_max_value(self) -> float:
        if self.is_empty():
            raise ValueError("empty interval cannot have max element")
        return self.get_numeric_set().get_max_value()

    def min_elem(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """Return the minimum element as a single-value Numbers."""

        min_value = self.get_min_value()
        return Numbers.create_instance(g=g, tg=tg).setup_from_min_max(
            min=min_value, max=min_value, unit=self.get_is_unit()
        )

    def max_elem(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """Return the maximum element as a single-value Numbers."""

        max_value = self.get_max_value()
        return Numbers.create_instance(g=g, tg=tg).setup_from_min_max(
            min=max_value, max=max_value, unit=self.get_is_unit()
        )

    def is_singleton(self) -> float | None:
        if self.get_numeric_set().is_single_element():
            return self.get_min_value()
        return None

    def closest_elem(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, target: "Numbers"
    ) -> "Numbers":
        """
        Find the closest element in this quantity set to a target value.
        Target must be a single value (min == max).
        Units must be commensurable. Returns a single-element quantity set.
        """
        if not self.get_is_unit().is_commensurable_with(target.get_is_unit()):
            raise ValueError("incompatible units")
        if not target.get_numeric_set().is_single_element():
            raise ValueError("target must be a single value, not a range")
        target_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=target)
        target_value = target_converted.get_numeric_set().get_min_value()
        closest = self.get_numeric_set().closest_elem(target_value)
        result = Numbers.create_instance(g=g, tg=tg)
        return result.setup_from_min_max(
            min=closest, max=closest, unit=self.get_is_unit()
        )

    def has_compatible_units_with(self, other: "Numbers") -> bool:
        return self.get_is_unit().is_commensurable_with(other.get_is_unit())

    def are_units_compatible(self, unit: "F.Units.is_unit") -> bool:
        return self.get_is_unit().is_commensurable_with(unit)

    def is_superset_of(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> bool:
        """
        Check if this quantity set is a superset of another.
        Returns False if units are not commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            return False
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        return self.get_numeric_set().is_superset_of(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )

    def is_subset_of(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> bool:
        """
        Check if this quantity set is a subset of another.
        Returns False if units are not commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            return False
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        return self.get_numeric_set().is_subset_of(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )

    def op_intersect_interval(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Numbers":
        """
        Compute the intersection of this quantity set with another.
        Units must be commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        out_numeric_set = self.get_numeric_set().op_intersect_intervals(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    @staticmethod
    def op_intersect_intervals(
        g: graph.GraphView, tg: fbrk.TypeGraph, *others: "Numbers"
    ) -> "Numbers":
        """
        Compute the intersection of multiple quantity sets.
        All sets must have commensurable units.
        """
        if not others:
            raise ValueError("intersect_all requires at least one quantity set")
        result = others[0]
        for other in others[1:]:
            result = result.op_intersect_interval(g=g, tg=tg, other=other)
        return result

    def op_union_interval(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Numbers":
        """
        Compute the union of this quantity set with another.
        Units must be commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        out_numeric_set = self.get_numeric_set().op_union(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    @staticmethod
    def op_union_intervals(
        g: graph.GraphView, tg: fbrk.TypeGraph, *others: "Numbers"
    ) -> "Numbers":
        """
        Compute the union of multiple quantity sets.
        All sets must have commensurable units.
        """
        if not others:
            raise ValueError("union_all requires at least one quantity set")
        result = others[0]
        for other in others[1:]:
            result = result.op_union_interval(g=g, tg=tg, other=other)
        return result

    def op_difference_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Numbers":
        """
        Compute the set difference of this quantity set minus another.
        Returns elements that are in self but not in other.
        Units must be commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        out_numeric_set = self.get_numeric_set().op_difference_intervals(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    def convert_to_unit(self, g: graph.GraphView, tg: fbrk.TypeGraph, unit: "is_unit"):
        """
        Convert to specified unit.
        """
        if not self.get_is_unit().is_commensurable_with(unit):
            raise ValueError("incompatible units")

        scale, offset = self.get_is_unit().get_conversion_to(unit)

        # Generate a numeric set for the scale
        scale_numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
            values=[(scale, scale)]
        )

        # Generate a numeric set for the offset
        offset_numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
            values=[(offset, offset)]
        )

        # Multiply the other numeric set by the scale
        out_numeric_set = scale_numeric_set.op_multiply(
            g=g, tg=tg, other=self.get_numeric_set()
        )

        # Add the offset to the scaled numeric set
        out_numeric_set = out_numeric_set.op_add(g=g, tg=tg, other=offset_numeric_set)

        # Return the new quantity set
        return Numbers.create_instance(g=g, tg=tg).setup(
            numeric_set=out_numeric_set, unit=self.get_is_unit()
        )

    def _convert_other_to_self_unit(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Numbers":
        """
        Convert between two units with the same basis vector but different multiplier
        and offset.
        eg Celsius to Kelvin.
        Returns a new Numbers from other with the converted values in the units of self.
        """
        return other.convert_to_unit(g=g, tg=tg, unit=self.get_is_unit())

    def convert_to_dimensionless(
        self, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> "Numbers":
        """
        Convert to dimensionless units.
        Returns a new Numbers with the converted values in dimensionless units.
        Offset and scale are applied to the returned NumericSet.
        """
        from faebryk.library.Units import Dimensionless, is_unit

        scale = self.get_is_unit()._extract_multiplier()
        offset = self.get_is_unit()._extract_offset()

        # Generate a numeric set for the scale
        scale_numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
            values=[(scale, scale)]
        )

        # Generate a numeric set for the offset
        offset_numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
            values=[(offset, offset)]
        )

        # Multiply the other numeric set by the scale
        out_numeric_set = scale_numeric_set.op_multiply(
            g=g, tg=tg, other=self.get_numeric_set()
        )

        # Add the offset to the scaled numeric set
        out_numeric_set = out_numeric_set.op_add(g=g, tg=tg, other=offset_numeric_set)

        dimensionless_unit = Dimensionless.bind_typegraph(tg=tg).create_instance(g=g)
        dimensionless_is_unit = dimensionless_unit.get_trait(is_unit)

        # Return the new quantity set
        return Numbers.create_instance(g=g, tg=tg).setup(
            numeric_set=out_numeric_set, unit=dimensionless_is_unit
        )

    def op_add_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Numbers":
        """Arithmetically add two quantity sets. Units must be commensurable."""
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        out_numeric_set = self.get_numeric_set().op_add(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    def op_mul_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Numbers":
        """
        Arithmetically multiply two quantity sets.
        Result unit is self.unit * other.unit.
        """
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        out_numeric_set = self.get_numeric_set().op_multiply(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )
        result_unit = self.get_is_unit().op_multiply(
            g=g, tg=tg, other=other_converted.get_is_unit()
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=result_unit,
        )

    def op_negate(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Arithmetically negate this quantity set (multiply by -1).
        Unit remains the same.
        """
        out_numeric_set = self.get_numeric_set().op_negate(g=g, tg=tg)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    def op_subtract_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Numbers":
        """
        Subtract another quantity set from this one.
        Units must be commensurable. Result has the unit of self.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        out_numeric_set = self.get_numeric_set().op_subtract(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    def op_invert(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Invert this quantity set (1/x).
        Unit is also inverted.
        """
        out_numeric_set = self.get_numeric_set().op_invert(g=g, tg=tg)
        inverted_unit = self.get_is_unit().op_invert(g=g, tg=tg)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=inverted_unit,
        )

    def op_div_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Numbers":
        """
        Divide this quantity set by another.
        Result unit is self.unit / other.unit.
        Unlike add/subtract, division doesn't require commensurable units.
        """
        out_numeric_set = self.get_numeric_set().op_div_intervals(
            g=g, tg=tg, other=other.get_numeric_set()
        )
        divided_unit = self.get_is_unit().op_divide(
            g=g, tg=tg, other=other.get_is_unit()
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=divided_unit,
        )

    def op_pow_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, exponent: "Numbers"
    ) -> "Numbers":
        """
        Raise this quantity set to a power.
        Exponent must be dimensionless. If exponent is a range (not single value),
        then the base must also be dimensionless.
        """
        if not exponent.get_is_unit().is_dimensionless():
            raise ValueError("exponent must have dimensionless units")

        exp_numeric = exponent.get_numeric_set()
        if not exp_numeric.is_single_element():
            if not self.get_is_unit().is_dimensionless():
                raise ValueError(
                    "base must have dimensionless units when exponent is an interval"
                )

        # Get the exponent value for unit calculation (use min value)
        exp_value = int(exp_numeric.get_min_value())
        result_unit = self.get_is_unit().op_power(g=g, tg=tg, exponent=exp_value)

        out_numeric_set = self.get_numeric_set().op_pow(g, tg, other=exp_numeric)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=result_unit,
        )

    def op_round(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, ndigits: int = 0
    ) -> "Numbers":
        """
        Round this quantity set to the specified number of decimal places.
        Unit remains the same.
        """
        out_numeric_set = self.get_numeric_set().op_round(g=g, tg=tg, ndigits=ndigits)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    def op_abs(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Take the absolute value of this quantity set.
        Unit remains the same.
        """
        out_numeric_set = self.get_numeric_set().op_abs(g=g, tg=tg)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    def op_log(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Take the natural logarithm of this quantity set.
        Unit remains the same (should be dimensionless for physical meaning).
        """
        out_numeric_set = self.get_numeric_set().op_log(g=g, tg=tg)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    def op_sqrt(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Take the square root of this quantity set.
        Equivalent to raising to the power of 0.5.
        """
        # Create a dimensionless quantity set with value 0.5
        from faebryk.library.Units import Dimensionless, is_unit

        dimensionless_unit = Dimensionless.bind_typegraph(tg=tg).create_instance(g=g)
        half = Numbers.create_instance(g=g, tg=tg)
        half.setup_from_min_max(
            min=0.5, max=0.5, unit=dimensionless_unit.get_trait(is_unit)
        )
        return self.op_pow_intervals(g=g, tg=tg, exponent=half)

    def op_sin(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Take the sine of this quantity set.
        Input must be in radians.
        Result is dimensionless.
        """
        if not self.get_is_unit().is_angular():
            raise ValueError("sin only defined for quantities in radians")
        out_numeric_set = self.get_numeric_set().op_sin(g=g, tg=tg)
        # Result is dimensionless
        from faebryk.library.Units import Dimensionless, is_unit

        dimensionless_unit = Dimensionless.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=dimensionless_unit.get_trait(is_unit),
        )

    def op_cos(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Take the cosine of this quantity set.
        Input must be in radians.
        Computed as sin(x + pi/2).
        Result is dimensionless.
        """
        if not self.get_is_unit().is_angular():
            raise ValueError("cos only defined for quantities in radians")
        # Create pi/2 offset in radians
        pi_half = Numbers.create_instance(g=g, tg=tg)
        pi_half.setup_from_min_max(
            min=math.pi / 2, max=math.pi / 2, unit=self.get_is_unit()
        )
        shifted = self.op_add_intervals(g=g, tg=tg, other=pi_half)
        return shifted.op_sin(g=g, tg=tg)

    def op_floor(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Floor this quantity set (round down to nearest integer).
        Computed as round(x - 0.5).
        """
        half = Numbers.create_instance(g=g, tg=tg)
        half.setup_from_min_max(min=0.5, max=0.5, unit=self.get_is_unit())
        shifted = self.op_subtract_intervals(g=g, tg=tg, other=half)
        return shifted.op_round(g=g, tg=tg, ndigits=0)

    def op_ceil(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Ceiling this quantity set (round up to nearest integer).
        Computed as round(x + 0.5).
        """
        half = Numbers.create_instance(g=g, tg=tg)
        half.setup_from_min_max(min=0.5, max=0.5, unit=self.get_is_unit())
        shifted = self.op_add_intervals(g=g, tg=tg, other=half)
        return shifted.op_round(g=g, tg=tg, ndigits=0)

    def op_total_span(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Returns the total span of all intervals in this disjoint set.
        For a single interval, this is equivalent to max - min.
        For multiple intervals, this sums the spans of each disjoint interval.
        """
        intervals = self.get_numeric_set().get_intervals()
        total = sum(
            abs(interval.get_max_value() - interval.get_min_value())
            for interval in intervals
        )
        result = Numbers.create_instance(g=g, tg=tg)
        return result.setup_from_min_max(min=total, max=total, unit=self.get_is_unit())

    def op_symmetric_difference_intervals(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Numbers":
        """
        Compute the symmetric difference of this quantity set with another.
        Returns intervals that are in one set but not both.
        Units must be commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        out_numeric_set = self.get_numeric_set().op_symmetric_difference_intervals(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            numeric_set=out_numeric_set,
            unit=self.get_is_unit(),
        )

    def op_deviation_to(
        self,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        other: "Numbers",
        relative: bool = False,
    ) -> "Numbers":
        """
        Calculate the deviation between this quantity set and another.
        Returns the total span of the symmetric difference.

        Args:
            g: Graph view
            tg: Type graph
            other: The quantity set to compare against
            relative: If True, return deviation relative to max absolute value

        Returns:
            A Numbers representing the deviation (single value).
            If relative=True, result is dimensionless.
        """
        sym_diff = self.op_symmetric_difference_intervals(g=g, tg=tg, other=other)
        deviation = sym_diff.op_total_span(g=g, tg=tg)

        if relative:
            # Get max absolute values from both sets
            self_abs = self.op_abs(g=g, tg=tg)
            other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
            other_abs = other_converted.op_abs(g=g, tg=tg)

            self_max = self_abs.get_numeric_set().get_max_value()
            other_max = other_abs.get_numeric_set().get_max_value()
            max_val = max(self_max, other_max)

            if max_val == 0:
                # Avoid division by zero - both are zero, so relative deviation is 0
                from faebryk.library.Units import Dimensionless

                dimensionless_unit = Dimensionless.bind_typegraph(
                    tg=tg
                ).create_instance(g=g)
                result = Numbers.create_instance(g=g, tg=tg)
                dimensionless_is_unit = dimensionless_unit.get_trait(is_unit)
                return result.setup_from_min_max(
                    min=0.0, max=0.0, unit=dimensionless_is_unit
                )

            # Create divisor quantity set
            divisor = Numbers.create_instance(g=g, tg=tg)
            divisor.setup_from_min_max(
                min=max_val, max=max_val, unit=self.get_is_unit()
            )
            return deviation.op_div_intervals(g=g, tg=tg, other=divisor)

        return deviation

    def is_single_element(self) -> bool:
        """Check if this quantity set contains exactly one value."""
        return self.get_numeric_set().is_single_element()

    def is_unbounded(self) -> bool:
        """Check if this quantity set extends to infinity in either direction."""
        numeric_set = self.get_numeric_set()
        return (
            numeric_set.get_min_value() == -math.inf
            or numeric_set.get_max_value() == math.inf
        )

    def is_finite(self) -> bool:
        """Check if this quantity set has finite bounds."""
        numeric_set = self.get_numeric_set()
        return (
            numeric_set.get_min_value() != -math.inf
            and numeric_set.get_max_value() != math.inf
        )

    def is_integer(self) -> bool:
        """Check if all values in this quantity set are integers."""
        return all(
            interval.is_integer() for interval in self.get_numeric_set().get_intervals()
        )

    def contains_value(self, value: float) -> bool:
        """
        Check if a numeric value is contained in this quantity set.
        The value should already be in the same units as this set.
        """
        return self.get_numeric_set().contains(value)

    def any(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """Return any element from this set as a single-value Numbers."""
        return self.min_elem(g=g, tg=tg)

    def as_gapless(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Numbers":
        """
        Return a quantity set spanning from min to max as a single interval.
        Fills in any gaps in disjoint intervals.
        """
        if self.is_empty():
            raise ValueError("empty interval cannot be made gapless")
        result = Numbers.create_instance(g=g, tg=tg)
        return result.setup_from_min_max(
            min=self.get_numeric_set().get_min_value(),
            max=self.get_numeric_set().get_max_value(),
            unit=self.get_is_unit(),
        )

    def op_greater_or_equal(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Booleans":
        """
        Check if self >= other (greater than or equal).
        Returns Booleans with possible values:
        - [True] if definitely >=
        - [False] if definitely <
        - [True, False] if uncertain (ranges overlap)
        Units must be commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        return self.get_numeric_set().op_ge_intervals(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )

    def op_greater_than(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Booleans":
        """
        Check if self > other (greater than).
        Returns Booleans with possible values:
        - [True] if definitely >
        - [False] if definitely <=
        - [True, False] if uncertain (ranges overlap)
        Units must be commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        return self.get_numeric_set().op_gt_intervals(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )

    def op_le(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Booleans":
        """
        Check if self <= other (less than or equal).
        Returns Booleans with possible values:
        - [True] if definitely <=
        - [False] if definitely >
        - [True, False] if uncertain (ranges overlap)
        Units must be commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        return self.get_numeric_set().op_le_intervals(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )

    def op_lt(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> "Booleans":
        """
        Check if self < other (less than).
        Returns Booleans with possible values:
        - [True] if definitely <
        - [False] if definitely >=
        - [True, False] if uncertain (ranges overlap)
        Units must be commensurable.
        """
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        return self.get_numeric_set().op_lt_intervals(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )

    def op_is_bit_set(
        self,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        bit_position: "Numbers",
    ) -> "Booleans":
        """
        Check if a specific bit is set in the value.
        Both self and bit_position must be single integer values.
        If either is not a single element, returns Booleans(False, True)
        indicating uncertainty.
        """

        if not self.is_single_element() or not bit_position.is_single_element():
            # Uncertain result when either is a range
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=BooleansAttributes.from_values(values=[False, True])
            )
        # TODO: this doesnt seem ideal
        value = int(self.get_numeric_set().get_min_value())
        bit = int(bit_position.get_numeric_set().get_min_value())
        is_set = ((value >> bit) & 1) == 1
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[is_set])
        )

    def __repr__(self) -> str:
        try:
            numeric_set = self.get_numeric_set()
            unit_symbol = self.get_is_unit().get_symbols()[0]
            return f"Numbers({numeric_set}, unit={unit_symbol})"
        except Exception:
            return "Numbers(<uninitialized>)"

    def __str__(self) -> str:
        return self.__repr__()

    def equals(self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers") -> bool:
        """
        Check equality with another Numbers.
        Two quantity sets are equal if they have commensurable units and
        the same numeric intervals (after unit conversion).
        """
        # Convert to same units and check commensurability
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        return self.get_numeric_set().equals(other_converted.get_numeric_set())

    def contains(
        self, g: graph.GraphView, tg: fbrk.TypeGraph, other: "Numbers"
    ) -> bool:
        other_converted = self._convert_other_to_self_unit(g=g, tg=tg, other=other)
        return self.get_numeric_set().contains(other_converted.get_value())

    def serialize(self) -> dict:
        """
        Serialize this quantity set to the API format.

        Returns a dict matching the component API format:
        {
            "type": "Quantity_Interval_Disjoint",
            "data": {
                "intervals": {
                    "type": "Numeric_Interval_Disjoint",
                    "data": {
                        "intervals": [
                            {"type": "Numeric_Interval", "data": {...}}
                        ]
                    }
                },
                "unit": "kiloohm"  # string unit name
            }
        }

        Values are in base SI units (e.g., ohms for resistance).
        Unit string indicates the display/original unit (e.g., "kiloohm").
        """
        as_base_units = self.convert_to_unit(
            g=self.g,
            tg=self.tg,
            unit=self.get_is_unit().to_base_units(g=self.g, tg=self.tg),
        )
        return {
            # legacy name for backwards compatibility
            "type": "Quantity_Interval_Disjoint",
            "data": {
                # note base unit for values only
                "intervals": as_base_units.get_numeric_set().serialize(),
                "unit": self.get_is_unit().serialize(),
            },
        }


class TestNumbers:
    def test_make_child(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class App(fabll.Node):
            from faebryk.library.Units import Meter

            quantity_set = Numbers.MakeChild(min=0.0, max=1.0, unit=Meter)

        app = App.bind_typegraph(tg=tg).create_instance(g=g)
        numeric_set = app.quantity_set.get().get_numeric_set()
        assert numeric_set.get_min_value() == 0.0
        assert numeric_set.get_max_value() == 1.0
        assert app.quantity_set.get().get_is_unit().get_symbols() == ["m"]

    def test_make_child_single_value(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class App(fabll.Node):
            from faebryk.library.Units import Meter

            quantity_set = Numbers.MakeChild_SingleValue(value=1.0, unit=Meter)

        app = App.bind_typegraph(tg=tg).create_instance(g=g)
        numeric_set = app.quantity_set.get().get_numeric_set()
        assert numeric_set.get_min_value() == 1.0
        assert numeric_set.get_max_value() == 1.0
        assert app.quantity_set.get().get_is_unit().get_symbols() == ["m"]

    def test_create_instance(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set.setup_from_min_max(
            min=0.0, max=1.0, unit=meter_instance.get_trait(is_unit)
        )
        assert quantity_set.get_numeric_set().get_min_value() == 0.0
        assert quantity_set.get_numeric_set().get_max_value() == 1.0
        assert not_none(quantity_set.get_is_unit().get_symbols() == ["m"])

    def test_setup_from_singleton(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set.setup_from_singleton(
            value=1.0, unit=meter_instance.get_trait(is_unit)
        )
        assert quantity_set.get_numeric_set().get_min_value() == 1.0

    def test_get_min_quantity(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=0.0, max=1.0, unit=meter_instance.get_trait(is_unit)
        )
        min_quantity = quantity_set.min_elem(g=g, tg=tg)
        assert min_quantity.get_numeric_set().get_min_value() == 0.0
        assert min_quantity.get_is_unit().get_symbols() == ["m"]

    def test_get_max_quantity(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=0.0, max=1.0, unit=meter_instance.get_trait(is_unit)
        )
        max_quantity = quantity_set.max_elem(g=g, tg=tg)
        assert max_quantity.get_numeric_set().get_max_value() == 1.0
        assert max_quantity.get_is_unit().get_symbols() == ["m"]

    def test_op_add_same_unit(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=1.0, unit=meter_instance.get_trait(is_unit)
        )
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=0.0, max=1.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_add_intervals(g=g, tg=tg, other=quantity_set_2)
        assert result.get_numeric_set().get_min_value() == 0.0
        assert result.get_numeric_set().get_max_value() == 2.0
        assert result.get_is_unit().get_symbols() == ["m"]

    def test_op_add_different_unit(self):
        # returns result in the self unit
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import DegreeCelsius, Kelvin, is_unit

        celsius = DegreeCelsius.bind_typegraph(tg=tg).create_instance(g=g)
        kelvin = Kelvin.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_celsius = Numbers.create_instance(g=g, tg=tg)
        quantity_celsius.setup_from_min_max(
            min=0.0, max=0.0, unit=celsius.get_trait(is_unit)
        )
        quantity_kelvin = Numbers.create_instance(g=g, tg=tg)
        quantity_kelvin.setup_from_min_max(
            min=0.0, max=0.0, unit=kelvin.get_trait(is_unit)
        )
        result = quantity_kelvin.op_add_intervals(g=g, tg=tg, other=quantity_celsius)
        result_numeric_set_rounded = result.get_numeric_set().op_round(
            g=g, tg=tg, ndigits=2
        )
        assert result_numeric_set_rounded.get_min_value() == 273.15
        assert result.get_is_unit().get_symbols() == ["K"]

    def test_op_multiply_same_unit(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import BasisVector, Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=2.0, max=4.0, unit=meter_instance.get_trait(is_unit)
        )
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=3.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_mul_intervals(g=g, tg=tg, other=quantity_set_2)
        assert result.get_numeric_set().get_min_value() == 6.0
        assert result.get_numeric_set().get_max_value() == 20.0
        result_unit_basis_vector = result.get_is_unit()._extract_basis_vector()
        assert result_unit_basis_vector == BasisVector(meter=2)

    def test_op_negate(self):
        """Test negation of a quantity set."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=2.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set.op_negate(g=g, tg=tg)
        # Negation flips the interval: [2, 5] -> [-5, -2]
        assert result.get_numeric_set().get_min_value() == -5.0
        assert result.get_numeric_set().get_max_value() == -2.0
        # Unit should remain the same
        assert result.get_is_unit().get_symbols() == ["m"]

    def test_op_subtract_same_unit(self):
        """Test subtraction of quantity sets with the same unit."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=5.0, max=10.0, unit=meter_instance.get_trait(is_unit)
        )
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=1.0, max=3.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_subtract_intervals(g=g, tg=tg, other=quantity_set_2)
        # [5, 10] - [1, 3] = [5-3, 10-1] = [2, 9]
        assert result.get_numeric_set().get_min_value() == 2.0
        assert result.get_numeric_set().get_max_value() == 9.0
        # Unit should remain the same as self
        assert result.get_is_unit().get_symbols() == ["m"]

    def test_op_invert(self):
        """Test inversion (1/x) of a quantity set."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import BasisVector, Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=2.0, max=4.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set.op_invert(g=g, tg=tg)
        # 1/[2, 4] = [1/4, 1/2] = [0.25, 0.5]
        assert result.get_numeric_set().get_min_value() == 0.25
        assert result.get_numeric_set().get_max_value() == 0.5
        # Unit should be inverted: m -> m^-1
        result_unit_basis_vector = result.get_is_unit()._extract_basis_vector()
        assert result_unit_basis_vector == BasisVector(meter=-1)

    def test_op_divide_same_unit(self):
        """Test division of quantity sets with the same unit."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import BasisVector, Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=4.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=2.0, max=4.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_div_intervals(g=g, tg=tg, other=quantity_set_2)
        # [4, 8] / [2, 4] = [4/4, 8/2] = [1, 4]
        assert result.get_numeric_set().get_min_value() == 1.0
        assert result.get_numeric_set().get_max_value() == 4.0
        # Unit should be m / m = dimensionless (m^0)
        result_unit_basis_vector = result.get_is_unit()._extract_basis_vector()
        assert result_unit_basis_vector == BasisVector()

    def test_op_divide_different_units(self):
        """Test division of quantity sets with different units."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import BasisVector, Meter, Second, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        second_instance = Second.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_distance = Numbers.create_instance(g=g, tg=tg)
        quantity_distance.setup_from_min_max(
            min=10.0, max=20.0, unit=meter_instance.get_trait(is_unit)
        )
        quantity_time = Numbers.create_instance(g=g, tg=tg)
        quantity_time.setup_from_min_max(
            min=2.0, max=5.0, unit=second_instance.get_trait(is_unit)
        )
        result = quantity_distance.op_div_intervals(g=g, tg=tg, other=quantity_time)
        # [10, 20] m / [2, 5] s = [10/5, 20/2] = [2, 10] m/s
        assert result.get_numeric_set().get_min_value() == 2.0
        assert result.get_numeric_set().get_max_value() == 10.0
        # Unit should be m / s = m * s^-1
        result_unit_basis_vector = result.get_is_unit()._extract_basis_vector()
        assert result_unit_basis_vector == BasisVector(meter=1, second=-1)

    def test_op_pow(self):
        """Test raising a quantity set to a power."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import BasisVector, Dimensionless, Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        dimensionless_instance = Dimensionless.bind_typegraph(tg=tg).create_instance(
            g=g
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=2.0, max=3.0, unit=meter_instance.get_trait(is_unit)
        )
        exponent = Numbers.create_instance(g=g, tg=tg)
        exponent.setup_from_min_max(
            min=2.0, max=2.0, unit=dimensionless_instance.get_trait(is_unit)
        )
        result = quantity_set.op_pow_intervals(g=g, tg=tg, exponent=exponent)
        # [2, 3]^2 = [4, 9]
        assert result.get_numeric_set().get_min_value() == 4.0
        assert result.get_numeric_set().get_max_value() == 9.0
        # Unit should be m^2
        result_unit_basis_vector = result.get_is_unit()._extract_basis_vector()
        assert result_unit_basis_vector == BasisVector(meter=2)

    def test_op_round(self):
        """Test rounding a quantity set."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=2.345, max=5.678, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set.op_round(g=g, tg=tg, ndigits=1)
        assert result.get_numeric_set().get_min_value() == 2.3
        assert result.get_numeric_set().get_max_value() == 5.7
        # Unit should remain the same
        assert result.get_is_unit().get_symbols() == ["m"]

    def test_op_abs(self):
        """Test absolute value of a quantity set."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Test with all-negative interval
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=-5.0, max=-2.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set.op_abs(g=g, tg=tg)
        # abs([-5, -2]) = [2, 5]
        assert result.get_numeric_set().get_min_value() == 2.0
        assert result.get_numeric_set().get_max_value() == 5.0
        # Unit should remain the same
        assert result.get_is_unit().get_symbols() == ["m"]

    def test_op_log(self):
        """Test natural log of a quantity set."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Dimensionless, is_unit

        dimensionless_instance = Dimensionless.bind_typegraph(tg=tg).create_instance(
            g=g
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=1.0, max=math.e, unit=dimensionless_instance.get_trait(is_unit)
        )
        result = quantity_set.op_log(g=g, tg=tg)
        # log([1, e]) = [0, 1]
        assert abs(result.get_numeric_set().get_min_value() - 0.0) < 1e-10
        assert abs(result.get_numeric_set().get_max_value() - 1.0) < 1e-10

    def test_op_sin(self):
        """Test sine of a quantity set in radians."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Radian, is_unit

        radian_instance = Radian.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=0.0, max=math.pi / 2, unit=radian_instance.get_trait(is_unit)
        )
        result = quantity_set.op_sin(g=g, tg=tg)
        # sin([0, pi/2] rad) = [0, 1]
        assert abs(result.get_numeric_set().get_min_value() - 0.0) < 1e-10
        assert abs(result.get_numeric_set().get_max_value() - 1.0) < 1e-10
        # Result should be dimensionless
        assert result.get_is_unit().is_dimensionless()

    def test_op_sin_rejects_dimensionless(self):
        """Test that sine rejects dimensionless input (must use radians)."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Dimensionless, is_unit

        dimensionless_instance = Dimensionless.bind_typegraph(tg=tg).create_instance(
            g=g
        )
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=0.0, max=math.pi / 2, unit=dimensionless_instance.get_trait(is_unit)
        )
        with pytest.raises(
            ValueError, match="sin only defined for quantities in radians"
        ):
            quantity_set.op_sin(g=g, tg=tg)

    def test_op_cos(self):
        """Test cosine of a quantity set in radians."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Radian, is_unit

        radian_instance = Radian.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=0.0, max=0.0, unit=radian_instance.get_trait(is_unit)
        )
        result = quantity_set.op_cos(g=g, tg=tg)
        # cos(0 rad) = 1
        assert abs(result.get_numeric_set().get_min_value() - 1.0) < 1e-10
        assert abs(result.get_numeric_set().get_max_value() - 1.0) < 1e-10
        # Result should be dimensionless
        assert result.get_is_unit().is_dimensionless()

    def test_op_total_span(self):
        """Test total span calculation of a quantity set."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=2.0, max=7.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set.op_total_span(g=g, tg=tg)
        # span of [2, 7] = 5
        assert result.get_numeric_set().get_min_value() == 5.0
        assert result.get_numeric_set().get_max_value() == 5.0
        # Unit should remain the same
        assert result.get_is_unit().get_symbols() == ["m"]

    def test_op_symmetric_difference(self):
        """Test symmetric difference of two quantity sets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 5]
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [3, 8]
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=3.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_symmetric_difference_intervals(
            g=g, tg=tg, other=quantity_set_2
        )
        # Symmetric difference of [0, 5] and [3, 8]:
        # In set1 only: [0, 3)
        # In set2 only: (5, 8]
        # Total span should be 3 + 3 = 6
        total_span = result.op_total_span(g=g, tg=tg)
        assert total_span.get_numeric_set().get_min_value() == 6.0

    def test_op_deviation_to(self):
        """Test deviation calculation between two quantity sets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 5]
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [3, 8]
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=3.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_deviation_to(g=g, tg=tg, other=quantity_set_2)
        # Deviation is the total span of symmetric difference = 6
        assert result.get_numeric_set().get_min_value() == 6.0
        assert result.get_numeric_set().get_max_value() == 6.0
        # Unit should remain the same
        assert result.get_is_unit().get_symbols() == ["m"]

    def test_op_deviation_to_relative(self):
        """Test relative deviation calculation between two quantity sets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 5]
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [3, 8]
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=3.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_deviation_to(
            g=g, tg=tg, other=quantity_set_2, relative=True
        )
        # Deviation = 6, max(abs) = 8, relative = 6/8 = 0.75
        assert result.get_numeric_set().get_min_value() == 0.75
        assert result.get_numeric_set().get_max_value() == 0.75
        # Result should be dimensionless (m / m = 1)
        assert result.get_is_unit().is_dimensionless()

    def test_closest_elem(self):
        """Test finding the closest element to a target."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set: [0, 3]
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=0.0, max=3.0, unit=meter_instance.get_trait(is_unit)
        )
        # Target: 5.0 (single value)
        target = Numbers.create_instance(g=g, tg=tg)
        target.setup_from_min_max(
            min=5.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set.closest_elem(g=g, tg=tg, target=target)
        # Closest to 5 in [0, 3] is 3
        assert result.get_numeric_set().get_min_value() == 3.0
        assert result.get_numeric_set().get_max_value() == 3.0

    def test_closest_elem_rejects_range(self):
        """Test that closest_elem rejects range targets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=0.0, max=3.0, unit=meter_instance.get_trait(is_unit)
        )
        # Target is a range, not a single value
        target = Numbers.create_instance(g=g, tg=tg)
        target.setup_from_min_max(
            min=4.0, max=6.0, unit=meter_instance.get_trait(is_unit)
        )
        with pytest.raises(ValueError, match="target must be a single value"):
            quantity_set.closest_elem(g=g, tg=tg, target=target)

    def test_is_superset_of(self):
        """Test superset check."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 10] - larger
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=10.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [2, 5] - smaller
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=2.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )

        assert quantity_set_1.is_superset_of(g=g, tg=tg, other=quantity_set_2) is True
        assert quantity_set_2.is_superset_of(g=g, tg=tg, other=quantity_set_1) is False

    def test_is_subset_of(self):
        """Test subset check."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 10] - larger
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=10.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [2, 5] - smaller
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=2.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )

        assert quantity_set_2.is_subset_of(g=g, tg=tg, other=quantity_set_1) is True
        assert quantity_set_1.is_subset_of(g=g, tg=tg, other=quantity_set_2) is False

    def test_op_intersect(self):
        """Test intersection of two quantity sets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 5]
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [3, 8]
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=3.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_intersect_interval(g=g, tg=tg, other=quantity_set_2)
        # Intersection of [0, 5] and [3, 8] is [3, 5]
        assert result.get_numeric_set().get_min_value() == 3.0
        assert result.get_numeric_set().get_max_value() == 5.0

    def test_op_intersect_intervals(self):
        """Test intersection of multiple quantity sets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 5]
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [3, 8]
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=3.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 3: [5, 12]
        quantity_set_3 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_3.setup_from_min_max(
            min=5.0, max=12.0, unit=meter_instance.get_trait(is_unit)
        )
        result = Numbers.op_intersect_intervals(
            g, tg, quantity_set_1, quantity_set_2, quantity_set_3
        )
        # Intersection of [0, 5], [3, 8], and [5, 12] is [5, 5]
        assert result.get_numeric_set().get_min_value() == 5.0
        assert result.get_numeric_set().get_max_value() == 5.0

    def test_op_union(self):
        """Test union of two quantity sets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 5]
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [3, 8]
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=3.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_union_interval(g=g, tg=tg, other=quantity_set_2)
        # Union of [0, 5] and [3, 8] is [0, 8]
        assert result.get_numeric_set().get_min_value() == 0.0
        assert result.get_numeric_set().get_max_value() == 8.0

    def test_op_union_intervals(self):
        """Test union of multiple quantity sets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 5]
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [3, 8]
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=3.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 3: [5, 12]
        quantity_set_3 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_3.setup_from_min_max(
            min=5.0, max=12.0, unit=meter_instance.get_trait(is_unit)
        )
        result = Numbers.op_union_intervals(
            g, tg, quantity_set_1, quantity_set_2, quantity_set_3
        )
        # Union of [0, 5], [3, 8], and [5, 12] is [0, 12]
        assert result.get_numeric_set().get_min_value() == 0.0
        assert result.get_numeric_set().get_max_value() == 12.0

    def test_op_difference(self):
        """Test difference of two quantity sets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Set 1: [0, 5]
        quantity_set_1 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_1.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        # Set 2: [3, 8]
        quantity_set_2 = Numbers.create_instance(g=g, tg=tg)
        quantity_set_2.setup_from_min_max(
            min=3.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set_1.op_difference_intervals(
            g=g, tg=tg, other=quantity_set_2
        )
        # Difference [0, 5] - [3, 8] is [0, 3)
        assert result.get_numeric_set().get_min_value() == 0.0
        assert result.get_numeric_set().get_max_value() == 3.0

    def test_is_single_element(self):
        """Test single element check."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # Single element
        single = Numbers.create_instance(g=g, tg=tg)
        single.setup_from_min_max(
            min=5.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        assert single.is_single_element() is True
        # Range
        range_set = Numbers.create_instance(g=g, tg=tg)
        range_set.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        assert range_set.is_single_element() is False

    def test_is_finite(self):
        """Test finite bounds check."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        finite = Numbers.create_instance(g=g, tg=tg)
        finite.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        assert finite.is_finite() is True
        assert finite.is_unbounded() is False

    def test_contains_value(self):
        """Test value containment check."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        assert quantity_set.contains_value(3.0)
        assert not quantity_set.contains_value(10.0)

    def test_any(self):
        """Test getting any element from set as a Numbers."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=3.0, max=7.0, unit=meter_instance.get_trait(is_unit)
        )
        # any() returns the minimum as a single-value Numbers
        result = quantity_set.any(g=g, tg=tg)
        assert result.get_numeric_set().get_min_value() == 3.0
        assert result.get_numeric_set().get_max_value() == 3.0
        assert result.is_single_element()
        # Unit should be preserved
        assert result.get_is_unit().get_symbols() == ["m"]

    def test_as_gapless(self):
        """Test converting to gapless interval."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=2.0, max=8.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set.as_gapless(g=g, tg=tg)
        assert result.get_numeric_set().get_min_value() == 2.0
        assert result.get_numeric_set().get_max_value() == 8.0

    def test_to_dimensionless(self):
        """Test converting to dimensionless units."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=2.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        result = quantity_set.convert_to_dimensionless(g=g, tg=tg)
        # Numeric values should be preserved
        assert result.get_numeric_set().get_min_value() == 2.0
        assert result.get_numeric_set().get_max_value() == 5.0
        # Unit should be dimensionless
        assert result.get_is_unit().is_dimensionless()

    def test_op_is_bit_set(self):
        """Test bit set operation."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Dimensionless, is_unit

        dimensionless = Dimensionless.bind_typegraph(tg=tg).create_instance(g=g)
        # Value 5 = 0b101 (bits 0 and 2 are set)
        value = Numbers.create_instance(g=g, tg=tg)
        value.setup_from_min_max(
            min=5.0, max=5.0, unit=dimensionless.get_trait(is_unit)
        )
        # Check bit 0
        bit0 = Numbers.create_instance(g=g, tg=tg)
        bit0.setup_from_min_max(min=0.0, max=0.0, unit=dimensionless.get_trait(is_unit))
        result0 = value.op_is_bit_set(g=g, tg=tg, bit_position=bit0)
        assert True in result0.get_boolean_values()  # bit 0 is set
        # Check bit 1
        bit1 = Numbers.create_instance(g=g, tg=tg)
        bit1.setup_from_min_max(min=1.0, max=1.0, unit=dimensionless.get_trait(is_unit))
        result1 = value.op_is_bit_set(g=g, tg=tg, bit_position=bit1)
        assert False in result1.get_boolean_values()  # bit 1 is not set
        # Check bit 2
        bit2 = Numbers.create_instance(g=g, tg=tg)
        bit2.setup_from_min_max(min=2.0, max=2.0, unit=dimensionless.get_trait(is_unit))
        result2 = value.op_is_bit_set(g=g, tg=tg, bit_position=bit2)
        assert True in result2.get_boolean_values()  # bit 2 is set

    def test_repr(self):
        """Test string representation."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        quantity_set = Numbers.create_instance(g=g, tg=tg)
        quantity_set.setup_from_min_max(
            min=2.0, max=5.0, unit=meter_instance.get_trait(is_unit)
        )
        repr_str = repr(quantity_set)
        assert "Numbers" in repr_str

    def test_eq_same(self):
        """Test equality of identical quantity sets."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        qs1 = Numbers.create_instance(g=g, tg=tg)
        qs1.setup_from_min_max(min=2.0, max=5.0, unit=meter_instance.get_trait(is_unit))
        qs2 = Numbers.create_instance(g=g, tg=tg)
        qs2.setup_from_min_max(min=2.0, max=5.0, unit=meter_instance.get_trait(is_unit))
        assert qs1.equals(g=g, tg=tg, other=qs2)

    def test_eq_different_values(self):
        """Test inequality when values differ."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        qs1 = Numbers.create_instance(g=g, tg=tg)
        qs1.setup_from_min_max(min=2.0, max=5.0, unit=meter_instance.get_trait(is_unit))
        qs2 = Numbers.create_instance(g=g, tg=tg)
        qs2.setup_from_min_max(min=3.0, max=6.0, unit=meter_instance.get_trait(is_unit))
        assert not qs1.equals(g=g, tg=tg, other=qs2)

    def test_eq_incompatible_units(self):
        """Test inequality when units are incompatible."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, Second, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        second_instance = Second.bind_typegraph(tg=tg).create_instance(g=g)
        qs1 = Numbers.create_instance(g=g, tg=tg)
        qs1.setup_from_min_max(min=2.0, max=5.0, unit=meter_instance.get_trait(is_unit))
        qs2 = Numbers.create_instance(g=g, tg=tg)
        qs2.setup_from_min_max(
            min=2.0, max=5.0, unit=second_instance.get_trait(is_unit)
        )
        pytest.raises(ValueError, qs1.equals, g=g, tg=tg, other=qs2)

    def test_serialize_api_format(self):
        """Test serialization to API format (Quantity_Interval_Disjoint)."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Ohm, is_unit

        # Values are already in base units (ohms), so we use base Ohm unit
        # 8000-12000 ohms = 8k-12k ohms, which represents "10kohm +/- 20%"
        ohm_instance = Ohm.bind_typegraph(tg=tg).create_instance(g=g)

        qs = Numbers.create_instance(g=g, tg=tg)
        qs.setup_from_min_max(
            min=8000.0, max=12000.0, unit=ohm_instance.get_trait(is_unit)
        )
        serialized = qs.serialize()

        assert serialized == {
            "type": "Quantity_Interval_Disjoint",
            "data": {
                "intervals": {
                    "type": "Numeric_Interval_Disjoint",
                    "data": {
                        "intervals": [
                            {
                                "type": "Numeric_Interval",
                                "data": {"min": 8000.0, "max": 12000.0},
                            }
                        ]
                    },
                },
                "unit": "Ω",
            },
        }

    def test_op_ge_definitely_true(self):
        """Test >= comparison when definitely true."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # [5, 10] >= [0, 3] is definitely True
        qs1 = Numbers.create_instance(g=g, tg=tg)
        qs1.setup_from_min_max(
            min=5.0, max=10.0, unit=meter_instance.get_trait(is_unit)
        )
        qs2 = Numbers.create_instance(g=g, tg=tg)
        qs2.setup_from_min_max(min=0.0, max=3.0, unit=meter_instance.get_trait(is_unit))
        result = qs1.op_greater_or_equal(g=g, tg=tg, other=qs2)
        assert result.get_boolean_values() == [True]

    def test_op_ge_definitely_false(self):
        """Test >= comparison when definitely false."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # [0, 3] >= [5, 10] is definitely False
        qs1 = Numbers.create_instance(g=g, tg=tg)
        qs1.setup_from_min_max(min=0.0, max=3.0, unit=meter_instance.get_trait(is_unit))
        qs2 = Numbers.create_instance(g=g, tg=tg)
        qs2.setup_from_min_max(
            min=5.0, max=10.0, unit=meter_instance.get_trait(is_unit)
        )
        result = qs1.op_greater_or_equal(g=g, tg=tg, other=qs2)
        assert result.get_boolean_values() == [False]

    def test_op_ge_uncertain(self):
        """Test >= comparison when uncertain (ranges overlap)."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # [0, 5] >= [3, 10] is uncertain
        qs1 = Numbers.create_instance(g=g, tg=tg)
        qs1.setup_from_min_max(min=0.0, max=5.0, unit=meter_instance.get_trait(is_unit))
        qs2 = Numbers.create_instance(g=g, tg=tg)
        qs2.setup_from_min_max(
            min=3.0, max=10.0, unit=meter_instance.get_trait(is_unit)
        )
        result = qs1.op_greater_or_equal(g=g, tg=tg, other=qs2)
        assert set(result.get_boolean_values()) == {True, False}

    def test_op_gt(self):
        """Test > comparison."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # [5, 10] > [0, 3] is definitely True
        qs1 = Numbers.create_instance(g=g, tg=tg)
        qs1.setup_from_min_max(
            min=5.0, max=10.0, unit=meter_instance.get_trait(is_unit)
        )
        qs2 = Numbers.create_instance(g=g, tg=tg)
        qs2.setup_from_min_max(min=0.0, max=3.0, unit=meter_instance.get_trait(is_unit))
        result = qs1.op_greater_than(g=g, tg=tg, other=qs2)
        assert result.get_boolean_values() == [True]

    def test_op_le(self):
        """Test <= comparison."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # [0, 3] <= [5, 10] is definitely True
        qs1 = Numbers.create_instance(g=g, tg=tg)
        qs1.setup_from_min_max(min=0.0, max=3.0, unit=meter_instance.get_trait(is_unit))
        qs2 = Numbers.create_instance(g=g, tg=tg)
        qs2.setup_from_min_max(
            min=5.0, max=10.0, unit=meter_instance.get_trait(is_unit)
        )
        result = qs1.op_le(g=g, tg=tg, other=qs2)
        assert result.get_boolean_values() == [True]

    def test_op_lt(self):
        """Test < comparison."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        from faebryk.library.Units import Meter, is_unit

        meter_instance = Meter.bind_typegraph(tg=tg).create_instance(g=g)
        # [0, 3] < [5, 10] is definitely True
        qs1 = Numbers.create_instance(g=g, tg=tg)
        qs1.setup_from_min_max(min=0.0, max=3.0, unit=meter_instance.get_trait(is_unit))
        qs2 = Numbers.create_instance(g=g, tg=tg)
        qs2.setup_from_min_max(
            min=5.0, max=10.0, unit=meter_instance.get_trait(is_unit)
        )
        result = qs1.op_lt(g=g, tg=tg, other=qs2)
        assert result.get_boolean_values() == [True]


@dataclass(frozen=True)
class CountAttributes(fabll.NodeAttributes):
    value: int


class _Count(fabll.Node[CountAttributes]):
    Attributes = CountAttributes

    @classmethod
    def MakeChild(cls, value: int) -> fabll._ChildField[Self]:  # type: ignore
        out = fabll._ChildField(cls, attributes=CountAttributes(value=value))
        return out

    @classmethod
    def create_instance(
        cls, g: graph.GraphView, tg: fbrk.TypeGraph, value: int
    ) -> "_Count":
        return _Count.bind_typegraph(tg).create_instance(
            g=g, attributes=CountAttributes(value=value)
        )

    def get_value(self) -> int:
        value = self.instance.node().get_dynamic_attrs().get("value", None)
        if value is None:
            raise ValueError("Count literal has no value")
        return int(value)


class TestCount:
    def test_make_child(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        expected_value = 1

        class App(fabll.Node):
            count = _Count.MakeChild(value=expected_value)

        app = App.bind_typegraph(tg=tg).create_instance(g=g)

        assert app.count.get().get_value() == expected_value

    def test_create_instance(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        expected_value = 42
        count = _Count.create_instance(g=g, tg=tg, value=expected_value)
        assert count.get_value() == expected_value

    def test_get_value_returns_int(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        count = _Count.create_instance(g=g, tg=tg, value=5)
        value = count.get_value()
        assert value == 5
        assert isinstance(value, int)

    def test_make_child_multiple(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class App(fabll.Node):
            count1 = _Count.MakeChild(value=10)
            count2 = _Count.MakeChild(value=20)
            count3 = _Count.MakeChild(value=30)

        app = App.bind_typegraph(tg=tg).create_instance(g=g)

        assert app.count1.get().get_value() == 10
        assert app.count2.get().get_value() == 20
        assert app.count3.get().get_value() == 30

    def test_zero_value(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        count = _Count.create_instance(g=g, tg=tg, value=0)
        assert count.get_value() == 0

    def test_negative_value(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        count = _Count.create_instance(g=g, tg=tg, value=-5)
        assert count.get_value() == -5


class Counts(fabll.Node):
    """
    A literal representing a set of integer count values.
    Used with CountParameter for constraining integer-valued parameters.
    """

    from faebryk.library.Parameters import can_be_operand

    is_literal = fabll.Traits.MakeEdge(is_literal.MakeChild())
    as_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())
    counts = F.Collections.PointerSet.MakeChild()

    @classmethod
    def MakeChild(cls, *values: int) -> fabll._ChildField[Self]:  # type: ignore
        """
        Create a Counts literal as a child field at type definition time.
        Does not require g or tg - works at type level.
        """
        out = fabll._ChildField(cls)

        _counts = [_Count.MakeChild(value=value) for value in values]
        out.add_dependant(
            *F.Collections.PointerSet.MakeEdges(
                [out, cls.counts], [[count] for count in _counts]
            )
        )
        out.add_dependant(*_counts, before=True)

        return out

    @classmethod
    def create_instance(cls, g: graph.GraphView, tg: fbrk.TypeGraph) -> "Counts":
        return cls.bind_typegraph(tg=tg).create_instance(g=g)

    def setup_from_values(self, values: list[int]) -> "Counts":
        g = self.g
        tg = self.tg
        for value in values:
            self.counts.get().append(_Count.create_instance(g=g, tg=tg, value=value))
        return self

    def get_counts(self) -> list[_Count]:
        return [count.cast(_Count) for count in self.counts.get().as_list()]

    def get_values(self) -> list[int]:
        return [count.get_value() for count in self.get_counts()]

    def is_empty(self) -> bool:
        return len(self.get_counts()) == 0

    def is_single_element(self) -> bool:
        values = self.get_values()
        return len(values) == 1

    def get_single(self) -> int:
        """
        Returns the single value if this is a singleton set, raises otherwise.
        """
        values = self.get_values()
        if len(values) != 1:
            raise ValueError(
                f"Expected single value, got {len(values)} values: {values}"
            )
        return values[0]

    def get_min(self) -> int:
        values = self.get_values()
        if not values:
            raise ValueError("Cannot get min of empty Counts")
        return min(values)

    def get_max(self) -> int:
        values = self.get_values()
        if not values:
            raise ValueError("Cannot get max of empty Counts")
        return max(values)

    def contains(self, item: int) -> bool:
        return item in self.get_values()

    def __repr__(self) -> str:
        return f"Counts({self.get_values()})"


class TestCounts:
    def test_make_child(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        expected_values = [1, 2, 3]

        class App(fabll.Node):
            count_set = Counts.MakeChild(*expected_values)

        app = App.bind_typegraph(tg=tg).create_instance(g=g)
        assert app.count_set.get().get_values() == expected_values

    def test_create_instance(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        assert counts.is_empty()

    def test_setup_from_values(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[5, 10, 15])
        assert counts.get_values() == [5, 10, 15]

    def test_get_counts(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[1, 2])
        count_list = counts.get_counts()
        assert len(count_list) == 2
        assert all(isinstance(c, _Count) for c in count_list)

    def test_is_empty_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        assert counts.is_empty() is True

    def test_is_empty_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[1])
        assert counts.is_empty() is False

    def test_is_single_element_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[42])
        assert counts.is_single_element() is True

    def test_is_single_element_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[1, 2])
        assert counts.is_single_element() is False

    def test_get_single(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[42])
        assert counts.get_single() == 42

    def test_get_single_raises_for_multiple(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[1, 2])
        with pytest.raises(ValueError, match="Expected single value"):
            counts.get_single()

    def test_get_single_raises_for_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        with pytest.raises(ValueError, match="Expected single value"):
            counts.get_single()

    def test_get_min(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[5, 2, 8, 1])
        assert counts.get_min() == 1

    def test_get_min_raises_for_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        with pytest.raises(ValueError, match="Cannot get min of empty"):
            counts.get_min()

    def test_get_max(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[5, 2, 8, 1])
        assert counts.get_max() == 8

    def test_get_max_raises_for_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        with pytest.raises(ValueError, match="Cannot get max of empty"):
            counts.get_max()

    def test_contains_true(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[1, 5, 10])
        assert counts.contains(5)
        assert counts.contains(1)
        assert counts.contains(10)

    def test_contains_false(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[1, 5, 10])
        assert not counts.contains(2)
        assert not counts.contains(0)
        assert not counts.contains(100)

    def test_repr(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        counts.setup_from_values(values=[1, 2, 3])
        assert repr(counts) == "Counts([1, 2, 3])"

    def test_repr_empty(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        counts = Counts.create_instance(g=g, tg=tg)
        assert repr(counts) == "Counts([])"


@dataclass(frozen=True)
class BooleansAttributes(fabll.NodeAttributes):
    has_true: bool
    has_false: bool

    @classmethod
    def from_values(cls, values: list[bool]) -> "BooleansAttributes":
        return cls(has_true=True in values, has_false=False in values)


class Booleans(fabll.Node[BooleansAttributes]):
    from faebryk.library.Parameters import can_be_operand

    Attributes = BooleansAttributes
    is_literal = fabll.Traits.MakeEdge(is_literal.MakeChild())
    as_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    def get_single(self) -> bool:
        """Get the single boolean value. Raises if not exactly one value."""
        values = self.get_values()
        if len(values) != 1:
            raise ValueError(f"Expected single boolean, got {len(values)}: {values}")
        return values[0]

    @classmethod
    def MakeChild(cls, *values: bool) -> fabll._ChildField[Self]:  # type: ignore
        return fabll._ChildField(
            cls,
            attributes=BooleansAttributes(
                has_true=True in values,
                has_false=False in values,
            ),
        )

    @classmethod
    def MakeChild_ConstrainToLiteral(
        cls, ref: fabll.RefPath, *values: bool
    ) -> fabll._ChildField:
        from faebryk.library.Expressions import Is

        lit = cls.MakeChild(*values)
        out = Is.MakeChild_Constrain([ref, [lit]])
        out.add_dependant(lit, before=True)
        return out

    def get_values(self) -> list[bool]:
        """Get the list of boolean values in this set."""
        match self.attributes():
            case BooleansAttributes(has_true=True, has_false=True):
                return [True, False]
            case BooleansAttributes(has_true=True, has_false=False):
                return [True]
            case BooleansAttributes(has_true=False, has_false=True):
                return [False]
            case _:
                return []

    def get_boolean_values(self) -> list[bool]:
        """Alias for get_values() for API compatibility."""
        return self.get_values()

    def is_empty(self) -> bool:
        """Check if this set contains no values."""
        attrs = self.attributes()
        return not attrs.has_true and not attrs.has_false

    def op_not(self, g: "graph.GraphView", tg: "fbrk.TypeGraph") -> "Booleans":
        """Logical NOT of all values in this set."""
        values = self.get_values()
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g,
            attributes=BooleansAttributes.from_values(values=[not v for v in values]),
        )

    def op_and(
        self, g: "graph.GraphView", tg: "fbrk.TypeGraph", other: "Booleans"
    ) -> "Booleans":
        """Logical AND of all combinations of values from both sets."""
        result = set()
        for v1 in self.get_values():
            for v2 in other.get_values():
                result.add(v1 and v2)
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=list(result))
        )

    def op_or(
        self, g: "graph.GraphView", tg: "fbrk.TypeGraph", other: "Booleans"
    ) -> "Booleans":
        """Logical OR of all combinations of values from both sets."""
        result = set()
        for v1 in self.get_values():
            for v2 in other.get_values():
                result.add(v1 or v2)
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=list(result))
        )

    def op_xor(
        self, g: "graph.GraphView", tg: "fbrk.TypeGraph", other: "Booleans"
    ) -> "Booleans":
        """Logical XOR of all combinations of values from both sets."""
        result = set()
        for v1 in self.get_values():
            for v2 in other.get_values():
                result.add(v1 != v2)
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=list(result))
        )

    def op_implies(
        self, g: "graph.GraphView", tg: "fbrk.TypeGraph", other: "Booleans"
    ) -> "Booleans":
        """Logical implication (self -> other) for all combinations."""
        result = set()
        for v1 in self.get_values():
            for v2 in other.get_values():
                result.add((not v1) or v2)
        return Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=list(result))
        )

    def is_true(self) -> bool:
        """Check if this set contains only True."""
        return self.get_values() == [True]

    def is_false(self) -> bool:
        """Check if this set contains only False."""
        return self.get_values() == [False]

    def equals(self, other: "Booleans") -> bool:
        """Check if two boolean sets have the same values."""
        return set(self.get_values()) == set(other.get_values())

    def is_singleton(self) -> bool | None:
        vals = self.get_values()
        if len(vals) != 1:
            return None
        return vals[0]

    def as_literal(self) -> "is_literal":
        return self.is_literal.get()


class EnumValue(fabll.Node):
    name_ = F.Collections.Pointer.MakeChild()
    value_ = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, name: str, value: str) -> fabll._ChildField[Self]:  # type: ignore
        out = fabll._ChildField(cls)
        F.Collections.Pointer.MakeEdgeForField(
            out,
            [out, cls.name_],
            Strings.MakeChild(name),
        )
        F.Collections.Pointer.MakeEdgeForField(
            out,
            [out, cls.value_],
            Strings.MakeChild(value),
        )
        return out

    @property
    def name(self) -> str:
        return self.name_.get().deref().cast(Strings).get_values()[0]

    @property
    def value(self) -> str:
        return self.value_.get().deref().cast(Strings).get_values()[0]


class AbstractEnums(fabll.Node):
    from faebryk.library.Parameters import can_be_operand

    is_literal = fabll.Traits.MakeEdge(is_literal.MakeChild())
    as_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())
    values = F.Collections.PointerSet.MakeChild()

    @staticmethod
    def get_enum_value(s: fabll.TypeNodeBoundTG, enum_member: Enum) -> EnumValue:
        for enum_value in s.as_type_node().get_children(
            direct_only=True, types=EnumValue, tg=s.tg
        ):
            enum_value_bound = EnumValue.bind_instance(instance=enum_value.instance)
            if enum_value_bound.name == enum_member.name:
                return enum_value_bound
        raise ValueError(f"Enum member {enum_member.name} not found in enum type")

    def setup(self, *enum_values: Enum) -> Self:
        atype = EnumsFactory(type(enum_values[0]))
        atype_n = atype.bind_typegraph(tg=self.tg)
        for enum_value in enum_values:
            self.values.get().append(
                AbstractEnums.get_enum_value(s=atype_n, enum_member=enum_value)
            )
        return self

    def get_values(self) -> list[str]:
        enum_values = list[str]()
        values = self.values.get().as_list()
        for value in values:
            enum_value = EnumValue.bind_instance(instance=value.instance)
            enum_values.append(enum_value.value)

        return enum_values

    def is_singleton(self) -> str | None:
        vals = self.get_values()
        if len(vals) != 1:
            return None
        return vals[0]

    def get_values_typed[T: Enum](self, EnumType: type[T]) -> list[T]:
        return [EnumType(value) for value in self.get_values()]

    def get_single_value_typed[T: Enum](self, EnumType: type[T]) -> T | None:
        values = self.get_values()
        return None if len(values) == 0 else EnumType(values[0])

    def get_all_members(self) -> list[EnumValue]:
        if (
            self.get_type_node() is None
        ):  # TODO better to do if self.try_get_trait(fabll.ImplementsType) is not None
            return list(self.get_children(direct_only=True, types=EnumValue))
        else:
            return list(
                fabll.Node.bind_instance(
                    instance=not_none(self.get_type_node())
                ).get_children(direct_only=True, types=EnumValue, tg=self.tg)
            )

    def get_enum_as_dict(self) -> dict[str, str]:
        return {member.name: member.value for member in self.get_all_members()}

    def get_single_value(self) -> str | None:
        values = self.get_values()
        return None if len(values) == 0 else values[0]

    @classmethod
    def MakeChild(cls, *enum_members: Enum) -> fabll._ChildField[Self]:  # type: ignore
        atype = EnumsFactory(type(enum_members[0]))
        cls_n = cast(type[fabll.NodeT], atype)
        out = fabll._ChildField(cls)

        for value in enum_members:
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge(
                    [out, cls.values],
                    [cls_n, value.name],
                )
            )
        return out

    @classmethod
    def MakeChild_ConstrainToLiteral(
        cls,
        enum_parameter_ref: fabll.RefPath,
        *enum_members: Enum,
    ) -> fabll._ChildField["F.Expressions.Is"]:
        from faebryk.library.Expressions import Is

        lit = cls.MakeChild(*enum_members)
        out = Is.MakeChild_Constrain([enum_parameter_ref, [lit]])
        out.add_dependant(lit, identifier="lit", before=True)
        return out

    def as_literal(self) -> "is_literal":
        return self.is_literal.get()


@once
def EnumsFactory(enum_type: type[Enum]) -> type[AbstractEnums]:
    ConcreteEnums = fabll.Node._copy_type(AbstractEnums)

    ConcreteEnums.__name__ = f"{enum_type.__name__}"

    for e_val in enum_type:
        ConcreteEnums._add_field(
            e_val.name,
            EnumValue.MakeChild(name=e_val.name, value=e_val.value).put_on_type(),
        )
    return ConcreteEnums


# --------------------------------------------------------------------------------------


LiteralNodes = Numbers | Booleans | Strings | AbstractEnums

LiteralLike = LiteralValues | LiteralNodes | is_literal


def make_simple_lit_singleton(
    g: graph.GraphView, tg: graph.TypeGraph, value: LiteralValues
) -> LiteralNodes:
    match value:
        case bool():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=g,
                attributes=BooleansAttributes(has_true=value, has_false=not value),
            )
        case float() | int():
            from faebryk.library.Units import Dimensionless

            value = float(value)
            return (
                Numbers.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .setup_from_singleton(
                    value=value,
                    unit=Dimensionless.bind_typegraph(tg=tg)
                    .create_instance(g=g)
                    .is_unit.get(),
                )
            )
        case Enum():
            return AbstractEnums.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=LiteralsAttributes(value=value)
            )
        case str():
            return Strings.bind_typegraph(tg=tg).create_instance(
                g=g, attributes=LiteralsAttributes(value=value)
            )


# Binding context ----------------------------------------------------------------------


class BoundLiteralContext:
    """
    Convenience context for binding types and creating instances within a graph.

    Usage:
        ctx = BoundLiteralContext(tg=tg, g=g)
        my_number = ctx.Numbers.setup_from_singleton(value=1.0)
    """

    def __init__(self, tg: graph.TypeGraph, g: graph.GraphView):
        self.tg = tg
        self.g = g
        self._bound: dict = {}

    def _get_bound(self, cls: type[LiteralNodes]):
        if cls not in self._bound:
            self._bound[cls] = cls.bind_typegraph(tg=self.tg)
        return self._bound[cls]

    @property
    def Numbers(self) -> "Numbers":
        return self._get_bound(Numbers).create_instance(g=self.g)

    @property
    def Booleans(self) -> "Booleans":
        return self._get_bound(Booleans).create_instance(g=self.g)

    @property
    @once
    def Enums(self):
        return AbstractEnums.bind_typegraph(tg=self.tg)

    @property
    @once
    def Strings(self):
        return Strings.bind_typegraph(tg=self.tg)

    def create_numbers(self) -> "Numbers":
        return self.Numbers.create_instance(g=self.g, tg=self.tg)

    def create_booleans(self, booleans: list[bool] | None = None) -> "Booleans":
        return Booleans.bind_typegraph(tg=self.tg).create_instance(
            g=self.g, attributes=BooleansAttributes.from_values(values=booleans or [])
        )

    def create_enums(self) -> "AbstractEnums":
        return self.Enums.create_instance(g=self.g)

    def create_strings(self) -> "Strings":
        return self.Strings.create_instance(g=self.g)

    def create_numbers_from_singleton(
        self,
        value: float,
        unit: "is_unit",
    ) -> "Numbers":
        """
        Create a Numbers literal with a single value.

        Args:
            value: The singleton value
            unit: Unit node. If None, no has_unit trait is added.
        """

        return self.create_numbers().setup_from_singleton(value=value, unit=unit)

    def create_numbers_from_interval(
        self,
        min: float,
        max: float,
        unit: "is_unit",
    ) -> "Numbers":
        """
        Create a Numbers literal with an interval [min, max].

        Args:
            min: Minimum value of the interval
            max: Maximum value of the interval
            unit: Unit node. If None, no has_unit trait is added.
        """

        return self.create_numbers().setup_from_min_max(min=min, max=max, unit=unit)

    # TODO add other literal constructors


def test_bound_context():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    ctx = BoundLiteralContext(tg=tg, g=g)
    from faebryk.library.Units import Ohm, is_unit

    ohm_instance = Ohm.bind_typegraph(tg=tg).create_instance(g=g)

    my_number = ctx.Numbers.setup_from_singleton(
        value=1.0, unit=ohm_instance.get_trait(is_unit)
    )
    my_bool = ctx.create_booleans(booleans=[True, False])

    assert my_number.get_value() == 1.0
    assert my_bool.get_values() == [True, False]


class TestStringLiterals:
    def test_string_literal_instance(self):
        values = ["a", "b", "c"]
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        string_set = (
            Strings.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_values(*values)
        )

        assert string_set.get_values() == values

    def test_string_literal_make_child(self):
        values = ["a", "b", "c"]
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class MyType(fabll.Node):
            string_set = Strings.MakeChild(*values)

        my_instance = MyType.bind_typegraph(tg=tg).create_instance(g=g)

        print(my_instance.string_set.get().get_values())
        assert my_instance.string_set.get().get_values() == values

    def test_string_literal_on_type(self):
        """Test that a Strings literal can be placed on a type node."""
        import faebryk.core.faebrykpy as fbrk

        values = ["a", "b", "c"]
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class MyType(fabll.Node):
            string_set = Strings.MakeChild(*values).put_on_type()

        # Bind the type to the typegraph and create the type node
        bound_type = MyType.bind_typegraph(tg=tg)
        type_node = bound_type.get_or_create_type()

        # Access the type-level string_set from the type node
        # With put_on_type(), the child is created on the type node itself
        child_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=type_node, child_identifier="string_set"
        )
        assert child_node is not None

        type_level_string_set = Strings.bind_instance(instance=child_node)
        assert type_level_string_set.get_values() == values

    def test_string_literal_alias_to_literal(self):
        from faebryk.library.Parameters import StringParameter, is_parameter_operatable

        values = ["a", "b", "c"]
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class MyType(fabll.Node):
            string_param = StringParameter.MakeChild()

            @classmethod
            def MakeChild(cls, *values: str) -> fabll._ChildField[Self]:  # type: ignore
                out = fabll._ChildField(cls)
                out.add_dependant(
                    Strings.MakeChild_ConstrainToLiteral(
                        [out, cls.string_param], *values
                    )
                )
                return out

        class MyTypeOuter(fabll.Node):
            my_type = MyType.MakeChild(*values)

        my_type_outer = MyTypeOuter.bind_typegraph(tg=tg).create_instance(g=g)

        lit = is_parameter_operatable.try_get_constrained_literal(
            my_type_outer.my_type.get()
            .string_param.get()
            .get_trait(is_parameter_operatable),
            Strings,
        )
        assert lit
        assert lit.get_values() == values

    def test_string_literal_is_singleton(self):
        values = ["a", "b", "c"]
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        string_set = Strings.bind_typegraph(tg=tg).create_instance(g=g)
        string_set.setup_from_values(*values)
        assert string_set.is_singleton() is None
        singleton_string_set = Strings.bind_typegraph(tg=tg).create_instance(g=g)
        singleton_string_set.setup_from_values("a")
        assert singleton_string_set.is_singleton() == "a"


class TestBooleans:
    def test_create_instance(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        bools = Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True, False])
        )
        assert set(bools.get_values()) == {True, False}

    def test_get_single(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        bools = Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True])
        )
        assert bools.get_single() is True

    def test_op_not(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        bools = Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True])
        )
        result = bools.op_not(g=g, tg=tg)
        assert result.get_values() == [False]

    def test_op_and(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        bools1 = Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True, False])
        )
        bools2 = Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True])
        )
        result = bools1.op_and(g=g, tg=tg, other=bools2)
        # True AND True = True, False AND True = False
        assert set(result.get_values()) == {True, False}

    def test_op_or(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        bools1 = Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[False])
        )
        bools2 = Booleans.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=BooleansAttributes.from_values(values=[True])
        )
        result = bools1.op_or(g=g, tg=tg, other=bools2)
        # False OR True = True
        assert result.get_values() == [True]


def test_string_literal_on_type():
    values = ["a", "b", "c"]
    g = graph.GraphView.create()
    tg = graph.TypeGraph.create(g=g)

    class MyType(fabll.Node):
        string_set = Strings.MakeChild(*values).put_on_type()

    _ = MyType.bind_typegraph(tg=tg).get_or_create_type()

    # TODO


def test_string_literal_alias_to_literal():
    from faebryk.library.Parameters import StringParameter, is_parameter_operatable

    values = ["a", "b", "c"]
    g = graph.GraphView.create()
    tg = graph.TypeGraph.create(g=g)

    class MyType(fabll.Node):
        string_param = StringParameter.MakeChild()

        @classmethod
        def MakeChild(cls, *values: str) -> fabll._ChildField[Self]:  # type: ignore
            out = fabll._ChildField(cls)
            out.add_dependant(
                Strings.MakeChild_ConstrainToLiteral([out, cls.string_param], *values)
            )
            return out

    class MyTypeOuter(fabll.Node):
        my_type = MyType.MakeChild(*values)

    my_type_outer = MyTypeOuter.bind_typegraph(tg=tg).create_instance(g=g)

    lit = is_parameter_operatable.try_get_constrained_literal(
        my_type_outer.my_type.get()
        .string_param.get()
        .get_trait(is_parameter_operatable),
        Strings,
    )
    assert lit
    assert lit.get_values() == values


def test_enums():
    """
    Tests carried over from enum_sets.py
    """
    from enum import Enum

    from faebryk.core.node import _make_graph_and_typegraph

    g, tg = _make_graph_and_typegraph()

    class MyEnum(Enum):
        A = "a"
        B = "b"
        C = "c"
        D = "d"

    EnumT = EnumsFactory(MyEnum)
    enum_lit = (
        EnumT.bind_typegraph(tg=tg).create_instance(g=g).setup(MyEnum.A, MyEnum.D)
    )

    elements = enum_lit.get_all_members()
    assert len(elements) == 4
    assert elements[0].name == "A"
    assert elements[0].value == MyEnum.A.value
    assert elements[1].name == "B"
    assert elements[1].value == MyEnum.B.value
    assert elements[2].name == "C"
    assert elements[2].value == MyEnum.C.value
    assert elements[3].name == "D"
    assert elements[3].value == MyEnum.D.value

    assert enum_lit.get_values() == ["a", "d"]


# def test_make_lit():
#     g = graph.GraphView.create()
#     tg = graph.TypeGraph.create(g=g)
#     assert make_lit(g, tg, value=True).get_values() == [True]
#     assert make_lit(g, tg, value=3).get_values() == [3]
#     assert make_lit(g, tg, value="test").get_values() == ["test"]


if __name__ == "__main__":
    import typer

    typer.run(test_enums)
