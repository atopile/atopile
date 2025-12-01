# FIXME: remove — duplicates Literals

import logging
import math
from bisect import bisect
from collections.abc import Generator
from dataclasses import dataclass
from typing import ClassVar

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph import graph
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)

REL_DIGITS = 7  # 99.99999% precision
ABS_DIGITS = 15  # femto
EPSILON_REL = 10 ** -(REL_DIGITS - 1)
EPSILON_ABS = 10**-ABS_DIGITS


def is_int(value: float) -> bool:
    return value == int(value)


def ge(a: float, b: float) -> bool:
    return a >= b


@dataclass(frozen=True)
class NumericAttributes(fabll.NodeAttributes):
    value: float


class Numeric(fabll.Node[NumericAttributes]):
    Attributes = NumericAttributes

    @classmethod
    def MakeChild(cls, value: float) -> fabll._ChildField:  # type: ignore
        out = fabll._ChildField(cls, attributes=NumericAttributes(value=value))
        return out

    @classmethod
    def create_instance(
        cls, g: graph.GraphView, tg: TypeGraph, value: float
    ) -> "Numeric":
        return Numeric.bind_typegraph(tg).create_instance(
            g=g, attributes=NumericAttributes(value=value)
        )

    def get_value(self) -> float:
        value = self.instance.node().get_dynamic_attrs().get("value", None)
        if value is None:
            raise ValueError("Numeric literal has no value")
        return float(value)


def test_numeric_make_child():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    expected_value = 1.0

    class App(fabll.Node):
        numeric = Numeric.MakeChild(value=expected_value)

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    assert app.numeric.get().get_value() == expected_value


def test_numeric_create_instance():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    expected_value = 1.0
    numeric = Numeric.create_instance(g=g, tg=tg, value=expected_value)
    assert numeric.get_value() == expected_value


class NumericInterval(fabll.Node):
    _min_identifier: ClassVar[str] = "min"
    _max_identifier: ClassVar[str] = "max"

    @classmethod
    def MakeChild(cls, min: float, max: float) -> fabll._ChildField:  # type: ignore
        if not NumericInterval.validate_bounds(min, max):
            raise ValueError(f"Invalid interval: {min} > {max}")
        out = fabll._ChildField(cls)
        min_numeric = Numeric.MakeChild(min)
        max_numeric = Numeric.MakeChild(max)
        out.add_dependant(min_numeric, identifier=cls._min_identifier)
        out.add_dependant(max_numeric, identifier=cls._max_identifier)
        out.add_dependant(
            fabll.MakeEdge(
                lhs=[out],
                rhs=[min_numeric],
                edge=EdgeComposition.build(child_identifier=cls._min_identifier),
            ),
            identifier=cls._min_identifier,
        )
        out.add_dependant(
            fabll.MakeEdge(
                lhs=[out],
                rhs=[max_numeric],
                edge=EdgeComposition.build(child_identifier=cls._max_identifier),
            ),
            identifier=cls._max_identifier,
        )
        return out

    def get_min(self) -> Numeric:
        numeric_instance = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._min_identifier
        )
        assert numeric_instance is not None
        return Numeric.bind_instance(numeric_instance)

    def get_max(self) -> Numeric:
        numeric_instance = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._max_identifier
        )
        assert numeric_instance is not None
        return Numeric.bind_instance(numeric_instance)

    def get_min_value(self) -> float:
        return self.get_min().get_value()

    def get_max_value(self) -> float:
        return self.get_max().get_value()

    @classmethod
    def create_instance(cls, g: graph.GraphView, tg: TypeGraph) -> "NumericInterval":
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
        self, g: graph.GraphView, tg: TypeGraph, min: float, max: float
    ) -> "NumericInterval":
        if not NumericInterval.validate_bounds(min, max):
            raise ValueError(f"Invalid interval: {min} > {max}")

        #  Add numeric literals to the node min and max fields
        min_numeric = Numeric.create_instance(g=g, tg=tg, value=min)
        max_numeric = Numeric.create_instance(g=g, tg=tg, value=max)
        _ = EdgeComposition.add_child(
            bound_node=self.instance,
            child=min_numeric.instance.node(),
            child_identifier=self._min_identifier,
        )
        _ = EdgeComposition.add_child(
            bound_node=self.instance,
            child=max_numeric.instance.node(),
            child_identifier=self._max_identifier,
        )
        return self

    def is_empty(self) -> bool:
        return False

    def is_unbounded(self) -> bool:
        return self.get_min_value() == -math.inf and self.get_max_value() == math.inf

    def is_finite(self) -> bool:
        return self.get_min_value() != -math.inf and self.get_max_value() != math.inf

    def is_single_element(self) -> bool:
        return self.get_min_value() == self.get_max_value()

    def is_integer(self) -> bool:
        return self.is_single_element() and is_int(self.get_min().get_value())

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
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericInterval"
    ) -> "NumericInterval":
        """
        Arithmetically adds two intervals.
        """
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(
            g,
            tg,
            self.get_min_value() + other.get_min_value(),
            self.get_max_value() + other.get_max_value(),
        )
        return numeric_interval

    def op_negate(self, g: graph.GraphView, tg: TypeGraph) -> "NumericInterval":
        """
        Arithmetically negates a interval.
        """
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(
            g,
            tg,
            -self.get_max_value(),
            -self.get_min_value(),
        )
        return numeric_interval

    def op_subtract(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericInterval"
    ) -> "NumericInterval":
        """
        Arithmetically subtracts a interval from another interval.
        """
        return self.op_add(g=g, tg=tg, other=other.op_negate(g=g, tg=tg))

    def op_multiply(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericInterval"
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
            g,
            tg,
            _min,
            _max,
        )
        return numeric_interval

    def op_invert(self, g: graph.GraphView, tg: TypeGraph) -> "NumericSet":
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
                g=g, tg=tg, values=[(-math.inf, 1 / _min), (1 / _max, math.inf)]
            )
        # Case 3
        elif _min < 0 == _max:
            return numeric_set.setup_from_values(
                g=g, tg=tg, values=[(-math.inf, 1 / _min)]
            )
        # Case 4
        elif _min == 0 < _max:
            return numeric_set.setup_from_values(
                g=g, tg=tg, values=[(1 / _max, math.inf)]
            )
        # Case 5
        else:
            return numeric_set.setup_from_values(
                g=g, tg=tg, values=[(1 / _max, 1 / _min)]
            )

    def op_pow(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericInterval"
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
        numeric_set.setup_from_values(g=g, tg=tg, values=[(min(values), max(values))])
        return numeric_set

    def op_divide(
        self: "NumericInterval",
        g: graph.GraphView,
        tg: TypeGraph,
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
        numeric_set.setup_from_intervals(g=g, tg=tg, intervals=products)

        return numeric_set

    def op_intersect(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericInterval"
    ) -> "NumericSet":
        """
        Set intersects two intervals.
        """
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        min_ = max(self.get_min_value(), other.get_min_value())
        max_ = min(self.get_max_value(), other.get_max_value())
        if min_ <= max_:
            return numeric_set.setup_from_values(g=g, tg=tg, values=[(min_, max_)])
        if min_ == max_:
            return numeric_set.setup_from_values(g=g, tg=tg, values=[(min_, min_)])
        return numeric_set

    def op_difference(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericInterval"
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
            return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=[self])
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
                g=g,
                tg=tg,
                values=[
                    (self.get_min_value(), other.get_min_value()),
                    (other.get_max_value(), self.get_max_value()),
                ],
            )
        # right overlap
        if self.get_min_value() < other.get_min_value():
            return numeric_set.setup_from_values(
                g=g,
                tg=tg,
                values=[(self.get_min_value(), other.get_min_value())],
            )
        # left overlap
        return numeric_set.setup_from_values(
            g=g,
            tg=tg,
            values=[(other.get_max_value(), self.get_max_value())],
        )

    def op_round(
        self, g: graph.GraphView, tg: TypeGraph, ndigits: int = 0
    ) -> "NumericInterval":
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(
            g=g,
            tg=tg,
            min=round(self.get_min_value(), ndigits),
            max=round(self.get_max_value(), ndigits),
        )
        return numeric_interval

    def op_abs(self, g: graph.GraphView, tg: TypeGraph) -> "NumericInterval":
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        # case 1: crosses zero
        if self.get_min_value() < 0 < self.get_max_value():
            numeric_interval.setup(
                g=g,
                tg=tg,
                min=0,
                max=self.get_max_value(),
            )
            return numeric_interval
        # case 2: negative only
        if self.get_min_value() < 0 and self.get_max_value() < 0:
            numeric_interval.setup(
                g=g,
                tg=tg,
                min=-self.get_max_value(),
                max=-self.get_min_value(),
            )
            return numeric_interval
        # case 3: max = 0 and min < 0
        if self.get_min_value() < 0 and self.get_max_value() == 0:
            numeric_interval.setup(
                g=g,
                tg=tg,
                min=0,
                max=-self.get_min_value(),
            )
            return numeric_interval

        assert self.get_min_value() >= 0 and self.get_max_value() >= 0
        return self

    def op_log(self, g: graph.GraphView, tg: TypeGraph) -> "NumericInterval":
        if self.get_min_value() <= 0:
            raise ValueError(f"invalid log of {self}")
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        numeric_interval.setup(
            g=g,
            tg=tg,
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

    def op_sine(self, g: graph.GraphView, tg: TypeGraph) -> "NumericInterval":
        numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
        min, max = NumericInterval.sine_on_interval(
            (float(self.get_min_value()), float(self.get_max_value()))
        )
        numeric_interval.setup(g=g, tg=tg, min=min, max=max)
        return numeric_interval

    def maybe_merge_interval(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericInterval"
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
        if right.get_min_value() in self:
            numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
            numeric_interval.setup(
                g=g,
                tg=tg,
                min=left.get_min_value(),
                max=max(left.get_max_value(), right.get_max_value()),
            )
            return [numeric_interval]
        return [left, right]

    def __contains__(self, item: float) -> bool:
        """
        Set checks if a number is in a interval.
        """
        if not isinstance(item, float):
            return False
        return ge(self.get_max_value(), item) and ge(item, self.get_min_value())

    # FIXME
    def __eq__(self, other: "NumericInterval") -> bool:
        return (
            self.get_min_value() == other.get_min_value()
            and self.get_max_value() == other.get_max_value()
        )

    def __hash__(self) -> int:
        return hash((self.get_min_value(), self.get_max_value()))

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

    def serialize_pset(self) -> dict:
        return {
            "min": None
            if math.isinf(self.get_min_value())
            else float(self.get_min_value()),
            "max": None
            if math.isinf(self.get_max_value())
            else float(self.get_max_value()),
        }


# TODO: Do we need something like this?
# @classmethod
# def deserialize_pset(cls, g: graph.GraphView, tg: TypeGraph, data: dict):
#     min_ = data["min"] if data["min"] is not None else -math.inf
#     max_ = data["max"] if data["max"] is not None else math.inf
#     return cls.create_instance(g=g, tg=tg).setup(g=g, tg=tg, min=min_, max=max_)


def test_numeric_interval_make_child():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    expected_min = 1.0
    expected_max = 2.0

    class App(fabll.Node):
        numeric_interval = NumericInterval.MakeChild(min=expected_min, max=expected_max)

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    assert app.numeric_interval.get().get_min().get_value() == expected_min
    assert app.numeric_interval.get().get_max().get_value() == expected_max


def test_numeric_interval_instance_setup():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    expected_min = 1.0
    expected_max = 2.0

    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    numeric_interval.setup(g=g, tg=tg, min=expected_min, max=expected_max)
    assert numeric_interval.get_min().get_value() == expected_min
    assert numeric_interval.get_max().get_value() == expected_max


def test_numeric_interval_is_empty():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    assert not numeric_interval.is_empty()


def test_numeric_interval_is_unbounded_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -math.inf
    max_value = math.inf
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    assert numeric_interval.is_unbounded()


def test_numeric_interval_is_unbounded_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    assert not numeric_interval.is_unbounded()


def test_numeric_interval_is_finite_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    assert numeric_interval.is_finite()


def test_numeric_interval_is_finite_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -math.inf
    max_value = math.inf
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    assert not numeric_interval.is_finite()


def test_numeric_interval_is_single_element_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 0.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    assert numeric_interval.is_single_element()


def test_numeric_interval_is_single_element_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    assert not numeric_interval.is_single_element()


def test_numeric_interval_is_integer_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 2.0
    max_value = 2.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    assert numeric_interval.is_integer()


def test_numeric_interval_is_integer_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 1.5
    max_value = 1.5
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    assert not numeric_interval.is_integer()


def test_numeric_interval_as_center_rel():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    assert numeric_interval.as_center_rel() == (0.5, 1.0)


def test_numeric_interval_is_subset_of_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    other = NumericInterval.create_instance(g=g, tg=tg)
    other_min_value = -0.5
    other_max_value = 1.5
    other.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    assert numeric_interval.is_subset_of(other=other)


def test_numeric_interval_is_subset_of_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    other = NumericInterval.create_instance(g=g, tg=tg)
    other_min_value = 1.5
    other_max_value = 2.5
    other.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    assert not numeric_interval.is_subset_of(other=other)


def test_numeric_interval_op_add():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    other = NumericInterval.create_instance(g=g, tg=tg)
    other_min_value = 0.5
    other_max_value = 1.5
    other.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = numeric_interval.op_add(g=g, tg=tg, other=other)
    assert result.get_min_value() == 0.5
    assert result.get_max_value() == 2.5


def test_numeric_interval_op_negate():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_negate(g=g, tg=tg)
    assert result.get_min_value() == -1.0
    assert result.get_max_value() == -0.0


def test_numeric_interval_op_subtract():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    other = NumericInterval.create_instance(g=g, tg=tg)
    other_min_value = 0.5
    other_max_value = 1.5
    other.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = numeric_interval.op_subtract(g=g, tg=tg, other=other)
    assert result.get_min_value() == -1.5
    assert result.get_max_value() == 0.5


def test_numeric_interval_op_multiply():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 3.0
    max_value = 4.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    other = NumericInterval.create_instance(g=g, tg=tg)
    other_min_value = 0.5
    other_max_value = 1.5
    other.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = numeric_interval.op_multiply(g=g, tg=tg, other=other)
    assert result.get_min_value() == 1.5
    assert result.get_max_value() == 6.0


def test_numeric_interval_op_multiply_negative_values():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -3.0
    max_value = -2.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    other = NumericInterval.create_instance(g=g, tg=tg)
    other_min_value = 0.5
    other_max_value = 3.5
    other.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = numeric_interval.op_multiply(g=g, tg=tg, other=other)
    assert result.get_min_value() == -10.5
    assert result.get_max_value() == -1.0


def test_numeric_interval_op_multiply_zero_values():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 1.0
    max_value = 2.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    other = NumericInterval.create_instance(g=g, tg=tg)
    other_min_value = 0.0
    other_max_value = 0.0
    other.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = numeric_interval.op_multiply(g=g, tg=tg, other=other)
    assert result.get_min_value() == 0.0
    assert result.get_max_value() == 0.0


def test_numeric_interval_op_invert_case_1():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 0.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_invert(g=g, tg=tg)
    assert result.is_empty()


def test_numeric_interval_op_invert_case_2():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -1.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_invert(g=g, tg=tg)
    result_intervals = result.get_intervals()
    assert len(result_intervals) == 2
    assert result_intervals[0].get_min_value() == -math.inf
    assert result_intervals[0].get_max_value() == -1.0
    assert result_intervals[1].get_min_value() == 1.0
    assert result_intervals[1].get_max_value() == math.inf


def test_numeric_interval_op_invert_case_3():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -1.0
    max_value = 0.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_invert(g=g, tg=tg)
    assert len(result.get_intervals()) == 1
    assert result.get_intervals()[0].get_min_value() == -math.inf
    assert result.get_intervals()[0].get_max_value() == -1.0


def test_numeric_interval_op_invert_case_4():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 1.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_invert(g=g, tg=tg)
    assert len(result.get_intervals()) == 1
    assert result.get_intervals()[0].get_min_value() == 1.0
    assert result.get_intervals()[0].get_max_value() == math.inf


def test_numeric_interval_op_invert_case_5():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 2.0
    max_value = 4.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_invert(g=g, tg=tg)
    assert len(result.get_intervals()) == 1
    assert result.get_intervals()[0].get_min_value() == 0.25
    assert result.get_intervals()[0].get_max_value() == 0.5


def test_numeric_interval_op_pow_positive_base_positive_exponent():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    base = NumericInterval.create_instance(g=g, tg=tg)
    base_min_value = 2.0
    base_max_value = 4.0
    base.setup(g=g, tg=tg, min=base_min_value, max=base_max_value)
    exp = NumericInterval.create_instance(g=g, tg=tg)
    exp_min_value = 1.0
    exp_max_value = 2.0
    exp.setup(g=g, tg=tg, min=exp_min_value, max=exp_max_value)
    result = base.op_pow(g=g, tg=tg, other=exp)
    assert len(result.get_intervals()) == 1
    assert result.get_intervals()[0].get_min_value() == 2.0
    assert result.get_intervals()[0].get_max_value() == 16.0


def test_numeric_interval_op_divide_positive_numerator_positive_denominator():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 1.0
    max_value = 2.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    other = NumericInterval.create_instance(g=g, tg=tg)
    other_min_value = 0.5
    other_max_value = 1.5
    other.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = numeric_interval.op_divide(g=g, tg=tg, other=other)
    assert len(result.get_intervals()) == 1
    assert result.get_intervals()[0].get_min_value() == 1.0 / 1.5
    assert result.get_intervals()[0].get_max_value() == 4.0


def test_numeric_interval_op_intersect_no_overlap():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    self_min_value = 1.0
    self_max_value = 2.0
    self_interval = NumericInterval.create_instance(g=g, tg=tg)
    self_interval.setup(g=g, tg=tg, min=self_min_value, max=self_max_value)
    other_min_value = 3.0
    other_max_value = 4.0
    other_interval = NumericInterval.create_instance(g=g, tg=tg)
    other_interval.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = self_interval.op_intersect(g=g, tg=tg, other=other_interval)
    assert result.is_empty()


def test_numeric_interval_op_intersect_partially_covered():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    self_min_value = 1.0
    self_max_value = 2.0
    self_interval = NumericInterval.create_instance(g=g, tg=tg)
    self_interval.setup(g=g, tg=tg, min=self_min_value, max=self_max_value)
    other_min_value = 1.5
    other_max_value = 2.5
    other_interval = NumericInterval.create_instance(g=g, tg=tg)
    other_interval.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = self_interval.op_intersect(g=g, tg=tg, other=other_interval)
    result_intervals = result.get_intervals()
    assert len(result_intervals) == 1
    assert result_intervals[0].get_min_value() == 1.5
    assert result_intervals[0].get_max_value() == 2.0


def test_numeric_interval_op_difference_no_overlap():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    self_min_value = 1.0
    self_max_value = 2.0
    self_interval = NumericInterval.create_instance(g=g, tg=tg)
    self_interval.setup(g=g, tg=tg, min=self_min_value, max=self_max_value)
    other_min_value = 3.0
    other_max_value = 4.0
    other_interval = NumericInterval.create_instance(g=g, tg=tg)
    other_interval.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
    result_intervals = result.get_intervals()
    assert len(result_intervals) == 1
    assert result_intervals[0].get_min_value() == 1.0
    assert result_intervals[0].get_max_value() == 2.0


def test_numeric_interval_op_difference_fully_covered():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    self_min_value = 1.0
    self_max_value = 5.0
    self_interval = NumericInterval.create_instance(g=g, tg=tg)
    self_interval.setup(g=g, tg=tg, min=self_min_value, max=self_max_value)
    other_min_value = 1.0
    other_max_value = 5.0
    other_interval = NumericInterval.create_instance(g=g, tg=tg)
    other_interval.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
    assert result.is_empty()


def test_numeric_interval_op_difference_inner_overlap():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    self_min_value = 1.0
    self_max_value = 10.0
    self_interval = NumericInterval.create_instance(g=g, tg=tg)
    self_interval.setup(g=g, tg=tg, min=self_min_value, max=self_max_value)
    other_min_value = 2.5
    other_max_value = 6.5
    other_interval = NumericInterval.create_instance(g=g, tg=tg)
    other_interval.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
    result_intervals = result.get_intervals()
    assert len(result_intervals) == 2
    assert result_intervals[0].get_min_value() == 1.0
    assert result_intervals[0].get_max_value() == 2.5
    assert result_intervals[1].get_min_value() == 6.5
    assert result_intervals[1].get_max_value() == 10.0


def test_numeric_interval_op_difference_right_overlap():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    self_min_value = 1.0
    self_max_value = 10.0
    self_interval = NumericInterval.create_instance(g=g, tg=tg)
    self_interval.setup(g=g, tg=tg, min=self_min_value, max=self_max_value)
    other_min_value = 6.5
    other_max_value = 10.0
    other_interval = NumericInterval.create_instance(g=g, tg=tg)
    other_interval.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
    result_intervals = result.get_intervals()
    assert len(result_intervals) == 1
    assert result_intervals[0].get_min_value() == 1.0
    assert result_intervals[0].get_max_value() == 6.5


def test_numeric_interval_op_difference_left_overlap():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    self_min_value = 1.0
    self_max_value = 10.0
    self_interval = NumericInterval.create_instance(g=g, tg=tg)
    self_interval.setup(g=g, tg=tg, min=self_min_value, max=self_max_value)
    other_min_value = 1.0
    other_max_value = 6.5
    other_interval = NumericInterval.create_instance(g=g, tg=tg)
    other_interval.setup(g=g, tg=tg, min=other_min_value, max=other_max_value)
    result = self_interval.op_difference(g=g, tg=tg, other=other_interval)
    result_intervals = result.get_intervals()
    assert len(result_intervals) == 1
    assert result_intervals[0].get_min_value() == 6.5
    assert result_intervals[0].get_max_value() == 10.0


def test_numeric_interval_op_round():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 1.9524377865952437
    max_value = 2.4983529411764706
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_round(g=g, tg=tg, ndigits=3)
    assert result.get_min_value() == 1.952
    assert result.get_max_value() == 2.498


def test_numeric_interval_op_abs():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -1.0
    max_value = 2.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_abs(g=g, tg=tg)
    assert result.get_min_value() == 0.0
    assert result.get_max_value() == 2.0


def test_numeric_interval_op_abs_crosses_zero():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -1.0
    max_value = 2.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_abs(g=g, tg=tg)
    assert result.get_min_value() == 0.0
    assert result.get_max_value() == 2.0


def test_numeric_interval_op_abs_negative_only():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -1.0
    max_value = 0.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_abs(g=g, tg=tg)
    assert result.get_min_value() == 0.0
    assert result.get_max_value() == 1.0


def test_numeric_interval_op_abs_max_zero_min_negative():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -1.0
    max_value = 0.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_abs(g=g, tg=tg)
    assert result.get_min_value() == 0.0
    assert result.get_max_value() == 1.0


def test_numeric_interval_op_log_positive_interval():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 1.0
    max_value = 2.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_log(g=g, tg=tg)
    assert result.get_min_value() == math.log(1.0)
    assert result.get_max_value() == math.log(2.0)


def test_numeric_interval_op_log_negative_value():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = -1.0
    max_value = 2.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    with pytest.raises(ValueError):
        numeric_interval.op_log(g=g, tg=tg)


def test_numeric_interval_op_sine():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 0.5
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_sine(g=g, tg=tg)
    assert result.get_min_value() == 0.0
    assert result.get_max_value() == math.sin(0.5)


def test_numeric_interval_op_sine_wide_interval():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    min_value = 0.0
    max_value = 10.0
    numeric_interval.setup(g=g, tg=tg, min=min_value, max=max_value)
    result = numeric_interval.op_sine(g=g, tg=tg)
    assert result.get_min_value() == -1.0
    assert result.get_max_value() == 1.0


def test_numeric_set_eq_numeric_set():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert numeric_set_1 == numeric_set_2


class NumericSet(fabll.Node):
    intervals = F.Collections.PointerSet.MakeChild()

    @classmethod
    def MakeChild(  # type: ignore
        cls, g: graph.GraphView, tg: TypeGraph, values: list[tuple[float, float]]
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        sorted_and_merged_values = NumericSet.sort_merge_values(
            g=g, tg=tg, values=values
        )
        _intervals = [
            NumericInterval.MakeChild(min=value[0], max=value[1])
            for value in sorted_and_merged_values
        ]
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
        tg: TypeGraph,
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
        tg: TypeGraph,
        values: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        intervals = []
        for value in values:
            intervals.append(
                NumericInterval.create_instance(g=g, tg=tg).setup(
                    g=g, tg=tg, min=value[0], max=value[1]
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
        if left is not None and target in left:
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

    def setup_from_values(
        self, g: graph.GraphView, tg: TypeGraph, values: list[tuple[float, float]]
    ) -> "NumericSet":
        assert self.is_empty()
        sorted_and_merged_values = NumericSet.sort_merge_values(
            g=g, tg=tg, values=values
        )
        for value in sorted_and_merged_values:
            self.intervals.get().append(
                NumericInterval.create_instance(g=g, tg=tg).setup(
                    g=g, tg=tg, min=value[0], max=value[1]
                )
            )
        return self

    def setup_from_intervals(
        self,
        g: graph.GraphView,
        tg: TypeGraph,
        intervals: list["NumericInterval | NumericSet"],
    ) -> "NumericSet":
        assert self.is_empty()
        sorted_and_merged_intervals = NumericSet.sort_merge_intervals(
            g=g, tg=tg, intervals=intervals
        )
        for interval in sorted_and_merged_intervals:
            self.intervals.get().append(interval)
        return self

    @classmethod
    def create_instance(cls, g: graph.GraphView, tg: TypeGraph) -> "NumericSet":
        return NumericSet.bind_typegraph(tg=tg).create_instance(g=g)

    def is_empty(self) -> bool:
        return len(self.get_intervals()) == 0

    def is_superset_of(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> bool:
        return other == other.op_intersect_intervals(g=g, tg=tg, other=self)

    def is_subset_of(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> bool:
        return other.is_superset_of(g=g, tg=tg, other=self)

    def op_intersect(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericInterval"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_intersect(g=g, tg=tg, other=other))
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def op_intersect_intervals(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
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

        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=result)

    def op_union(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = self.get_intervals() + other.get_intervals()
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=list(intervals))

    def op_difference_interval(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericInterval"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_difference(g=g, tg=tg, other=other))
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def op_difference_intervals(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        # TODO there is probably a more efficient way to do this
        out = self
        for o in other.get_intervals():
            out = out.op_difference_interval(g=g, tg=tg, other=o)
        return out

    def op_symmetric_difference_intervals(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        return self.op_union(g=g, tg=tg, other=other).op_difference_intervals(
            g=g, tg=tg, other=self.op_intersect_intervals(g=g, tg=tg, other=other)
        )

    def op_pow(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)

        self_intervals = self.get_intervals()
        other_intervals = other.get_intervals()

        out = []
        for self_interval in self_intervals:
            for other_interval in other_intervals:
                out.append(self_interval.op_pow(g=g, tg=tg, other=other_interval))

        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=out)

    def op_add(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for self_interval in self.get_intervals():
            for other_interval in other.get_intervals():
                intervals.append(self_interval.op_add(g=g, tg=tg, other=other_interval))
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def op_negate(self, g: graph.GraphView, tg: TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_negate(g=g, tg=tg))
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def op_subtract(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        return self.op_add(g=g, tg=tg, other=other.op_negate(g=g, tg=tg))

    def op_multiply(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for self_interval in self.get_intervals():
            for other_interval in other.get_intervals():
                intervals.append(
                    self_interval.op_multiply(g=g, tg=tg, other=other_interval)
                )
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def op_invert(self, g: graph.GraphView, tg: TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_invert(g=g, tg=tg))
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def op_div_intervals(
        self: "NumericSet",
        g: graph.GraphView,
        tg: TypeGraph,
        other: "NumericSet",
    ) -> "NumericSet":
        return self.op_multiply(g=g, tg=tg, other=other.op_invert(g=g, tg=tg))

    def op_ge_intervals(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "BooleanSet":
        boolean_set = BooleanSet.create_instance(g=g, tg=tg)
        if self.is_empty() or other.is_empty():
            return boolean_set
        if self.get_min_value() >= other.get_max_value():
            return boolean_set.setup(g=g, tg=tg, booleans=[True])
        if self.get_max_value() < other.get_min_value():
            return boolean_set.setup(g=g, tg=tg, booleans=[False])
        return boolean_set.setup(g=g, tg=tg, booleans=[True, False])

    def op_gt_intervals(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "BooleanSet":
        boolean_set = BooleanSet.create_instance(g=g, tg=tg)
        if self.is_empty() or other.is_empty():
            return boolean_set
        if self.get_min_value() > other.get_max_value():
            return boolean_set.setup(g=g, tg=tg, booleans=[True])
        if self.get_max_value() <= other.get_min_value():
            return boolean_set.setup(g=g, tg=tg, booleans=[False])
        return boolean_set.setup(g=g, tg=tg, booleans=[True, False])

    def op_le_intervals(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "BooleanSet":
        boolean_set = BooleanSet.create_instance(g=g, tg=tg)
        if self.is_empty() or other.is_empty():
            return boolean_set
        if self.get_max_value() <= other.get_min_value():
            return boolean_set.setup(g=g, tg=tg, booleans=[True])
        if self.get_min_value() > other.get_max_value():
            return boolean_set.setup(g=g, tg=tg, booleans=[False])
        return boolean_set.setup(g=g, tg=tg, booleans=[True, False])

    def op_lt_intervals(
        self, g: graph.GraphView, tg: TypeGraph, other: "NumericSet"
    ) -> "BooleanSet":
        boolean_set = BooleanSet.create_instance(g=g, tg=tg)
        if self.is_empty() or other.is_empty():
            return boolean_set
        if self.get_max_value() < other.get_min_value():
            return boolean_set.setup(g=g, tg=tg, booleans=[True])
        if self.get_min_value() >= other.get_max_value():
            return boolean_set.setup(g=g, tg=tg, booleans=[False])
        return boolean_set.setup(g=g, tg=tg, booleans=[True, False])

    def op_round(
        self, g: graph.GraphView, tg: TypeGraph, ndigits: int = 0
    ) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_round(g=g, tg=tg, ndigits=ndigits))
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def op_abs(self, g: graph.GraphView, tg: TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_abs(g=g, tg=tg))
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def op_log(self, g: graph.GraphView, tg: TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_log(g=g, tg=tg))
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def op_sin(self, g: graph.GraphView, tg: TypeGraph) -> "NumericSet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg)
        intervals = []
        for interval in self.get_intervals():
            intervals.append(interval.op_sine(g=g, tg=tg))
        return numeric_set.setup_from_intervals(g=g, tg=tg, intervals=intervals)

    def __contains__(self, item: float) -> bool:
        if not isinstance(item, float):
            return False
        for interval in self.get_intervals():
            if item in interval:
                return True
        return False

    # FIXME
    def __eq__(self, value: "NumericSet") -> bool:
        if not isinstance(value, NumericSet):
            return False
        self_intervals = self.get_intervals()
        value_intervals = value.get_intervals()
        if len(self_intervals) != len(value_intervals):
            return False
        for r1, r2 in zip(self_intervals, value_intervals):
            if r1 != r2:
                return False
        return True

    # def __ge__(self, other: "NumericSet") -> BoolSet:
    #     return self.op_ge_intervals(other)

    # def __gt__(self, other: "NumericSet") -> BoolSet:
    #     return self.op_gt_intervals(other)

    # def __le__(self, other: "NumericSet") -> BoolSet:
    #     return self.op_le_intervals(other)

    # def __lt__(self, other: "NumericSet") -> BoolSet:
    #     return self.op_lt_intervals(other)

    def __hash__(self) -> int:
        return hash(tuple(hash(r) for r in self.get_intervals()))

    def __repr__(self) -> str:
        return f"_N_intervals({
            ', '.join(
                f'[{r.get_min_value()}, {r.get_max_value()}]'
                for r in self.get_intervals()
            )
        })"

    def __iter__(self) -> Generator["NumericInterval"]:
        yield from self.get_intervals()

    # # operators
    # Dont think we can do these as we need to pass in the graph and typegraph
    # def __add__(self, other: "NumericSet"):
    #     return self.op_add_intervals(other)

    # def __sub__(self, other: "NumericSet"):
    #     return self.op_subtract_intervals(other)

    # def __neg__(self):
    #     return self.op_negate()

    # def __mul__(self, other: "NumericSet"):
    #     return self.op_mul_intervals(other)

    # def __truediv__(
    #     self: "NumericSet",
    #     other: "NumericSet",
    # ):
    #     return self.op_div_intervals(other)

    # def __and__(
    #     self,
    #     other: "Numeric_Interval_Disjoint | Numeric_Interval",
    # ):
    #     if isinstance(other, Numeric_Interval):
    #         return self.op_intersect_interval(other)
    #     return self.op_intersect_intervals(other)

    # def __or__(self, other: "NumericSet"):
    #     return self.op_union_intervals(other)

    # def __pow__(self, other: "NumericSet"):
    #     return self.op_pow_intervals(other)

    def is_single_element(self) -> bool:
        if self.is_empty():
            return False
        return self.get_min_value() == self.get_max_value()

    def any(self) -> float:
        return self.get_min_value()

    def serialize_pset(self) -> dict:
        return {"intervals": [r.serialize_pset() for r in self.get_intervals()]}

    # TODO: Do we need something like this?
    # @classmethod
    # def deserialize_pset(cls, data: dict):
    #     intervals = [
    #         P_Set.deserialize(r) for r in data["intervals"]
    #             for r in data["intervals"]
    #         ]
    #     )


def test_numeric_set_sort_merge_intervals():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_interval_1 = NumericInterval.create_instance(g=g, tg=tg)
    numeric_interval_1.setup(g=g, tg=tg, min=1.8, max=2.2)
    numeric_interval_2 = NumericInterval.create_instance(g=g, tg=tg)
    numeric_interval_2.setup(g=g, tg=tg, min=1.5, max=1.6)
    numeric_interval_3 = NumericInterval.create_instance(g=g, tg=tg)
    numeric_interval_3.setup(g=g, tg=tg, min=2.0, max=3.0)

    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_intervals(
        g=g,
        tg=tg,
        intervals=[numeric_interval_1, numeric_interval_2, numeric_interval_3],
    )
    intervals = numeric_set.get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == 1.5
    assert intervals[0].get_max_value() == 1.6
    assert intervals[1].get_min_value() == 1.8
    assert intervals[1].get_max_value() == 3.0


def test_numeric_set_make_child():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)

    interval_1_min = 0.0
    interval_1_max = 1.0
    interval_2_min = 1.0
    interval_2_max = 2.0

    class App(fabll.Node):
        numeric_set = NumericSet.MakeChild(
            g=g,
            tg=tg,
            values=[(interval_1_min, interval_1_max), (interval_2_min, interval_2_max)],
        )

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    intervals = app.numeric_set.get().get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == interval_1_min
    assert intervals[0].get_max_value() == interval_1_max
    assert intervals[1].get_min_value() == interval_2_min
    assert intervals[1].get_max_value() == interval_2_max


def test_numeric_set_instance_setup_from_values():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    interval_1_min = 0.0
    interval_1_max = 1.0
    interval_2_min = 1.0
    interval_2_max = 2.0
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(
        g=g,
        tg=tg,
        values=[(interval_1_min, interval_1_max), (interval_2_min, interval_2_max)],
    )
    assert numeric_set.get_intervals()[0].get_min_value() == interval_1_min
    assert numeric_set.get_intervals()[0].get_max_value() == interval_1_max
    assert numeric_set.get_intervals()[1].get_min_value() == interval_2_min
    assert numeric_set.get_intervals()[1].get_max_value() == interval_2_max


def test_numeric_set_instance_setup_from_intervals():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    interval_1 = NumericInterval.create_instance(g=g, tg=tg)
    interval_1.setup(g=g, tg=tg, min=0.0, max=1.0)
    interval_2 = NumericInterval.create_instance(g=g, tg=tg)
    interval_2.setup(g=g, tg=tg, min=1.0, max=2.0)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_intervals(g=g, tg=tg, intervals=[interval_1, interval_2])
    intervals = numeric_set.get_intervals()
    assert len(intervals) == 1
    assert intervals[0].get_min_value() == 0.0
    assert intervals[0].get_max_value() == 2.0


def test_numeric_set_is_empty():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    assert numeric_set.is_empty()
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (1.0, 2.0)])
    assert not numeric_set.is_empty()


def test_numeric_set_is_superset_of_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert numeric_set_1.is_superset_of(g=g, tg=tg, other=numeric_set_2)


def test_numeric_set_is_superset_of_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.5), (2.0, 3.0)])
    assert not numeric_set_1.is_superset_of(g=g, tg=tg, other=numeric_set_2)


def test_numeric_set_is_subset_of_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert numeric_set_1.is_subset_of(g=g, tg=tg, other=numeric_set_2)


def test_numeric_set_is_subset_of_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.5), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert not numeric_set_1.is_subset_of(g=g, tg=tg, other=numeric_set_2)


def test_numeric_set_op_intersect_intervals_partially_covered():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.5, 1.5), (1.7, 3.6)])
    result = numeric_set_1.op_intersect_intervals(g=g, tg=tg, other=numeric_set_2)
    intervals = result.get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == 0.5
    assert intervals[0].get_max_value() == 1.0
    assert intervals[1].get_min_value() == 2.0
    assert intervals[1].get_max_value() == 3.0


def test_numeric_set_op_union_intervals():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.5, 1.5), (1.7, 3.6)])
    result = numeric_set_1.op_union(g=g, tg=tg, other=numeric_set_2)
    intervals = result.get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == 0.0
    assert intervals[0].get_max_value() == 1.5
    assert intervals[1].get_min_value() == 1.7
    assert intervals[1].get_max_value() == 3.6


def test_numeric_set_op_difference_intervals():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_interval = NumericInterval.create_instance(g=g, tg=tg)
    numeric_interval.setup(g=g, tg=tg, min=0.5, max=2.5)
    result = numeric_set.op_difference_interval(g=g, tg=tg, other=numeric_interval)
    intervals = result.get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == 0.0
    assert intervals[0].get_max_value() == 0.5
    assert intervals[1].get_min_value() == 2.5
    assert intervals[1].get_max_value() == 3.0


def test_numeric_set_op_symmetric_difference_intervals():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.5, 1.5), (1.7, 3.6)])
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


def test_numeric_set_op_pow_intervals():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (1.0, 2.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (1.0, 2.0)])
    result = numeric_set_1.op_pow(g=g, tg=tg, other=numeric_set_2)
    intervals = result.get_intervals()
    assert len(intervals) == 1
    assert intervals[0].get_min_value() == 0.0
    assert intervals[0].get_max_value() == 4.0


def test_numeric_set_op_add_intervals():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.5, 1.5), (1.7, 3.6)])
    result = numeric_set_1.op_add(g=g, tg=tg, other=numeric_set_2)
    intervals = result.get_intervals()
    assert len(intervals) == 1
    assert intervals[0].get_min_value() == 0.5
    assert intervals[0].get_max_value() == 6.6


def test_numeric_set_op_negate():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    result = numeric_set.op_negate(g=g, tg=tg)
    intervals = result.get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == -3.0
    assert intervals[0].get_max_value() == -2.0
    assert intervals[1].get_min_value() == -1.0
    assert intervals[1].get_max_value() == 0.0


def test_numeric_set_op_subtract_intervals():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.5, 1.5), (1.7, 3.6)])
    result = numeric_set_1.op_subtract(g=g, tg=tg, other=numeric_set_2)
    intervals = result.get_intervals()
    assert len(intervals) == 1
    assert intervals[0].get_min_value() == -3.6
    assert intervals[0].get_max_value() == 2.5


def test_numeric_set_op_multiply():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.5, 1.5), (1.7, 3.6)])
    result = numeric_set_1.op_multiply(g=g, tg=tg, other=numeric_set_2)
    intervals = result.get_intervals()
    assert len(intervals) == 1
    assert intervals[0].get_min_value() == 0.0
    assert intervals[0].get_max_value() == 10.8


def test_numeric_set_op_invert():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    result = numeric_set.op_invert(g=g, tg=tg)
    intervals = result.get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == 1 / 3
    assert intervals[0].get_max_value() == 1 / 2
    assert intervals[1].get_min_value() == 1
    assert intervals[1].get_max_value() == math.inf


def test_numeric_set_op_div_intervals():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.5, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.5, 1.5), (1.7, 3.6)])
    result = numeric_set_1.op_div_intervals(g=g, tg=tg, other=numeric_set_2)
    intervals = result.get_intervals()
    assert len(intervals) == 1
    assert intervals[0].get_min_value() == 0.5 / 3.6
    assert intervals[0].get_max_value() == 6


def test_numeric_set_op_ge_intervals_empty():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)

    assert numeric_set_1.op_ge_intervals(g=g, tg=tg, other=numeric_set_2).is_empty()


def test_numeric_set_op_ge_intervals_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(3.5, 4.5), (5.0, 6.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert numeric_set_1.op_ge_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [True]


def test_numeric_set_op_ge_intervals_true_equal():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(3.5, 4.5), (5.0, 6.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(1.5, 2.5), (3.0, 3.5)])
    assert numeric_set_1.op_ge_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [True]


def test_numeric_set_op_ge_intervals_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(3.5, 4.5), (5.0, 6.0)])
    assert numeric_set_1.op_ge_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [False]


def test_numeric_set_op_gt_intervals_empty():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    assert numeric_set_1.op_gt_intervals(g=g, tg=tg, other=numeric_set_2).is_empty()


def test_numeric_set_op_gt_intervals_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(3.5, 4.5), (5.0, 6.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert numeric_set_1.op_gt_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [True]


def test_numeric_set_op_gt_intervals_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(3.5, 4.5), (5.0, 6.0)])
    assert numeric_set_1.op_gt_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [False]


def test_numeric_set_op_gt_intervals_true_equal():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(1.5, 2.5), (3.0, 3.5)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(1.5, 2.5), (3.0, 3.5)])
    assert numeric_set_1.op_gt_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [True, False]


def test_numeric_set_op_le_intervals_empty():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    assert numeric_set_1.op_le_intervals(g=g, tg=tg, other=numeric_set_2).is_empty()


def test_numeric_set_op_le_intervals_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(3.5, 4.5), (5.0, 6.0)])
    assert numeric_set_1.op_le_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [True]


def test_numeric_set_op_le_intervals_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(3.5, 4.5), (5.0, 6.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert numeric_set_1.op_le_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [False]


def test_numeric_set_op_lt_intervals_empty():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    assert numeric_set_1.op_lt_intervals(g=g, tg=tg, other=numeric_set_2).is_empty()


def test_numeric_set_op_lt_intervals_true():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(3.5, 4.5), (5.0, 6.0)])
    assert numeric_set_1.op_lt_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [True]


def test_numeric_set_op_lt_intervals_false():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(3.5, 4.5), (5.0, 6.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert numeric_set_1.op_lt_intervals(
        g=g, tg=tg, other=numeric_set_2
    ).get_boolean_values() == [False]


def test_numeric_set_op_round():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(
        g=g, tg=tg, values=[(0.0001, 1.0123456789), (2.4532450, 3.432520)]
    )
    result = numeric_set.op_round(g=g, tg=tg, ndigits=3)
    intervals = result.get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == 0.0
    assert intervals[0].get_max_value() == 1.012
    assert intervals[1].get_min_value() == 2.453
    assert intervals[1].get_max_value() == 3.433


def test_numeric_set_op_abs():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(-10.0, -5.0), (1.0, 3.0)])
    result = numeric_set.op_abs(g=g, tg=tg)
    intervals = result.get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == 1.0
    assert intervals[0].get_max_value() == 3.0
    assert intervals[1].get_min_value() == 5.0
    assert intervals[1].get_max_value() == 10.0


def test_numeric_set_op_log():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.1, 1.0), (2.0, 3.0)])
    result = numeric_set.op_log(g=g, tg=tg)
    intervals = result.get_intervals()
    assert len(intervals) == 2
    assert intervals[0].get_min_value() == math.log(0.1)
    assert intervals[0].get_max_value() == math.log(1.0)
    assert intervals[1].get_min_value() == math.log(2.0)
    assert intervals[1].get_max_value() == math.log(3.0)


def test_numeric_set_op_sin():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    result = numeric_set.op_sin(g=g, tg=tg)
    intervals = result.get_intervals()
    assert len(intervals) == 1
    assert intervals[0].get_min_value() == math.sin(0.0)
    assert intervals[0].get_max_value() == math.sin(2.0)


def test_numeric_set_contains():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert 0.5 in numeric_set
    assert 0.0 in numeric_set
    assert 1.0 in numeric_set
    assert 2.0 in numeric_set
    assert 3.0 in numeric_set
    assert 4.0 not in numeric_set


def test_numeric_set_eq():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_1 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_1.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    numeric_set_2 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_2.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert numeric_set_1 == numeric_set_2
    numeric_set_3 = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_3.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 4.0)])
    assert numeric_set_1 != numeric_set_3


def test_numeric_repr():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert repr(numeric_set) == "_N_intervals([0.0, 1.0], [2.0, 3.0])"


def test_numeric_iter():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])

    for interval in numeric_set:
        assert interval.get_min_value() >= 0.0
        assert interval.get_max_value() <= 3.0


def test_numeric_set_is_single_element():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set_single_element = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_single_element.setup_from_values(g=g, tg=tg, values=[(1.0, 1.0)])
    assert numeric_set_single_element.is_single_element()

    numeric_set_multiple_elements = NumericSet.create_instance(g=g, tg=tg)
    numeric_set_multiple_elements.setup_from_values(
        g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)]
    )
    assert not numeric_set_multiple_elements.is_single_element()


def test_numeric_set_any():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    numeric_set = NumericSet.create_instance(g=g, tg=tg)
    numeric_set.setup_from_values(g=g, tg=tg, values=[(0.0, 1.0), (2.0, 3.0)])
    assert numeric_set.any() == 0.0


# Boolsets


@dataclass(frozen=True)
class BooltAttributes(fabll.NodeAttributes):
    value: bool


class Boolean(fabll.Node[BooltAttributes]):
    Attributes = BooltAttributes

    @classmethod
    def MakeChild(cls, value: bool) -> fabll._ChildField:  # type: ignore
        return fabll._ChildField(cls, attributes=BooltAttributes(value=value))

    @classmethod
    def create_instance(
        cls, g: graph.GraphView, tg: TypeGraph, value: bool
    ) -> "Boolean":
        return Boolean.bind_typegraph(tg).create_instance(
            g=g, attributes=BooltAttributes(value=value)
        )

    def get_value(self) -> bool:
        value = self.instance.node().get_dynamic_attrs().get("value", None)
        if value is None:
            raise ValueError("Boolean literal has no value")
        return bool(value)


def test_boolean_make_child():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)

    class App(fabll.Node):
        boolean = Boolean.MakeChild(value=True)

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    assert app.boolean.get().get_value()


class BooleanSet(fabll.Node):
    booleans = F.Collections.PointerSet.MakeChild()

    @classmethod
    def MakeChild(cls, booleans: list[bool]) -> fabll._ChildField:  # type: ignore
        out = fabll._ChildField(cls)
        booleans_makechilds = [Boolean.MakeChild(value=boolean) for boolean in booleans]
        out.add_dependant(
            *F.Collections.PointerSet.MakeEdges(
                [out, cls.booleans],
                [[boolean_makechild] for boolean_makechild in booleans_makechilds],
            )
        )
        out.add_dependant(*booleans_makechilds, before=True)
        return out

    @classmethod
    def create_instance(cls, g: graph.GraphView, tg: TypeGraph) -> "BooleanSet":
        return BooleanSet.bind_typegraph(tg=tg).create_instance(g=g)

    def setup(  # type: ignore
        self, g: graph.GraphView, tg: TypeGraph, booleans: list[bool]
    ) -> "BooleanSet":
        for boolean in booleans:
            self.booleans.get().append(
                Boolean.create_instance(g=g, tg=tg, value=boolean)
            )
        return self

    def get_booleans(self) -> list[Boolean]:
        return [boolean.cast(Boolean) for boolean in self.booleans.get().as_list()]

    def get_boolean_values(self) -> list[bool]:
        return [
            boolean.cast(Boolean).get_value()
            for boolean in self.booleans.get().as_list()
        ]

    def op_not(self, g: graph.GraphView, tg: TypeGraph) -> "BooleanSet":
        boolean_set = BooleanSet.create_instance(g=g, tg=tg)
        boolean_set.setup(
            g=g, tg=tg, booleans=[not boolean for boolean in self.get_boolean_values()]
        )
        return boolean_set

    def op_and(
        self, g: graph.GraphView, tg: TypeGraph, other: "BooleanSet"
    ) -> "BooleanSet":
        boolean_set = BooleanSet.create_instance(g=g, tg=tg)
        booleans = []
        for boolean in self.get_boolean_values():
            for other_boolean in other.get_boolean_values():
                booleans.append(boolean and other_boolean)
        boolean_set.setup(g=g, tg=tg, booleans=booleans)
        return boolean_set

    def op_or(
        self, g: graph.GraphView, tg: TypeGraph, other: "BooleanSet"
    ) -> "BooleanSet":
        boolean_set = BooleanSet.create_instance(g=g, tg=tg)
        booleans = []
        for boolean in self.get_boolean_values():
            for other_boolean in other.get_boolean_values():
                booleans.append(boolean or other_boolean)
        boolean_set.setup(g=g, tg=tg, booleans=booleans)
        return boolean_set

    def is_empty(self) -> bool:
        return len(self.get_boolean_values()) == 0


def test_boolean_set_make_child():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)

    class App(fabll.Node):
        boolean_set = BooleanSet.MakeChild(booleans=[True, False])

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    assert app.boolean_set.get().get_boolean_values() == [True, False]


def test_boolean_set_create_instance():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    boolean_set = BooleanSet.create_instance(g=g, tg=tg)
    boolean_set.setup(g=g, tg=tg, booleans=[True, False])
    assert boolean_set.get_boolean_values() == [True, False]


def test_boolean_set_op_not():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    boolean_set = BooleanSet.create_instance(g=g, tg=tg)
    boolean_set.setup(g=g, tg=tg, booleans=[True, False])
    result = boolean_set.op_not(g=g, tg=tg)
    assert result.get_boolean_values() == [False, True]


def test_boolean_set_op_and():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    boolean_set_1 = BooleanSet.create_instance(g=g, tg=tg)
    boolean_set_1.setup(g=g, tg=tg, booleans=[True, False])
    boolean_set_2 = BooleanSet.create_instance(g=g, tg=tg)
    boolean_set_2.setup(g=g, tg=tg, booleans=[True, False])
    result = boolean_set_1.op_and(g=g, tg=tg, other=boolean_set_2)
    assert result.get_boolean_values() == [True, False, False, False]


def test_boolean_set_op_or():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    boolean_set_1 = BooleanSet.create_instance(g=g, tg=tg)
    boolean_set_1.setup(g=g, tg=tg, booleans=[True, False])
    boolean_set_2 = BooleanSet.create_instance(g=g, tg=tg)
    boolean_set_2.setup(g=g, tg=tg, booleans=[True, False])
    result = boolean_set_1.op_or(g=g, tg=tg, other=boolean_set_2)
    assert result.get_boolean_values() == [True, True, True, False]


class QuantitySet(fabll.Node):
    _is_literal = fabll.Traits.MakeEdge(F.Literals.is_literal.MakeChild())
    _can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    _numeric_set_identifier: ClassVar[str] = "numeric_set"
    _has_unit_identifier: ClassVar[str] = "has_unit"

    @classmethod
    def MakeChild(  # type: ignore
        cls,
        g: graph.GraphView,
        tg: TypeGraph,
        min: float,
        max: float,
        unit: type[fabll.NodeT],
    ) -> fabll._ChildField:
        if not NumericInterval.validate_bounds(min, max):
            raise ValueError(f"Invalid interval: {min} > {max}")
        out = fabll._ChildField(cls)
        numeric_set = NumericSet.MakeChild(g=g, tg=tg, values=[(min, max)])
        out.add_dependant(numeric_set, identifier=cls._numeric_set_identifier)
        out.add_dependant(
            fabll.MakeEdge(
                [out],
                [numeric_set],
                edge=EdgeComposition.build(
                    child_identifier=cls._numeric_set_identifier
                ),
            ),
            identifier=cls._numeric_set_identifier,
        )
        out.add_dependant(
            fabll.Traits.MakeEdge(F.Units.has_unit.MakeChild(unit), [out]),
            identifier=cls._has_unit_identifier,
        )

        return out

    @classmethod
    def create_instance(cls, g: graph.GraphView, tg: TypeGraph) -> "QuantitySet":
        return cls.bind_typegraph(tg=tg).create_instance(g=g)

    def setup(  # type: ignore
        self,
        g: graph.GraphView,
        tg: TypeGraph,
        numeric_set: NumericSet,
        unit: fabll.Node,
    ) -> "QuantitySet":
        _ = EdgeComposition.add_child(
            bound_node=self.instance,
            child=numeric_set.instance.node(),
            child_identifier=self._numeric_set_identifier,
        )
        has_unit_instance = F.Units.has_unit.bind_typegraph(tg=tg).create_instance(g=g)
        has_unit_instance.setup(g=g, unit=unit)

        _ = fbrk.EdgeTrait.add_trait_instance(
            bound_node=self.instance,
            trait_instance=has_unit_instance.instance.node(),
        )

        return self

    def setup_from_min_max(
        self,
        g: graph.GraphView,
        tg: TypeGraph,
        min: float,
        max: float,
        unit: fabll.Node,
    ) -> "QuantitySet":
        numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
            g=g, tg=tg, values=[(min, max)]
        )
        return self.setup(g=g, tg=tg, numeric_set=numeric_set, unit=unit)

    def get_numeric_set(self) -> NumericSet:
        numeric_set = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._numeric_set_identifier
        )
        assert numeric_set is not None
        return NumericSet.bind_instance(numeric_set)

    def get_is_unit(self) -> "F.Units.is_unit":
        return self.get_trait(F.Units.has_unit).get_is_unit()

    def get_unit_node(self) -> fabll.Node:
        return self.get_trait(F.Units.has_unit).unit.get().deref()

    # def get_unit(self) -> IsUnit:
    # unit = EdgePointer.get_pointed_node_by_identifier(
    #     bound_node=self.instance, identifier=self._unit_identifier
    # )
    # assert unit is not None
    # return IsUnit.bind_instance(unit)

    # @classmethod
    # def unbounded(
    #     cls: type[QuantitySetT], units: Unit
    # ) -> Quantity_Interval_DisjointT:
    #     return cls(Quantity_Interval(units=units))

    def is_empty(self) -> bool:
        return self.get_numeric_set().is_empty()

    def get_min_value(self) -> float:
        if self.is_empty():
            raise ValueError("empty interval cannot have min element")
        return self.get_numeric_set().get_min_value()

    def get_max_value(self) -> float:
        if self.is_empty():
            raise ValueError("empty interval cannot have max element")
        return self.get_numeric_set().get_max_value()

    def get_min_quantity(self, g: graph.GraphView, tg: TypeGraph) -> "QuantitySet":
        min_value = self.get_min_value()
        unit = self.get_trait(F.Units.has_unit).unit.get().deref()
        return QuantitySet.create_instance(g=g, tg=tg).setup_from_min_max(
            g=g, tg=tg, min=min_value, max=min_value, unit=unit
        )

    def get_max_quantity(self, g: graph.GraphView, tg: TypeGraph) -> "QuantitySet":
        max_value = self.get_max_value()
        unit = self.get_trait(F.Units.has_unit).unit.get().deref()
        return QuantitySet.create_instance(g=g, tg=tg).setup_from_min_max(
            g=g, tg=tg, min=max_value, max=max_value, unit=unit
        )

    # def closest_elem(
    #     self, g: graph.GraphView, tg: TypeGraph, target: "QuantitySet"
    # ) -> "QuantitySet":
    #     if not self.get_unit().is_commensurable_with(target.get_unit()):
    #         raise ValueError("incompatible units")
    #     return self.base_to_units(
    #         self._intervals.closest_elem(target.to(self.interval_units).magnitude)
    #     )

    # def is_superset_of(self, other: "Quantity_Interval_Disjoint") -> bool:
    #     if not self.units.is_compatible_with(other.units):
    #         return False
    #     return self._intervals.is_superset_of(
    #         Quantity_Interval_Disjoint.from_value(other)._intervals
    #     )

    # def is_subset_of(self, other: "Quantity_Interval_Disjoint") -> bool:
    #     if not self.units.is_compatible_with(other.units):
    #         return False
    #     return self._intervals.is_subset_of(
    #         Quantity_Interval_Disjoint.from_value(other)._intervals
    #     )

    # def op_intersect_interval(
    #     self, other: "Quantity_Interval"
    # ) -> "Quantity_Interval_Disjoint":
    #     if not self.units.is_compatible_with(other.units):
    #         raise ValueError("incompatible units")
    #     _interval = self._intervals.op_intersect_interval(other._interval)
    #     return Quantity_Interval_Disjoint._from_intervals(_interval, self.units)

    # def op_intersect_intervals(
    #     self, *other: "Quantity_Interval_Disjoint"
    # ) -> "Quantity_Interval_Disjoint":
    #     # TODO make pretty
    #     def single(left, right):
    #         if not left.units.is_compatible_with(right.units):
    #             raise ValueError("incompatible units")
    #         _interval = left._intervals.op_intersect_intervals(right._intervals)
    #         return Quantity_Interval_Disjoint._from_intervals(_interval, left.units)

    #     out = Quantity_Interval_Disjoint(self)

    #     for o in other:
    #         out = single(out, o)

    #     return out

    # def op_union_intervals(
    #     self, other: "Quantity_Interval_Disjoint"
    # ) -> ""QuantitySet"":
    #     if not self.units.is_compatible_with(other.units):
    #         raise ValueError("incompatible units")
    #     _interval = self._intervals.op_union_intervals(other._intervals)
    #     return QuantitySet._from_intervals(_interval, self.units)

    # def op_difference_intervals(
    #     self, other: "QuantitySet"
    # ) -> "QuantitySet":
    #     if not self.units.is_compatible_with(other.units):
    #         raise ValueError("incompatible units")
    #     _interval = self._intervals.op_difference_intervals(other._intervals)
    #     return QuantitySet._from_intervals(_interval, self.units)

    # def op_symmetric_difference_intervals(
    #     self, other: "QuantitySet"
    # ) -> "QuantitySet":
    #     if not self.units.is_compatible_with(other.units):
    #         raise ValueError("incompatible units")
    #   _interval = self._intervals.op_symmetric_difference_intervals(other._intervals)
    #     return QuantitySet._from_intervals(_interval, self.units)

    def convert_to_other_unit(
        self, g: graph.GraphView, tg: TypeGraph, other: "QuantitySet"
    ) -> "QuantitySet":
        if not self.get_is_unit().is_commensurable_with(other.get_is_unit()):
            raise ValueError("incompatible units")
        scale, offset = other.get_is_unit().get_conversion_to(self.get_is_unit())

        # Generate a numeric set for the scale
        scale_numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
            g=g, tg=tg, values=[(scale, scale)]
        )

        # Generate a numeric set for the offset
        offset_numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
            g=g, tg=tg, values=[(offset, offset)]
        )

        # Multiply the other numeric set by the scale
        out_numeric_set = scale_numeric_set.op_multiply(
            g=g, tg=tg, other=other.get_numeric_set()
        )

        # Add the offset to the scaled numeric set
        out_numeric_set = out_numeric_set.op_add(g=g, tg=tg, other=offset_numeric_set)

        # Return the new quantity set
        return QuantitySet.create_instance(g=g, tg=tg).setup(
            g=g, tg=tg, numeric_set=out_numeric_set, unit=self.get_unit_node()
        )

    def op_add(
        self, g: graph.GraphView, tg: TypeGraph, other: "QuantitySet"
    ) -> "QuantitySet":
        other_converted = self.convert_to_other_unit(g=g, tg=tg, other=other)
        out_numeric_set = self.get_numeric_set().op_add(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )
        quantity_set = QuantitySet.create_instance(g=g, tg=tg)
        return quantity_set.setup(
            g=g,
            tg=tg,
            numeric_set=out_numeric_set,
            unit=self.get_unit_node(),
        )

    def op_multiply(
        self, g: graph.GraphView, tg: TypeGraph, other: "QuantitySet"
    ) -> "QuantitySet":
        other_converted = self.convert_to_other_unit(g=g, tg=tg, other=other)
        out_numeric_set = self.get_numeric_set().op_multiply(
            g=g, tg=tg, other=other_converted.get_numeric_set()
        )
        quantity_set = QuantitySet.create_instance(g=g, tg=tg)
        unit = self.get_is_unit().op_multiply(
            g=g, tg=tg, other=other_converted.get_is_unit()
        )
        unit_node = fbrk.EdgeTrait.get_owner_node_of(bound_node=unit.instance)
        assert unit_node is not None
        unit_node = fabll.Node.bind_instance(instance=unit_node)

        return quantity_set.setup(
            g=g,
            tg=tg,
            numeric_set=out_numeric_set,
            unit=unit_node,
        )

    # def op_multiply(
    #     self, g: graph.GraphView, tg: TypeGraph, other: "QuantitySet"
    # ) -> "QuantitySet":
    #     scale, offset = self.get_unit().get_conversion_to(other.get_unit())
    #     scale_numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
    #         g=g, tg=tg, values=[(scale, scale)]
    #     )
    #     offset_numeric_set = NumericSet.create_instance(g=g, tg=tg).setup_from_values(
    #         g=g, tg=tg, values=[(offset, offset)]
    #     )
    #     out_numeric_set = scale_numeric_set.op_multiply(
    #         g=g, tg=tg, other=other.get_numeric_set()
    #     )
    #     out_numeric_set = out_numeric_set.op_add(g=g, tg=tg, other=offset_numeric_set)


# def op_negate(self) -> "QuantitySet":
#     _interval = self._intervals.op_negate()
#     return QuantitySet._from_intervals(_interval, self.units)

# def op_subtract_intervals(
#     self, other: "QuantitySet"
# ) -> "QuantitySet":
#     if not self.units.is_compatible_with(other.units):
#         raise ValueError("incompatible units")
#     _interval = self._intervals.op_subtract_intervals(other._intervals)
#     return QuantitySet._from_intervals(_interval, self.units)

# def op_mul_intervals(
#     self, other: "QuantitySet"
# ) -> "QuantitySet":
#     _interval = self._intervals.op_mul_intervals(other._intervals)
#     return QuantitySet._from_intervals(
#         _interval, cast(Unit, self.units * other.units)
#     )

# def op_invert(self) -> "QuantitySet":
#     _interval = self._intervals.op_invert()
#     return QuantitySet._from_intervals(_interval, 1 / self.units)

# def op_div_intervals(
#     self, other: "QuantitySet"
# ) -> "QuantitySet":
#     _interval = self._intervals.op_div_intervals(other._intervals)
#     return QuantitySet._from_intervals(
#         _interval, cast(Unit, self.units / other.units)
#     )

# def op_pow_intervals(
#     self, other: "QuantitySet"
# ) -> "QuantitySet":
#     if not other.units.is_compatible_with(dimensionless):
#         raise ValueError("exponent must have dimensionless units")
#     if other.min_elem != other.max_elem and not self.units.is_compatible_with(
#         dimensionless
#     ):
#         raise ValueError(
#             "base must have dimensionless units when exponent is interval"
#         )
#     units = self.units**other.min_elem.magnitude
#     _interval = self._intervals.op_pow_intervals(other._intervals)
#     return QuantitySet._from_intervals(_interval, units)

# def op_round(self, ndigits: int = 0) -> "QuantitySet":
#     _interval = self._intervals.op_round(ndigits)
#     return QuantitySet._from_intervals(_interval, self.units)

# def op_abs(self) -> "QuantitySet":
#     _interval = self._intervals.op_abs()
#     return QuantitySet._from_intervals(_interval, self.units)

# def op_log(self) -> "QuantitySet":
#     _interval = self._intervals.op_log()
#     return QuantitySet._from_intervals(_interval, self.units)

# def op_sqrt(self) -> "QuantitySet":
#     return self**0.5

# def op_sin(self) -> "QuantitySet":
#     if not self.units.is_compatible_with(dimensionless):
#         raise ValueError("sin only defined for dimensionless quantities")
#     _interval = self._intervals.op_sin()
#     return QuantitySet._from_intervals(_interval, self.units)

# def op_cos(self) -> "QuantitySet":
#     return (self + quantity(math.pi / 2, self.units)).op_sin()

# def op_floor(self) -> "QuantitySet":
#     return (self - quantity(0.5, self.units)).op_round()

# def op_ceil(self) -> "QuantitySet":
#     return (self + quantity(0.5, self.units)).op_round()

# def op_total_span(self) -> Quantity:
#     """Returns the sum of the spans of all intervals in this disjoint set.
#     For a single interval, this is equivalent to max - min.
#     For multiple intervals, this sums the spans of each disjoint interval."""
#     return quantity(
#         sum(abs(r.max_elem - r.min_elem) for r in self._intervals), self.units
#     )

# def op_deviation_to(
#     self, other: QuantitySetLike, relative: bool = False
# ) -> Quantity:
#     try:
#         other_qty = QuantitySet.from_value(other)
#     except ValueError:
#         return NotImplemented
#     sym_diff = self.op_symmetric_difference_intervals(other_qty)
#     deviation = sym_diff.op_total_span()
#     if relative:
#         deviation /= max(abs(self).max_elem, abs(other_qty).max_elem)
#     return deviation

# def op_is_bit_set(self, other: QuantitySetLike) -> BoolSet:
#     other_qty = QuantitySet.from_value(other)
#     if not self.is_single_element() or not other_qty.is_single_element():
#         return BoolSet(False, True)
#     # TODO more checking
#     return BoolSet((int(self.any()) >> int(other_qty.any())) & 1 == 1)

# def __contains__(self, item: Any) -> bool:
#     if isinstance(item, (float, int, Number)):
#         item = quantity(item)
#     if isinstance(item, Quantity):
#         if not item.units.is_compatible_with(self.units):
#             return False
#         item = item.to(self.interval_units).magnitude
#     if not isinstance(item, float) and not isinstance(item, int):
#         return False
#     return self._intervals.__contains__(item)

# @once
# def __hash__(self) -> int:
#     return hash((self._intervals, self.interval_units))

# @once
# def __repr__(self) -> str:
#     return f"QuantitySet({self})"

# @once
# def __str__(self) -> str:
#     def _format_interval(r: Numeric_Interval) -> str:
#         if r._min == r._max:
#             return f"[{self._format_number(r._min)}]"
#         try:
#             center, rel = r.as_center_rel()
#             if rel < 0.5 and round(rel, 2) == rel:
#                 return f"[{self._format_number(center)} ± {rel * 100:.2f}%]"
#         except ZeroDivisionError:
#             pass

#         return f"[{self._format_number(r._min)}, {self._format_number(r._max)}]"

#     out = ", ".join(_format_interval(r) for r in self._intervals.intervals)

#     return f"({out})"

# def __iter__(self) -> Generator[Quantity_Interval]:
#     for r in self._intervals.intervals:
#         yield Quantity_Interval._from_interval(r, self.units)

# def is_unbounded(self) -> bool:
#     return self._intervals.is_unbounded()

# @override
# def is_finite(self) -> bool:
#     return self._intervals.is_finite()

# # operators
# @staticmethod
# def from_value(other: QuantitySetLike) -> "QuantitySet":
#     if isinstance(other, QuantitySet):
#         return other
#     if isinstance(other, Quantity_Singleton):
#         return Quantity_Set_Discrete(other.get_value())
#     if isinstance(other, Quantity_Interval):
#         return QuantitySet(other)
#     if isinstance(other, Quantity):
#         return Quantity_Set_Discrete(other)
#     if isinstance(other, tuple) and len(other) == 2:
#         return QuantitySet(other)
#     if isinstance(other, NumberLike):
#         return Quantity_Set_Discrete(quantity(other))
#     raise ValueError(f"unsupported type: {type(other)}")

# @staticmethod
# def intersect_all(*obj: QuantitySetLike) -> "QuantitySet":
#     if not obj:
#         return Quantity_Set_Empty()
#     intersected = QuantitySet.from_value(obj[0])
#     for o in obj[1:]:
#         intersected = intersected & QuantitySet.from_value(o)
#     return intersected

# def __eq__(self, value: Any) -> bool:
#     if value is None:
#         return False
#     if not isinstance(value, QuantitySetLikeR):
#         return False
#     value_q = QuantitySet.from_value(value)
#     return self._intervals == value_q._intervals

# def __add__(self, other: QuantitySetLike) -> "QuantitySet":
#     try:
#         other_qty = QuantitySet.from_value(other)
#     except ValueError:
#         return NotImplemented
#     return self.op_add_intervals(other_qty)

# def __radd__(self, other: QuantitySetLike) -> "QuantitySet":
#     return self + other

# def __sub__(self, other: QuantitySetLike) -> "QuantitySet":
#     try:
#         other_qty = QuantitySet.from_value(other)
#     except ValueError:
#         return NotImplemented
#     return self.op_subtract_intervals(other_qty)

# def __rsub__(self, other: QuantitySetLike) -> "QuantitySet":
#     return -self + other

# def __neg__(self) -> "QuantitySet":
#     return self.op_negate()

# def __mul__(self, other: QuantitySetLike) -> "QuantitySet":
#     try:
#         other_qty = QuantitySet.from_value(other)
#     except ValueError:
#         return NotImplemented
#     return self.op_mul_intervals(other_qty)

# def __rmul__(self, other: QuantitySetLike) -> "QuantitySet":
#     return self * other

# def __truediv__(self, other: QuantitySetLike) -> "QuantitySet":
#     try:
#         other_qty = QuantitySet.from_value(other)
#     except ValueError:
#         return NotImplemented
#     return self.op_div_intervals(other_qty)

# def __rtruediv__(self, other: QuantitySetLike) -> "QuantitySet":
#     return self.op_invert() * QuantitySet.from_value(other)

# def __pow__(self, other: QuantitySetLike) -> "QuantitySet":
#     return self.op_pow_intervals(QuantitySet.from_value(other))

# def __and__(self, other: QuantitySetLike) -> "QuantitySet":
#     try:
#         other_qty = QuantitySet.from_value(other)
#     except ValueError:
#         return NotImplemented
#     return self.op_intersect_intervals(other_qty)

# def __rand__(self, other: QuantitySetLike) -> "QuantitySet":
#     return QuantitySet.from_value(other) & self

# def __or__(self, other: QuantitySetLike) -> "QuantitySet":
#     try:
#         other_qty = QuantitySet.from_value(other)
#     except ValueError:
#         return NotImplemented
#     return self.op_union_intervals(other_qty)

# def __ror__(self, other: QuantitySetLike) -> "QuantitySet":
#     return QuantitySet.from_value(other) | self

# def __xor__(self, other: QuantitySetLike) -> "QuantitySet":
#     try:
#         other_qty = QuantitySet.from_value(other)
#     except ValueError:
#         return NotImplemented
#     return self.op_symmetric_difference_intervals(other_qty)

# def __rxor__(self, other: QuantitySetLike) -> "QuantitySet":
#     return QuantitySet.from_value(other) ^ self

# def __ge__(self, other: QuantitySetLike) -> BoolSet:
#     other_q = QuantitySet.from_value(other)
#     if not self.units.is_compatible_with(other_q.units):
#         raise ValueError("incompatible units")
#     return self._intervals >= other_q._intervals

# def __gt__(self, other: QuantitySetLike) -> BoolSet:
#     other_q = QuantitySet.from_value(other)
#     if not self.units.is_compatible_with(other_q.units):
#         raise ValueError("incompatible units")
#     return self._intervals > other_q._intervals

# def __le__(self, other: QuantitySetLike) -> BoolSet:
#     other_q = QuantitySet.from_value(other)
#     if not self.units.is_compatible_with(other_q.units):
#         raise ValueError("incompatible units")
#     return self._intervals <= other_q._intervals

# def __lt__(self, other: QuantitySetLike) -> BoolSet:
#     other_q = QuantitySet.from_value(other)
#     if not self.units.is_compatible_with(other_q.units):
#         raise ValueError("incompatible units")
#     return self._intervals < other_q._intervals

# def __round__(self, ndigits: int = 0) -> "QuantitySet":
#     return self.op_round(ndigits)

# def __abs__(self) -> "QuantitySet":
#     return self.op_abs()

# @once
# def is_single_element(self) -> bool:
#     if self.is_empty():
#         return False
#     return self.min_elem == self.max_elem  # type: ignore #TODO

# @property
# def is_integer(self) -> bool:
#     return all(r.is_integer for r in self._intervals.intervals)

# def as_gapless(self) -> "Quantity_Interval":
#     if self.is_empty():
#         raise ValueError("empty interval cannot be gapless")
#     return Quantity_Interval(self.min_elem, self.max_elem, units=self.units)

# @override
# def any(self) -> Quantity:
#     return self.min_elem

# def serialize_pset(self) -> dict[str, Any]:
#     return {
#         "intervals": self._intervals.serialize(),
#         "unit": str(self.units),
#     }

# @override
# @classmethod
# def deserialize_pset(cls, data: dict):
#     from faebryk.libs.units import P

#     out = cls(units=getattr(P, data["unit"]))
#     out._intervals = P_Set.deserialize(data["intervals"])
#     return out

# def to_dimensionless(self) -> "QuantitySet":
#     return QuantitySet._from_intervals(
#         self._intervals, dimensionless
#     )


def test_quantity_set_make_child():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)

    class App(fabll.Node):
        quantity_set = QuantitySet.MakeChild(
            g=g, tg=tg, min=0.0, max=1.0, unit=F.Units.Meter
        )

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    numeric_set = app.quantity_set.get().get_numeric_set()
    assert numeric_set.get_min_value() == 0.0
    assert numeric_set.get_max_value() == 1.0
    assert not_none(
        app.quantity_set.get()
        .get_is_unit()
        .symbol.get()
        .try_extract_constrained_literal()
    ).get_values() == ["m"]


def test_quantity_set_create_instance():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    quantity_set = QuantitySet.create_instance(g=g, tg=tg)
    meter_instance = F.Units.Meter.bind_typegraph(tg=tg).create_instance(g=g)
    quantity_set.setup_from_min_max(g=g, tg=tg, min=0.0, max=1.0, unit=meter_instance)
    assert quantity_set.get_numeric_set().get_min_value() == 0.0
    assert quantity_set.get_numeric_set().get_max_value() == 1.0
    assert quantity_set.get_is_unit().get_symbols() == ["m"]


def test_quantity_set_get_min_quantity():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    meter_instance = F.Units.Meter.bind_typegraph(tg=tg).create_instance(g=g)
    quantity_set = QuantitySet.create_instance(g=g, tg=tg)
    quantity_set.setup_from_min_max(g=g, tg=tg, min=0.0, max=1.0, unit=meter_instance)
    min_quantity = quantity_set.get_min_quantity(g=g, tg=tg)
    assert min_quantity.get_numeric_set().get_min_value() == 0.0
    assert not_none(
        min_quantity.get_is_unit().symbol.get().try_extract_constrained_literal()
    ).get_values() == ["m"]


def test_quantity_set_get_max_quantity():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    meter_instance = F.Units.Meter.bind_typegraph(tg=tg).create_instance(g=g)
    quantity_set = QuantitySet.create_instance(g=g, tg=tg)
    quantity_set.setup_from_min_max(g=g, tg=tg, min=0.0, max=1.0, unit=meter_instance)
    max_quantity = quantity_set.get_max_quantity(g=g, tg=tg)
    assert max_quantity.get_numeric_set().get_max_value() == 1.0
    assert not_none(
        max_quantity.get_is_unit().symbol.get().try_extract_constrained_literal()
    ).get_values() == ["m"]


def test_quantity_set_op_add_same_unit():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    meter_instance = F.Units.Meter.bind_typegraph(tg=tg).create_instance(g=g)
    quantity_set_1 = QuantitySet.create_instance(g=g, tg=tg)
    quantity_set_1.setup_from_min_max(g=g, tg=tg, min=0.0, max=1.0, unit=meter_instance)
    quantity_set_2 = QuantitySet.create_instance(g=g, tg=tg)
    quantity_set_2.setup_from_min_max(g=g, tg=tg, min=0.0, max=1.0, unit=meter_instance)
    result = quantity_set_1.op_add(g=g, tg=tg, other=quantity_set_2)
    assert result.get_numeric_set().get_min_value() == 0.0
    assert result.get_numeric_set().get_max_value() == 2.0
    assert not_none(
        result.get_is_unit().symbol.get().try_extract_constrained_literal()
    ).get_values() == ["m"]


def test_quantity_set_op_add_different_unit():
    class DegreeFahrenheit(fabll.Node):
        _is_unit = fabll.Traits.MakeEdge(
            F.Units.is_unit.MakeChild(
                ["°F"],
                F.Units.BasisVector(kelvin=1),
                multiplier=5 / 9,
                offset=233.15 + 200 / 9,
            )
        )

    # returns result in the self unit
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    celsius = F.Units.DegreeCelsius.bind_typegraph(tg=tg).create_instance(g=g)
    farenheit = DegreeFahrenheit.bind_typegraph(tg=tg).create_instance(g=g)
    quantity_celsius = QuantitySet.create_instance(g=g, tg=tg)
    quantity_celsius.setup_from_min_max(g=g, tg=tg, min=0.0, max=0.0, unit=celsius)
    quantity_farenheit = QuantitySet.create_instance(g=g, tg=tg)
    quantity_farenheit.setup_from_min_max(g=g, tg=tg, min=0.0, max=0.0, unit=farenheit)
    result = quantity_farenheit.op_add(g=g, tg=tg, other=quantity_celsius)
    result_numeric_set_rounded = result.get_numeric_set().op_round(
        g=g, tg=tg, ndigits=2
    )
    assert result_numeric_set_rounded.get_min_value() == 32
    assert not_none(
        result.get_is_unit().symbol.get().try_extract_constrained_literal()
    ).get_values() == ["°F"]


def test_quantity_set_op_multiply_same_unit():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    meter_instance = F.Units.Meter.bind_typegraph(tg=tg).create_instance(g=g)
    quantity_set_1 = QuantitySet.create_instance(g=g, tg=tg)
    quantity_set_1.setup_from_min_max(g=g, tg=tg, min=2.0, max=4.0, unit=meter_instance)
    quantity_set_2 = QuantitySet.create_instance(g=g, tg=tg)
    quantity_set_2.setup_from_min_max(g=g, tg=tg, min=3.0, max=5.0, unit=meter_instance)
    result = quantity_set_1.op_multiply(g=g, tg=tg, other=quantity_set_2)
    assert result.get_numeric_set().get_min_value() == 6.0
    assert result.get_numeric_set().get_max_value() == 20.0
    result_unit_basis_vector = result.get_is_unit()._extract_basis_vector()
    assert result_unit_basis_vector == F.Units.BasisVector(meter=2)


@dataclass(frozen=True)
class CountAttributes(fabll.NodeAttributes):
    value: int


class Count(fabll.Node[CountAttributes]):
    Attributes = CountAttributes

    @classmethod
    def MakeChild(cls, value: int) -> fabll._ChildField:
        out = fabll._ChildField(cls, attributes=CountAttributes(value=value))
        return out

    @classmethod
    def create_instance(cls, g: graph.GraphView, tg: TypeGraph, value: int) -> "Count":
        return Count.bind_typegraph(tg).create_instance(
            g=g, attributes=CountAttributes(value=value)
        )

    def get_value(self) -> int:
        value = self.instance.node().get_dynamic_attrs().get("value", None)
        if value is None:
            raise ValueError("Count literal has no value")
        return int(value)


def test_count_make_child():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    expected_value = 1

    class App(fabll.Node):
        count = Count.MakeChild(value=expected_value)

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    assert app.count.get().get_value() == expected_value


def test_count_create_instance():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    expected_value = 1.0
    numeric = Numeric.create_instance(g=g, tg=tg, value=expected_value)
    assert numeric.get_value() == expected_value


class Counts(fabll.Node):
    """
    A literal representing a set of integer count values.
    Used with CountParameter for constraining integer-valued parameters.
    """

    _is_literal = fabll.Traits.MakeEdge(F.Literals.is_literal.MakeChild())
    _can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    counts = F.Collections.PointerSet.MakeChild()

    @classmethod
    def MakeChild(cls, *values: int) -> fabll._ChildField:
        """
        Create a Counts literal as a child field at type definition time.
        Does not require g or tg - works at type level.
        """
        out = fabll._ChildField(cls)

        _counts = [Count.MakeChild(value=value) for value in values]
        out.add_dependant(
            *F.Collections.PointerSet.MakeEdges(
                [out, cls.counts], [[count] for count in _counts]
            )
        )
        out.add_dependant(*_counts, before=True)

        return out

    @classmethod
    def create_instance(cls, g: graph.GraphView, tg: TypeGraph) -> "Counts":
        return cls.bind_typegraph(tg=tg).create_instance(g=g)

    def setup_from_values(
        self, g: graph.GraphView, tg: TypeGraph, values: list[int]
    ) -> "Counts":
        for value in values:
            self.counts.get().append(Count.create_instance(g=g, tg=tg, value=value))
        return self

    def get_counts(self) -> list[Count]:
        return [count.cast(Count) for count in self.counts.get().as_list()]

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

    def __contains__(self, item: int) -> bool:
        return item in self.get_values()

    def __repr__(self) -> str:
        return f"Counts({self.get_values()})"


def test_count_set_make_child():
    g = graph.GraphView.create()
    tg = TypeGraph.create(g=g)
    expected_values = [1, 2, 3]

    class App(fabll.Node):
        count_set = Counts.MakeChild(*expected_values)

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    assert app.count_set.get().get_values() == expected_values
