# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from enum import Enum
from itertools import pairwise
from typing import Any, Callable, cast

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.utils import (
    Contradiction,
    ContradictionByLiteral,
)
from faebryk.libs.picker.lcsc import PickedPartLCSC
from faebryk.libs.picker.localpick import PickerOption, pick_module_by_params
from faebryk.libs.picker.picker import pick_part_recursively
from faebryk.libs.util import cast_assert, not_none

logger = logging.getLogger(__name__)

_Unit = type[fabll.NodeT]
_Quantity = tuple[float, _Unit]
_Range = tuple[float, float] | tuple[_Quantity, _Quantity]

Range = F.Literals.Numbers

dimensionless = F.Units.Dimensionless


class BoundExpressions:
    """
    A class to bind expressions to a graph and typegraph for concise test code.
    """

    def __init__(
        self, g: graph.GraphView | None = None, tg: fbrk.TypeGraph | None = None
    ):
        self.g = g or graph.GraphView.create()
        self.tg = tg or fbrk.TypeGraph.create(g=self.g)

    def parameter_op(
        self,
        units: "type[fabll.Node] | None" = None,
        within: "F.Literals.Numbers | None" = None,
        domain: "F.NumberDomain | None" = None,
        soft_set: "F.Literals.Numbers | None" = None,
        guess: "F.Literals.Numbers | None" = None,
        tolerance_guess: float | None = None,
        likely_constrained: bool = False,
    ) -> F.Parameters.can_be_operand:
        is_unit_node = None
        if units:
            is_unit_node = (
                units.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .get_trait(F.Units.is_unit)
            )
        else:
            is_unit_node = (
                F.Units.Dimensionless.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .is_unit.get()
            )
        return (
            F.Parameters.NumericParameter.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .setup(
                units=is_unit_node,
                within=within,
                domain=domain,
                soft_set=soft_set,
                guess=guess,
                tolerance_guess=tolerance_guess,
                likely_constrained=likely_constrained,
            )
            .can_be_operand.get()
        )

    def enum_parameter_op(self, enum_type) -> F.Parameters.can_be_operand:
        return (
            F.Parameters.EnumParameter.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .setup(enum=enum_type)
        ).can_be_operand.get()

    def bool_parameter_op(self) -> F.Parameters.can_be_operand:
        return (
            F.Parameters.BooleanParameter.bind_typegraph(tg=self.tg).create_instance(
                g=self.g
            )
        ).can_be_operand.get()

    class U:
        """Short aliases for units from F.Units for concise test code."""

        # Base SI units
        A = F.Units.Ampere
        m = F.Units.Meter
        kg = F.Units.Kilogram
        s = F.Units.Second
        K = F.Units.Kelvin
        mol = F.Units.Mole
        cd = F.Units.Candela

        # Derived SI units (coherent)
        rad = F.Units.Radian
        sr = F.Units.Steradian
        Hz = F.Units.Hertz
        N = F.Units.Newton
        Pa = F.Units.Pascal
        J = F.Units.Joule
        W = F.Units.Watt
        C = F.Units.Coulomb
        V = F.Units.Volt
        Fa = F.Units.Farad  # 'F' conflicts with F import
        Ohm = F.Units.Ohm
        S = F.Units.Siemens
        Wb = F.Units.Weber
        T = F.Units.Tesla
        H = F.Units.Henry
        degC = F.Units.DegreeCelsius
        lm = F.Units.Lumen
        lx = F.Units.Lux
        Bq = F.Units.Becquerel
        Gy = F.Units.Gray
        Sv = F.Units.Sievert
        kat = F.Units.Katal

        # SI patches
        g = F.Units.Gram

        # Dimensionless / scalar
        dl = F.Units.Dimensionless
        pct = F.Units.Percent
        ppm = F.Units.Ppm

        # Angles (non-SI)
        deg = F.Units.Degree
        arcmin = F.Units.ArcMinute
        arcsec = F.Units.ArcSecond

        # Time (non-SI)
        min_ = F.Units.Minute  # 'min' is a Python builtin
        hr = F.Units.Hour
        day = F.Units.Day
        wk = F.Units.Week
        mo = F.Units.Month
        yr = F.Units.Year

        # Volume
        L = F.Units.Liter

        # Angular frequency
        rpm = F.Units.RPM

        # Data units
        bit = F.Units.Bit
        B = F.Units.Byte
        bps = F.Units.BitsPerSecond

        # Compound units
        Ah = F.Units.AmpereHour
        Vps = F.Units.VoltsPerSecond

    def add(
        self, *operands: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Add.c(*operands, g=self.g, tg=self.tg)

    def subtract(
        self,
        minuend: F.Parameters.can_be_operand,
        *subtrahends: F.Parameters.can_be_operand,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Subtract.c(minuend, *subtrahends, g=self.g, tg=self.tg)

    def multiply(
        self, *operands: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Multiply.c(*operands, g=self.g, tg=self.tg)

    def divide(
        self,
        numerator: F.Parameters.can_be_operand,
        *denominators: F.Parameters.can_be_operand,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Divide.c(numerator, *denominators, g=self.g, tg=self.tg)

    def sqrt(self, operand: F.Parameters.can_be_operand) -> F.Parameters.can_be_operand:
        return F.Expressions.Sqrt.c(operand, g=self.g, tg=self.tg)

    def power(
        self,
        base: F.Parameters.can_be_operand,
        exponent: F.Parameters.can_be_operand,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Power.c(base, exponent, g=self.g, tg=self.tg)

    def round(
        self, operand: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Round.c(operand, g=self.g, tg=self.tg)

    def abs(self, operand: F.Parameters.can_be_operand) -> F.Parameters.can_be_operand:
        return F.Expressions.Abs.c(operand, g=self.g, tg=self.tg)

    def sin(self, operand: F.Parameters.can_be_operand) -> F.Parameters.can_be_operand:
        return F.Expressions.Sin.c(operand, g=self.g, tg=self.tg)

    def log(
        self,
        operand: F.Parameters.can_be_operand,
        base: F.Parameters.can_be_operand | None = None,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Log.c(operand, base, g=self.g, tg=self.tg)

    def cos(self, operand: F.Parameters.can_be_operand) -> F.Parameters.can_be_operand:
        return F.Expressions.Cos.c(operand, g=self.g, tg=self.tg)

    def floor(
        self, operand: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Floor.c(operand, g=self.g, tg=self.tg)

    def ceil(self, operand: F.Parameters.can_be_operand) -> F.Parameters.can_be_operand:
        return F.Expressions.Ceil.c(operand, g=self.g, tg=self.tg)

    def min(
        self, *operands: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Min.c(*operands, g=self.g, tg=self.tg)

    def max(
        self, *operands: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Max.c(*operands, g=self.g, tg=self.tg)

    def is_(
        self,
        *operands: F.Parameters.can_be_operand,
        assert_: bool = False,
        tg: fbrk.TypeGraph | None = None,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Is.c(*operands, g=self.g, tg=self.tg, assert_=assert_)

    def is_subset(
        self,
        subset: F.Parameters.can_be_operand,
        superset: F.Parameters.can_be_operand,
        assert_: bool = False,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.IsSubset.c(
            subset, superset, g=self.g, tg=self.tg, assert_=assert_
        )

    def is_superset(
        self,
        superset: F.Parameters.can_be_operand,
        subset: F.Parameters.can_be_operand,
        assert_: bool = False,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.IsSuperset.c(
            superset, subset, g=self.g, tg=self.tg, assert_=assert_
        )

    def greater_or_equal(
        self,
        left: F.Parameters.can_be_operand,
        right: F.Parameters.can_be_operand,
        assert_: bool = False,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.GreaterOrEqual.c(
            left, right, g=self.g, tg=self.tg, assert_=assert_
        )

    def greater_than(
        self,
        left: F.Parameters.can_be_operand,
        right: F.Parameters.can_be_operand,
        assert_: bool = False,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.GreaterThan.c(
            left, right, g=self.g, tg=self.tg, assert_=assert_
        )

    def less_or_equal(
        self,
        left: F.Parameters.can_be_operand,
        right: F.Parameters.can_be_operand,
        assert_: bool = False,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.LessOrEqual.c(
            left, right, g=self.g, tg=self.tg, assert_=assert_
        )

    def less_than(
        self,
        left: F.Parameters.can_be_operand,
        right: F.Parameters.can_be_operand,
        assert_: bool = False,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.LessThan.c(
            left, right, g=self.g, tg=self.tg, assert_=assert_
        )

    def not_(
        self,
        operand: F.Parameters.can_be_operand,
        assert_: bool = False,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Not.c(operand, g=self.g, tg=self.tg, assert_=assert_)

    def and_(
        self, *operands: F.Parameters.can_be_operand, assert_: bool = False
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.And.c(*operands, g=self.g, tg=self.tg, assert_=assert_)

    def or_(
        self, *operands: F.Parameters.can_be_operand, assert_: bool = False
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Or.c(*operands, g=self.g, tg=self.tg, assert_=assert_)

    def implies(
        self,
        antecedent: F.Parameters.can_be_operand,
        consequent: F.Parameters.can_be_operand,
        assert_: bool = False,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Implies.c(
            antecedent, consequent, g=self.g, tg=self.tg, assert_=assert_
        )

    def xor(
        self, *operands: F.Parameters.can_be_operand, assert_: bool = False
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Xor.c(*operands, g=self.g, tg=self.tg, assert_=assert_)

    def intersection(
        self, *operands: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Intersection.c(*operands, g=self.g, tg=self.tg)

    def union(
        self, *operands: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Union.c(*operands, g=self.g, tg=self.tg)

    def symmetric_difference(
        self,
        left: F.Parameters.can_be_operand,
        right: F.Parameters.can_be_operand,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.SymmetricDifference.c(left, right, g=self.g, tg=self.tg)

    def lit_op_single(self, value: float | _Quantity) -> F.Parameters.can_be_operand:
        unit = None
        if isinstance(value, tuple):
            unit: type[fabll.Node] | None = value[1]
            value = value[0]
        else:
            unit = self.U.dl
        is_unit = (
            unit.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .get_trait(F.Units.is_unit)
        )

        return (
            (
                F.Literals.Numbers.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .setup_from_singleton(value=value, unit=is_unit)
            )
            .is_literal.get()
            .as_operand.get()
        )

    def _range_to(self, range: _Range) -> tuple[float, float, type[fabll.Node]]:
        lower = range[0]
        upper = range[1]
        if isinstance(lower, tuple):
            lower_value = lower[0]
            lower_unit = lower[1]
        else:
            lower_value = lower
            lower_unit = self.U.dl
        if isinstance(upper, tuple):
            upper_value = upper[0]
            upper_unit = upper[1]
        else:
            upper_value = upper
            upper_unit = self.U.dl
        assert lower_unit == upper_unit
        return lower_value, upper_value, lower_unit

    def lit_op_range(self, range: _Range) -> F.Parameters.can_be_operand:
        lower_value, upper_value, lower_unit = self._range_to(range)
        is_unit = (
            lower_unit.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .get_trait(F.Units.is_unit)
        )
        return (
            (
                F.Literals.Numbers.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .setup_from_min_max(min=lower_value, max=upper_value, unit=is_unit)
            )
            .is_literal.get()
            .as_operand.get()
        )

    def lit_op_ranges(self, *ranges: _Range) -> F.Parameters.can_be_operand:
        ranges_values = [self._range_to(range) for range in ranges]
        assert len(set(range_value[2] for range_value in ranges_values)) == 1
        is_unit = (
            ranges_values[0][2]
            .bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .get_trait(F.Units.is_unit)
        )
        return (
            F.Literals.Numbers.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .setup(
                numeric_set=F.Literals.NumericSet.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .setup_from_values(
                    values=[
                        (range_value[0], range_value[1])
                        for range_value in ranges_values
                    ]
                ),
                unit=is_unit,
            )
        ).get_trait(F.Parameters.can_be_operand)

    def lit_op_range_from_center_rel(
        self, center: _Quantity, rel: float
    ) -> F.Parameters.can_be_operand:
        is_unit = (
            center[1]
            .bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .get_trait(F.Units.is_unit)
        )
        return (
            (
                F.Literals.Numbers.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .setup_from_center_rel(center=center[0], rel=rel, unit=is_unit)
            )
            .is_literal.get()
            .as_operand.get()
        )

    def lit_bool(self, *values: bool) -> F.Parameters.can_be_operand:
        return (
            (
                F.Literals.Booleans.bind_typegraph(tg=self.tg).create_instance(
                    g=self.g,
                    attributes=F.Literals.Booleans.Attributes(
                        has_true=True in values, has_false=False in values
                    ),
                )
            )
            .is_literal.get()
            .as_operand.get()
        )

    def lit_op_enum(self, *values: Enum) -> F.Parameters.can_be_operand:
        concrete_enum = F.Literals.EnumsFactory(type(values[0]))
        _ = concrete_enum.bind_typegraph(tg=self.tg).get_or_create_type()
        return (
            concrete_enum.bind_typegraph(tg=self.tg)
            .create_instance(
                g=self.g,
            )
            .setup(*values)
            .is_literal.get()
            .as_operand.get()
        )

    def lit_op_discrete_set(
        self, *values: float | _Quantity
    ) -> F.Parameters.can_be_operand:
        return (
            F.Literals.Numbers.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .is_literal.get()
            .as_operand.get()
        )


def _create_letters(
    E: BoundExpressions, n: int, units=fabll.Node
) -> tuple[F.Parameters.ReprContext, list[F.Parameters.is_parameter]]:
    context = F.Parameters.ReprContext()

    class App(fabll.Node):
        params = [F.Parameters.NumericParameter.MakeChild() for _ in range(n)]

    app = App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    params = [p.get().is_parameter.get() for p in app.params]

    return context, params


def test_solve_phase_one():
    solver = DefaultSolver()
    E = BoundExpressions()

    class App(fabll.Node):
        voltage1 = F.Parameters.NumericParameter.MakeChild(unit=E.U.V)
        voltage2 = F.Parameters.NumericParameter.MakeChild(unit=E.U.V)
        voltage3 = F.Parameters.NumericParameter.MakeChild(unit=E.U.V)

    app = App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    voltage1_op = app.voltage1.get().can_be_operand.get()
    voltage2_op = app.voltage2.get().can_be_operand.get()
    voltage3_op = app.voltage3.get().can_be_operand.get()

    E.is_(voltage1_op, voltage2_op, assert_=True)
    E.is_(voltage3_op, E.add(voltage1_op, voltage2_op), assert_=True)

    E.is_(voltage1_op, E.lit_op_range(((1, E.U.V), (3, E.U.V))), assert_=True)
    E.is_(voltage3_op, E.lit_op_range(((2, E.U.V), (6, E.U.V))), assert_=True)

    solver.simplify_symbolically(E.tg, E.g)


# TODO remove slow
@pytest.mark.slow
def test_simplify():
    E = BoundExpressions()

    class App(fabll.Node):
        ops = [F.Parameters.NumericParameter.MakeChild(unit=E.U.dl) for _ in range(10)]

    app_type = App.bind_typegraph(tg=E.tg)
    app = app_type.create_instance(g=E.g)

    # (((((((((((A + B + 1) + C + 2) * D * 3) * E * 4) * F * 5) * G * (A - A)) + H + 7)
    #  + I + 8) + J + 9) - 3) - 4) < 11
    # => (H + I + J + 17) < 11
    app_ops = [p.get().can_be_operand.get() for p in app.ops]
    constants: list[F.Parameters.can_be_operand] = [
        E.lit_op_single((c, E.U.dl)) for c in range(0, 10)
    ]
    E.is_(constants[5], E.subtract(app_ops[0], app_ops[0]), assert_=True)
    E.is_(
        constants[9].get_sibling_trait(F.Parameters.can_be_operand),
        E.lit_op_range(((0, E.U.dl), (1, E.U.dl))),
    )
    acc = app.ops[0].get().can_be_operand.get()
    for i, p in enumerate(app_ops[1:3]):
        E.is_(acc, E.add(acc, p, constants[i]), assert_=True)
    for i, p in enumerate(app_ops[3:7]):
        E.is_(acc, E.multiply(acc, p, constants[i + 3]), assert_=True)
    for i, p in enumerate(app_ops[7:]):
        E.is_(acc, E.add(acc, p, constants[i + 7]), assert_=True)

    E.is_(
        acc,
        E.subtract(acc, E.lit_op_single((3, E.U.dl)), E.lit_op_single((4, E.U.dl))),
        assert_=True,
    )
    # assert isinstance(acc, Subtract)
    assert E.less_or_equal(acc, E.lit_op_single((11, E.U.dl)))

    solver = DefaultSolver()
    solver.simplify_symbolically(E.tg, E.g)
    # TODO actually test something


@pytest.mark.slow
def test_simplify_logic_and():
    E = BoundExpressions()

    class App(fabll.Node):
        p = [F.Parameters.BooleanParameter.MakeChild() for _ in range(4)]

    app_type = App.bind_typegraph(tg=E.tg)
    app = app_type.create_instance(g=E.g)

    anded = E.and_(
        app.p[0].get().can_be_operand.get(),
        E.lit_bool(True),
        assert_=True,
    )

    for p in app.p[1:]:
        E.is_(
            anded,
            E.and_(anded, p.get().can_be_operand.get()),
            assert_=True,
        )
    E.is_(
        anded,
        E.and_(
            anded,
            anded,
        ),
        assert_=True,
    )

    solver = DefaultSolver()
    solver.simplify_symbolically(E.tg, E.g)
    # TODO actually test something


def test_shortcircuit_logic_and():
    E = BoundExpressions()
    p0 = (
        F.Parameters.BooleanParameter.bind_typegraph(E.tg)
        .create_instance(E.g)
        .can_be_operand.get()
    )
    E.and_(p0, E.lit_bool(False), assert_=True)
    solver = DefaultSolver()

    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(E.tg, E.g)


def test_shortcircuit_logic_or():
    E = BoundExpressions()

    class App(fabll.Node):
        p = [F.Parameters.BooleanParameter.MakeChild() for _ in range(4)]

    app = App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    ored = E.or_(app.p[0].get().can_be_operand.get(), assert_=True)
    for p in app.p[1:]:
        E.is_(
            ored,
            E.or_(ored, p.get().can_be_operand.get()),
            assert_=True,
        )
    E.is_(ored, E.or_(ored, ored), assert_=True)

    ored.get_parent_force()[0].get_trait(F.Expressions.is_assertable).assert_()
    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    assert not_none(
        repr_map.try_get_literal(
            ored.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
    ).equals_singleton(True)


def test_inequality_to_set():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.dl)
    E.less_than(p0, E.lit_op_single((2, E.U.dl)), assert_=True)
    E.greater_than(p0, E.lit_op_single((1, E.U.dl)), assert_=True)
    solver = DefaultSolver()
    solver.update_superset_cache(p0)
    assert solver.inspect_get_known_supersets(
        p0.get_sibling_trait(F.Parameters.is_parameter)
    ).equals(
        E.lit_op_range((1, 2)).get_sibling_trait(F.Literals.is_literal),
        g=E.g,
        tg=E.tg,
    )


def test_remove_obvious_tautologies():
    E = BoundExpressions()
    p0, p1, p2 = [E.parameter_op(units=E.U.dl) for _ in range(3)]

    E.is_(p0, E.add(p1, p2), assert_=True)

    E.greater_than(p1, E.lit_op_single((0.0, E.U.dl)), assert_=True)
    E.greater_than(p2, E.lit_op_single((0.0, E.U.dl)), assert_=True)
    E.is_(p2, E.add(p1, p2), assert_=True)
    E.is_(p2, p2, assert_=True)

    solver = DefaultSolver()
    solver.simplify_symbolically(E.tg, E.g)
    # TODO actually test something


def test_subset_of_literal():
    E = BoundExpressions()
    p0, p1, p2 = (
        E.parameter_op(
            units=E.U.dl,
            within=E.lit_op_range((0, i)).get_parent_of_type(F.Literals.Numbers),
        )
        for i in range(3)
    )
    E.is_(p0, p1, assert_=True)
    E.is_(p1, p2, assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(
        fabll.Traits(p0).get_obj_raw(),
        fabll.Traits(p1).get_obj_raw(),
        fabll.Traits(p2).get_obj_raw(),
    )
    # for p in (p0, p1, p2):
    #     assert solver.inspect_get_known_supersets(
    #         p.get_sibling_trait(F.Parameters.is_parameter)
    #     ) == E.lit_op_range((0.0, 0.0))


def test_alias_classes():
    E = BoundExpressions()
    A, B, C, D, H = (E.parameter_op() for _ in range(5))
    E.is_(A, B, assert_=True)
    addition = E.add(C, D)
    E.is_(B, addition, assert_=True)
    addition2 = E.add(D, C)
    E.is_(H, addition2, assert_=True)

    context = F.Parameters.ReprContext()
    for p in (A, B, C, D, H):
        p.get_sibling_trait(F.Parameters.is_parameter_operatable).compact_repr(context)
    solver = DefaultSolver()
    solver.simplify_symbolically(E.tg, E.g, print_context=context)
    # TODO actually test something


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.skip(reason="TODO: Replace with new realworld test")
def test_solve_realworld_biggest():
    pass
    # TODO: Replace with new realworld test

    # class App(fabll.Node):
    #     led = fabll.f_field(F.PoweredLED)(low_side_resistor=True)
    #     mcu: RP2040_ReferenceDesign
    #     usb_power: USB_C_PSU_Vertical

    #     def __preinit__(self):
    #         self.led.led.color.constrain_subset(F.LED.Color.YELLOW)
    #         self.led.led.brightness.constrain_subset(
    #             TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
    #         )

    #         self.usb_power.power_out.connect(self.mcu.usb.usb_if.buspower)
    #         self.mcu.rp2040.gpio[25].line.connect(self.led.power.hv)
    #         self.usb_power.power_out.lv.connect(self.led.power.lv)
    #         self.mcu.rp2040.pinmux.enable(self.mcu.rp2040.gpio[25])

    # app = App()
    # F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    # solver = DefaultSolver()
    # solver.simplify_symbolically(app.get_graph())

    # pick_part_recursively(app, solver)


# TODO remove slow (1pytest -m "not slow" test/core/solver/test_solver.py.5min)
@pytest.mark.slow
def test_inspect_known_superranges():
    E = BoundExpressions()
    p0 = E.parameter_op(
        units=E.U.V,
        within=E.lit_op_range(((1, E.U.V), (10, E.U.V))).get_parent_of_type(
            F.Literals.Numbers
        ),
    ).get_sibling_trait(F.Parameters.can_be_operand)
    E.is_(
        p0,
        E.add(
            E.lit_op_range(((1, E.U.V), (3, E.U.V))),
            E.lit_op_range(((4, E.U.V), (6, E.U.V))),
        ),
        assert_=True,
    )
    solver = DefaultSolver()
    solver.update_superset_cache(p0)
    assert solver.inspect_get_known_supersets(
        p0.get_sibling_trait(F.Parameters.is_parameter)
    ).equals(
        E.lit_op_range(((5, E.U.V), (9, E.U.V))).get_sibling_trait(
            F.Literals.is_literal
        ),
        g=E.g,
        tg=E.tg,
    )


def test_obvious_contradiction_by_literal():
    E = BoundExpressions()
    p0, p1 = [E.parameter_op(units=E.U.V) for _ in range(2)]

    E.is_(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))))
    E.is_(p1, E.lit_op_range(((5, E.U.V), (10, E.U.V))))

    E.is_(p0, p1, assert_=True)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(E.tg, E.g)


def test_subset_is():
    E = BoundExpressions()
    A, B = [E.parameter_op() for _ in range(2)]

    E.is_(A, E.lit_op_range((0, 15)), assert_=True)
    E.is_subset(B, E.lit_op_range((5, 20)), assert_=True)
    E.is_(A, B, assert_=True)

    context = F.Parameters.ReprContext()
    for p in [A, B]:
        p.get_sibling_trait(F.Parameters.is_parameter_operatable).compact_repr(context)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(E.tg, E.g)


def test_subset_is_expr():
    E = BoundExpressions()
    A, B, C = [E.parameter_op() for _ in range(3)]

    context = F.Parameters.ReprContext()
    for p in [A, B, C]:
        p.get_sibling_trait(F.Parameters.is_parameter_operatable).compact_repr(context)

    D = E.add(A, B)
    E.is_(C, E.lit_op_range((0, 15)), assert_=True)

    E.is_subset(D, E.lit_op_range((5, 20)), assert_=True)

    E.is_(C, D, assert_=True)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(E.tg, E.g, print_context=context)


def test_subset_single_alias():
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.V)

    E.is_subset(A, E.lit_op_single((1, E.U.V)), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    g_out = repr_map.G_out
    tg_out = repr_map.tg_out
    assert not_none(
        repr_map.try_get_literal(
            A.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
    ).equals(
        E.lit_op_single((1, E.U.V)).get_sibling_trait(F.Literals.is_literal),
        g=g_out,
        tg=tg_out,
    )


def test_very_simple_alias_class():
    E = BoundExpressions()
    A, B, C = params = (E.parameter_op(units=E.U.V) for _ in range(3))
    E.is_(A, B, assert_=True)
    E.is_(B, C, assert_=True)

    context = F.Parameters.ReprContext()
    for p in params:
        p.get_sibling_trait(F.Parameters.is_parameter_operatable).compact_repr(context)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    assert (
        repr_map.try_get_literal(
            A.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
        == repr_map.try_get_literal(
            B.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
        == repr_map.try_get_literal(
            C.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
    )


def test_domain():
    E = BoundExpressions()
    p0 = E.parameter_op(
        units=E.U.V,
        within=E.lit_op_range(((0, E.U.V), (10, E.U.V))).get_parent_of_type(
            F.Literals.Numbers
        ),
    ).get_sibling_trait(F.Parameters.can_be_operand)
    E.is_(p0, E.lit_op_range(((15, E.U.V), (20, E.U.V))), assert_=True)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(E.tg, E.g)


def test_less_obvious_contradiction_by_literal():
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.V)
    B = E.parameter_op(units=E.U.V)
    C = E.parameter_op(units=E.U.V)

    E.is_(A, E.lit_op_range(((0.0, E.U.V), (10.0, E.U.V))), assert_=True)
    E.is_(B, E.lit_op_range(((5.0, E.U.V), (10.0, E.U.V))), assert_=True)
    E.is_(C, E.add(A, B), assert_=True)
    E.is_(E.lit_op_range(((0.0, E.U.V), (15.0, E.U.V))), C, assert_=True)

    print_context = F.Parameters.ReprContext()
    for p in (A, B, C):
        p.get_sibling_trait(F.Parameters.is_parameter_operatable).compact_repr(
            print_context
        )

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(E.tg, E.g, print_context=print_context)


def test_symmetric_inequality_correlated():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    p1 = E.parameter_op(units=E.U.V)

    E.is_(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)
    E.is_(p1, p0, assert_=True)

    E.greater_or_equal(p0, p1, assert_=True)
    E.greater_or_equal(p1, p0, assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    g_out = repr_map.G_out
    tg_out = repr_map.tg_out
    assert not_none(
        repr_map.try_get_literal(
            p0.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
    ).equals(
        not_none(
            repr_map.try_get_literal(
                p1.get_sibling_trait(F.Parameters.is_parameter_operatable)
            )
        ),
        g=g_out,
        tg=tg_out,
    )
    assert not_none(
        repr_map.try_get_literal(
            p0.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
    ).equals(
        E.lit_op_range(((0, E.U.V), (10, E.U.V))).get_sibling_trait(
            F.Literals.is_literal
        ),
        g=g_out,
        tg=tg_out,
    )


@pytest.mark.parametrize(
    "expr_type, operands, expected",
    [
        (F.Expressions.Add.c, (5, 10), 15),
        # (Subtract, (5, 10), -5),
        # (Multiply, (5, 10), 50),
        # (Divide, (5, 10), 0.5),
    ],
)
def test_simple_literal_folds_arithmetic(
    expr_type: Callable[..., F.Parameters.can_be_operand],
    operands: tuple[float, ...],
    expected: float,
):
    E = BoundExpressions()
    expected_result = expected

    p0 = E.parameter_op(units=E.U.dl)
    p1 = E.parameter_op(units=E.U.dl)

    E.is_(p0, E.lit_op_single(operands[0]), assert_=True)
    E.is_(p1, E.lit_op_single(operands[1]), assert_=True)

    expr = expr_type(p0, p1)
    E.less_or_equal(expr, E.lit_op_single(100.0), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    deduced_subset = repr_map.try_get_literal(
        expr.get_sibling_trait(F.Parameters.is_parameter_operatable), allow_subset=True
    )
    assert not_none(deduced_subset) == expected_result


@pytest.mark.parametrize(
    "expr_type, operands, expected",
    [
        (F.Expressions.Add.c, (5, 10), 15),
        (F.Expressions.Add.c, (-5, 15), 10),
        # (F.Expressions.Add.c, ((0, 10), 5), (5, 15)),
        # (F.Expressions.Add.c, ((0, 10), (-10, 0)), (-10, 10)),
        (F.Expressions.Add.c, (5, 5, 5), 15),
        (F.Expressions.Subtract.c, (5, 10), -5),
        (F.Expressions.Multiply.c, (5, 10), 50),
        (F.Expressions.Divide.c, (5, 10), 0.5),
    ],
)
def test_super_simple_literal_folding(
    expr_type: Callable[[F.Parameters.can_be_operand], F.Parameters.can_be_operand],
    operands: tuple[float, ...],
    expected: float,
):
    E = BoundExpressions()
    operands_op = [E.lit_op_single(o) for o in operands]
    expr = expr_type(*operands_op)
    solver = DefaultSolver()

    E.less_or_equal(expr, E.lit_op_single(100.0), assert_=True)

    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    assert not_none(
        repr_map.try_get_literal(
            expr.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
    ).equals_singleton(expected)


def test_literal_folding_add_multiplicative():
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.dl)
    B = E.parameter_op(units=E.U.dl)

    expr = E.subtract(
        E.add(
            A,
            E.multiply(A, E.lit_op_single(2)),
            E.multiply(A, E.lit_op_single(5)),
            B,
            E.multiply(A, B, E.lit_op_single(2)),
        ),
        B,
    )
    # expect: 8A + 2AB

    E.less_or_equal(expr, E.lit_op_single(100.0), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map

    rep_add = not_none(
        repr_map.map_forward(
            expr.get_sibling_trait(F.Parameters.is_parameter_operatable)
        ).maps_to
    )
    rep_A = repr_map.map_forward(
        A.get_sibling_trait(F.Parameters.is_parameter_operatable)
    ).maps_to
    rep_B = repr_map.map_forward(
        B.get_sibling_trait(F.Parameters.is_parameter_operatable)
    ).maps_to
    assert isinstance(
        fabll.Traits(rep_add).get_obj_raw(),
        F.Expressions.Add,
    )
    context = repr_map.output_print_context
    assert (
        len(
            cast(F.Expressions.Add, fabll.Traits(rep_add).get_obj_raw())
            .operands.get()
            .as_list()
        )
        == 2
    ), f"{rep_add.compact_repr(context)}"
    mul1, mul2 = (
        cast(F.Expressions.Add, fabll.Traits(rep_add).get_obj_raw())
        .operands.get()
        .as_list()
    )

    mulexp1 = fabll.Traits(mul1).get_obj(F.Expressions.Multiply)
    mulexp2 = fabll.Traits(mul2).get_obj(F.Expressions.Multiply)

    # TODO: What is this trying to test?
    assert any(
        set(m.operands.get().as_list()) == [rep_A, 8] for m in (mulexp1, mulexp2)
    )
    assert any(
        set(m.operands.get().as_list()) == [rep_A, rep_B, 2] for m in (mulexp1, mulexp2)
    )


def test_literal_folding_add_multiplicative_2():
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.dl)
    B = E.parameter_op(units=E.U.dl)

    expr = E.add(
        A,
        E.multiply(A, E.lit_op_single(2)),
        E.lit_op_single(10),
        E.multiply(E.lit_op_single(5), A),
        E.lit_op_single(0),
        B,
    )

    E.less_or_equal(expr, E.lit_op_single(100.0), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    rep_add = repr_map.map_forward(
        expr.get_sibling_trait(F.Parameters.is_parameter_operatable)
    ).maps_to
    a_res = repr_map.map_forward(
        A.get_sibling_trait(F.Parameters.is_parameter_operatable)
    ).maps_to
    b_res = repr_map.map_forward(
        B.get_sibling_trait(F.Parameters.is_parameter_operatable)
    ).maps_to
    assert isinstance(rep_add, F.Expressions.Add)
    assert a_res is not None
    a_ops = [
        op
        for op in a_res.get_operations()
        if isinstance(op, F.Expressions.Multiply) and (8) in op.operands.get().as_list()
    ]
    assert len(a_ops) == 1
    mul = next(iter(a_ops))
    assert set(rep_add.operands.get().as_list()) == {
        b_res,
        (10),
        mul,
    }


def test_transitive_subset():
    E = BoundExpressions()

    # TODO: Constrain to real number domain
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(A, B, assert_=True)
    E.is_subset(B, C, assert_=True)

    context = F.Parameters.ReprContext()
    for p in (A, B, C):
        p.get_sibling_trait(F.Parameters.is_parameter_operatable).compact_repr(context)

    E.is_(C, E.lit_op_range((0, 10)), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(
        E.tg, E.g, print_context=context
    ).data.mutation_map
    assert not_none(
        repr_map.try_get_literal(
            A.get_sibling_trait(F.Parameters.is_parameter_operatable), allow_subset=True
        )
    ).equals(
        E.lit_op_range((0, 10)).get_sibling_trait(F.Literals.is_literal), g=E.g, tg=E.tg
    )


def test_nested_additions():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()
    D = E.parameter_op()

    E.is_(A, E.lit_op_single(1), assert_=True)
    E.is_(B, E.lit_op_single(1), assert_=True)
    E.is_(C, E.add(A, B), assert_=True)
    E.is_(D, E.add(C, A), assert_=True)

    solver = DefaultSolver()
    repr_map = not_none(solver.simplify_symbolically(E.tg, E.g).data.mutation_map)

    assert (
        fabll.Traits(
            not_none(
                repr_map.try_get_literal(
                    A.get_sibling_trait(F.Parameters.is_parameter_operatable)
                )
            )
        ).get_obj_raw()
        == fabll.Traits(E.lit_op_single(1)).get_obj_raw()
    )
    assert (
        fabll.Traits(
            not_none(
                repr_map.try_get_literal(
                    B.get_sibling_trait(F.Parameters.is_parameter_operatable)
                )
            )
        ).get_obj_raw()
        == fabll.Traits(E.lit_op_single(1)).get_obj_raw()
    )
    assert (
        fabll.Traits(
            not_none(
                repr_map.try_get_literal(
                    C.get_sibling_trait(F.Parameters.is_parameter_operatable)
                )
            )
        ).get_obj_raw()
        == fabll.Traits(E.lit_op_single(2)).get_obj_raw()
    )
    assert (
        fabll.Traits(
            not_none(
                repr_map.try_get_literal(
                    D.get_sibling_trait(F.Parameters.is_parameter_operatable)
                )
            )
        ).get_obj_raw()
        == fabll.Traits(E.lit_op_single(3)).get_obj_raw()
    )
    assert (
        fabll.Traits(
            not_none(
                repr_map.try_get_literal(
                    D.get_sibling_trait(F.Parameters.is_parameter_operatable)
                )
            )
        ).get_obj_raw()
        == fabll.Traits(E.lit_op_single(3)).get_obj_raw()
    )


def test_combined_add_and_multiply_with_ranges():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_(A, E.lit_op_range_from_center_rel((1, E.U.dl), 0.01), assert_=True)
    E.is_(B, E.lit_op_range_from_center_rel((2, E.U.dl), 0.01), assert_=True)
    E.is_(C, E.add(E.multiply(E.lit_op_single(2), A), B), assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(A, B, C)
    assert solver.inspect_get_known_supersets(
        C.get_sibling_trait(F.Parameters.is_parameter)
    ).equals(
        E.lit_op_range_from_center_rel((4, E.U.dl), 0.01).get_sibling_trait(
            F.Literals.is_literal
        ),
        g=E.g,
        tg=E.tg,
    )


def test_voltage_divider_find_v_out_no_division():
    E = BoundExpressions()
    r_top = E.parameter_op()
    r_bottom = E.parameter_op()
    v_in = E.parameter_op()
    v_out = E.parameter_op()

    E.is_(v_in, E.lit_op_range((9, 10)), assert_=True)
    E.is_(r_top, E.lit_op_range((10, 100)), assert_=True)
    E.is_(r_bottom, E.lit_op_range((10, 100)), assert_=True)
    E.is_(
        v_out,
        E.multiply(
            v_in, r_bottom, E.power(E.add(r_top, r_bottom), E.lit_op_single(-1))
        ),
        assert_=True,
    )
    solver = DefaultSolver()

    # dependency problem prevents finding precise solution of [9/11, 100/11]
    # TODO: automatically rearrange expression to match
    # v_out.alias_is(v_in * (1 / (1 + (r_top / r_bottom))))
    solver.update_superset_cache(v_in, v_out, r_top, r_bottom)
    assert solver.inspect_get_known_supersets(
        v_out.get_sibling_trait(F.Parameters.is_parameter)
    ).equals(
        E.lit_op_range((0.45, 50)).get_sibling_trait(F.Literals.is_literal),
        g=E.g,
        tg=E.tg,
    )


def test_voltage_divider_find_v_out_with_division():
    E = BoundExpressions()
    r_top = E.parameter_op()
    r_bottom = E.parameter_op()
    v_in = E.parameter_op()
    v_out = E.parameter_op()

    E.is_(v_in, E.lit_op_range((9, 10)), assert_=True)
    E.is_(r_top, E.lit_op_range((10, 100)), assert_=True)
    E.is_(r_bottom, E.lit_op_range((10, 100)), assert_=True)
    E.is_(
        v_out,
        E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)),
        assert_=True,
    )

    solver = DefaultSolver()
    solver.update_superset_cache(v_in, v_out, r_top, r_bottom)
    assert solver.inspect_get_known_supersets(
        v_out.get_sibling_trait(F.Parameters.is_parameter)
    ).equals(
        E.lit_op_range((0.45, 50)).get_sibling_trait(F.Literals.is_literal),
        g=E.g,
        tg=E.tg,
    )


def test_voltage_divider_find_v_out_single_variable_occurrences():
    E = BoundExpressions()
    r_top = E.parameter_op()
    r_bottom = E.parameter_op()
    v_in = E.parameter_op()
    v_out = E.parameter_op()

    E.is_(v_in, E.lit_op_range((9, 10)), assert_=True)
    E.is_(r_top, E.lit_op_range((10, 100)), assert_=True)
    E.is_(r_bottom, E.lit_op_range((10, 100)), assert_=True)
    E.is_(
        v_out,
        E.multiply(
            v_in,
            E.divide(
                E.lit_op_single(1), E.add(E.lit_op_single(1), E.divide(r_top, r_bottom))
            ),
        ),
        assert_=True,
    )

    solver = DefaultSolver()
    solver.update_superset_cache(v_in, v_out, r_top, r_bottom)
    assert solver.inspect_get_known_supersets(
        v_out.get_sibling_trait(F.Parameters.is_parameter)
    ).equals(
        E.lit_op_range((9 / 11, 100 / 11)).get_sibling_trait(F.Literals.is_literal),
        g=E.g,
        tg=E.tg,
    )


def test_voltage_divider_find_v_in():
    E = BoundExpressions()
    r_top = E.parameter_op()
    r_bottom = E.parameter_op()
    v_in = E.parameter_op()
    v_out = E.parameter_op()

    E.is_(v_out, E.lit_op_range((9, 10)), assert_=True)
    E.is_(r_top, E.lit_op_range((10, 100)), assert_=True)
    E.is_(r_bottom, E.lit_op_range((10, 100)), assert_=True)
    E.is_(
        v_out,
        E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)),
        assert_=True,
    )

    solver = DefaultSolver()

    # TODO: should find [9.9, 100]
    solver.update_superset_cache(v_in, v_out, r_top, r_bottom)
    assert solver.inspect_get_known_supersets(
        v_in.get_sibling_trait(F.Parameters.is_parameter)
    ).equals(
        E.lit_op_range((1.8, 200)).get_sibling_trait(F.Literals.is_literal),
        g=E.g,
        tg=E.tg,
    )


def test_voltage_divider_find_resistances():
    E = BoundExpressions()
    r_top = E.parameter_op(units=E.U.Ohm)
    r_bottom = E.parameter_op(units=E.U.Ohm)
    v_in = E.parameter_op(units=E.U.V)
    v_out = E.parameter_op(units=E.U.V)
    r_total = E.parameter_op(units=E.U.Ohm)

    E.is_(v_in, E.lit_op_range(((9, E.U.V), (10, E.U.V))))
    E.is_(v_out, E.lit_op_range(((0.9, E.U.V), (1, E.U.V))))
    E.is_(r_total, E.lit_op_range_from_center_rel((100, E.U.Ohm), 0.01), assert_=True)
    E.is_(r_total, E.add(r_top, r_bottom), assert_=True)
    E.is_(
        v_out,
        E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)),
        assert_=True,
    )

    solver = DefaultSolver()
    # FIXME: this test looks funky
    solver.update_superset_cache(v_in, v_out, r_top, r_bottom, r_total)
    assert solver.inspect_get_known_supersets(
        v_out.get_sibling_trait(F.Parameters.is_parameter)
    ).equals(
        E.lit_op_range(((0.9, E.U.V), (1, E.U.V))).get_sibling_trait(
            F.Literals.is_literal
        ),
        g=E.g,
        tg=E.tg,
    )

    # TODO: specify r_top (with tolerance), finish solving to find r_bottom


def test_voltage_divider_find_r_top():
    E = BoundExpressions()
    r_top = E.parameter_op(units=E.U.Ohm)
    r_bottom = E.parameter_op(units=E.U.Ohm)
    v_in = E.parameter_op(units=E.U.V)
    v_out = E.parameter_op(units=E.U.V)

    E.is_(v_in, E.lit_op_range_from_center_rel((10, E.U.V), 0.01))
    E.is_(v_out, E.lit_op_range_from_center_rel((1, E.U.V), 0.01))
    E.is_(r_bottom, E.lit_op_range_from_center_rel((1, E.U.Ohm), 0.01))
    E.is_(v_out, E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)))
    # r_top = (v_in * r_bottom) / v_out - r_bottom

    solver = DefaultSolver()
    solver.update_superset_cache(v_in, v_out, r_top, r_bottom)
    assert solver.inspect_get_known_supersets(
        r_top.get_sibling_trait(F.Parameters.is_parameter)
    ).equals(
        E.lit_op_range(
            ((10 * 0.99**2) / 1.01 - 1.01, (10 * 1.01**2) / 0.99 - 0.99)
        ).get_sibling_trait(F.Literals.is_literal),
        g=E.g,
        tg=E.tg,
    )


def test_voltage_divider_reject_invalid_r_top():
    E = BoundExpressions()
    r_top = E.parameter_op(units=E.U.Ohm)
    r_bottom = E.parameter_op(units=E.U.Ohm)
    v_in = E.parameter_op(units=E.U.V)
    v_out = E.parameter_op(units=E.U.V)

    E.is_(v_in, E.lit_op_range_from_center_rel((10, E.U.V), 0.01))
    E.is_(v_out, E.lit_op_range_from_center_rel((1, E.U.V), 0.01))
    E.is_(v_out, E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)))

    E.is_(r_bottom, E.lit_op_range_from_center_rel((1, E.U.Ohm), 0.01))
    E.is_(r_top, E.lit_op_range_from_center_rel((999, E.U.Ohm), 0.01))

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(E.tg, E.g)


def test_base_unit_switch():
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.Ah)
    E.is_(A, E.lit_op_range(((0.100, E.U.Ah), (0.600, E.U.Ah))))
    E.greater_or_equal(A, E.lit_op_single((0.100, E.U.Ah)), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    assert not_none(
        repr_map.try_get_literal(
            A.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
    ).equals(
        E.lit_op_range(((0.100, E.U.Ah), (0.600, E.U.Ah))).get_sibling_trait(
            F.Literals.is_literal
        ),
        g=E.g,
        tg=E.tg,
    )


@pytest.mark.parametrize("predicate_type", [F.Expressions.Is, F.Expressions.IsSubset])
def test_try_fulfill_super_basic(
    predicate_type: type[F.Expressions.Is] | type[F.Expressions.IsSubset],
):
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    E.is_(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))))

    solver = DefaultSolver()
    pred = predicate_type.c(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))))
    assert solver.try_fulfill(
        pred.get_sibling_trait(F.Expressions.is_assertable), lock=False
    )


def test_congruence_filter():
    E = BoundExpressions()

    A = E.enum_parameter_op(F.LED.Color)
    x = E.is_(A, E.lit_op_enum(F.LED.Color.EMERALD))

    y1 = E.not_(x, assert_=True)
    y2 = E.not_(x, assert_=True)
    assert y1.get_sibling_trait(F.Expressions.is_expression).is_congruent_to(
        y2.get_sibling_trait(F.Expressions.is_expression),
        g=E.g,
        tg=E.tg,
    )

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    assert (
        repr_map.map_forward(
            y1.get_sibling_trait(F.Parameters.is_parameter_operatable)
        ).maps_to
        == repr_map.map_forward(
            y2.get_sibling_trait(F.Parameters.is_parameter_operatable)
        ).maps_to
    )


def test_inspect_enum_simple():
    E = BoundExpressions()
    A = E.enum_parameter_op(F.LED.Color)

    E.is_subset(A, E.lit_op_enum(F.LED.Color.EMERALD), assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(fabll.Traits(A).get_obj_raw())
    assert solver.inspect_get_known_supersets(
        A.get_sibling_trait(F.Parameters.is_parameter)
    ).equals_singleton(F.LED.Color.EMERALD)


def test_regression_enum_contradiction():
    E = BoundExpressions()
    A = E.enum_parameter_op(F.LED.Color)

    E.is_subset(A, E.lit_op_enum(F.LED.Color.BLUE, F.LED.Color.RED), assert_=True)

    solver = DefaultSolver()
    with pytest.raises(Contradiction):
        solver.try_fulfill(
            E.is_(A, E.lit_op_enum(F.LED.Color.EMERALD)).get_sibling_trait(
                F.Expressions.is_assertable
            ),
            lock=False,
        )


def test_inspect_enum_led():
    E = BoundExpressions()
    led = F.LED.bind_typegraph(tg=E.tg).create_instance(g=E.g)

    E.is_subset(
        led.color.get().can_be_operand.get(),
        E.lit_op_enum(F.LED.Color.EMERALD),
        assert_=True,
    )

    solver = DefaultSolver()
    solver.update_superset_cache(led.color.get())
    assert (
        solver.inspect_get_known_supersets(led.color.get().is_parameter.get())
        == F.LED.Color.EMERALD
    )


@pytest.mark.usefixtures("setup_project_config")
def test_simple_pick():
    E = BoundExpressions()
    led = F.LED.bind_typegraph(tg=E.tg).create_instance(g=E.g)

    solver = DefaultSolver()
    pick_module_by_params(
        led,
        solver,
        [
            PickerOption(
                part=PickedPartLCSC(
                    manufacturer="Everlight Elec",
                    partno="19-217/GHC-YR1S2/3T",
                    supplier_partno="C72043",
                ),
                params={
                    "color": E.lit_op_enum(F.LED.Color.EMERALD),
                    "max_brightness": E.lit_op_single((0.285, E.U.cd)),
                    "forward_voltage": E.lit_op_single((3.0, E.U.V)),
                    "max_current": E.lit_op_single((0.1100, E.U.A)),
                },  # type: ignore
                pinmap={
                    "1": led.diode.get().cathode.get(),
                    "2": led.diode.get().anode.get(),
                },
            ),
        ],
    )

    assert led.has_trait(F.has_part_picked)
    assert (
        cast_assert(PickedPartLCSC, led.get_trait(F.has_part_picked).get_part()).lcsc_id
        == "C72043"
    )


@pytest.mark.usefixtures("setup_project_config")
def test_simple_negative_pick():
    E = BoundExpressions()
    led = F.LED.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    E.is_subset(
        led.color.get().can_be_operand.get(),
        E.lit_op_enum(F.LED.Color.RED, F.LED.Color.BLUE),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_module_by_params(
        led,
        solver,
        [
            PickerOption(
                part=PickedPartLCSC(
                    manufacturer="Everlight Elec",
                    partno="19-217/GHC-YR1S2/3T",
                    supplier_partno="C72043",
                ),
                params={
                    "color": E.lit_op_enum(F.LED.Color.EMERALD),
                    "max_brightness": E.lit_op_single((0.285, E.U.cd)),
                    "forward_voltage": E.lit_op_single((3.0, E.U.V)),
                    "max_current": E.lit_op_single((0.1100, E.U.A)),
                },  # type: ignore
                pinmap={
                    "1": led.diode.get().cathode.get(),
                    "2": led.diode.get().anode.get(),
                },
            ),
            PickerOption(
                part=PickedPartLCSC(
                    manufacturer="Everlight Elec",
                    partno="19-217/BHC-ZL1M2RY/3T",
                    supplier_partno="C72041",
                ),
                params={
                    "color": E.lit_op_enum(F.LED.Color.BLUE),
                    "max_brightness": E.lit_op_single((0.0280, E.U.cd)),
                    "forward_voltage": E.lit_op_single((3.0, E.U.V)),
                    "max_current": E.lit_op_single((0.1100, E.U.A)),
                },  # type: ignore
                pinmap={
                    "1": led.diode.get().cathode.get(),
                    "2": led.diode.get().anode.get(),
                },
            ),
        ],
    )

    assert led.has_trait(F.has_part_picked)
    assert (
        cast_assert(PickedPartLCSC, led.get_trait(F.has_part_picked).get_part()).lcsc_id
        == "C72041"
    )


def test_jlcpcb_pick_resistor():
    E = BoundExpressions()
    resistor = F.Resistor.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    E.is_subset(
        resistor.resistance.get().can_be_operand.get(),
        E.lit_op_range(((10, E.U.Ohm), (100, E.U.Ohm))),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(resistor, solver)

    assert resistor.has_trait(F.has_part_picked)
    print(resistor.get_trait(F.has_part_picked).get_part())


@pytest.mark.usefixtures("setup_project_config")
def test_jlcpcb_pick_capacitor():
    E = BoundExpressions()
    capacitor = F.Capacitor.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    E.is_subset(
        capacitor.capacitance.get().can_be_operand.get(),
        E.lit_op_range(((100e-9, E.U.Fa), (1e-6, E.U.Fa))),
        assert_=True,
    )
    E.greater_or_equal(
        capacitor.max_voltage.get().can_be_operand.get(),
        E.lit_op_single((50, E.U.V)),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(capacitor, solver)

    assert capacitor.has_trait(F.has_part_picked)
    print(capacitor.get_trait(F.has_part_picked).get_part())


@pytest.mark.xfail(reason="TODO: add support for leds")
def test_jlcpcb_pick_led():
    E = BoundExpressions()
    led = F.LED.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    E.is_subset(
        led.color.get().can_be_operand.get(),
        E.lit_op_enum(F.LED.Color.EMERALD),
        assert_=True,
    )
    E.greater_or_equal(
        led.diode.get().max_current.get().can_be_operand.get(),
        E.lit_op_single((0.010, E.U.A)),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(led, solver)

    assert led.has_trait(F.has_part_picked)
    print(led.get_trait(F.has_part_picked).get_part())


@pytest.mark.xfail(reason="TODO: swap for test without PoweredLED")
def test_jlcpcb_pick_powered_led_simple():
    # TODO: add support for powered leds
    assert False
    # E = BoundExpressions()
    # led = F.PoweredLED
    # led.led.color.constrain_subset(fabll.EnumSet(F.LED.Color.EMERALD))
    # led.power.voltage.constrain_subset(lit_op_range(((1.8, E.U.V), (5.5, E.U.V))))
    # led.led.forward_voltage.constrain_subset(lit_op_range(((1, E.U.V), (4, E.U.V))))

    # solver = DefaultSolver()
    # children_mods = led.get_children(
    #     direct_only=False, types=fabll.Node, required_trait=fabll.is_module
    # )

    # pick_part_recursively(led, solver)

    # picked_parts = [mod for mod in children_mods if mod.has_trait(F.has_part_picked)]
    # assert len(picked_parts) == 2
    # print([(p, p.get_trait(F.has_part_picked).get_part()) for p in picked_parts])


@pytest.mark.xfail(reason="TODO: swap for test without PoweredLED")
def test_jlcpcb_pick_powered_led_regression():
    # TODO: add support for powered leds
    assert False
    # E = BoundExpressions()
    # led = F.PoweredLED()
    # led.led.color.constrain_subset(F.LED.Color.RED)
    # led.power.voltage.alias_is((3, E.U.V))
    # led.led.brightness.constrain_subset(
    #     TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
    # )

    # solver = DefaultSolver()
    # children_mods = led.get_children(
    #     direct_only=False, types=fabll.Node, required_trait=fabll.is_module
    # )

    # pick_part_recursively(led, solver)

    # picked_parts = [mod for mod in children_mods if mod.has_trait(F.has_part_picked)]
    # assert len(picked_parts) == 2
    # for p in picked_parts:
    #     print(p.get_full_name(types=False), p.get_trait(F.has_part_picked).get_part())
    #     print(p.pretty_params(solver))


def test_simple_parameter_isolation():
    E = BoundExpressions()
    op = F.Expressions.Add

    x_op_y = E.lit_op_range_from_center_rel((3, E.U.dl), 0.01)
    y = E.lit_op_range_from_center_rel((1, E.U.dl), 0.01)
    x_expected = (E.lit_op_range_from_center_rel((2, E.U.dl), 0.02),)

    X = E.parameter_op()
    Y = E.parameter_op()

    add = op.c(X, Y)
    E.is_(add, x_op_y, assert_=True)
    E.is_(Y, y, assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(X, Y)

    assert (
        solver.inspect_get_known_supersets(
            X.get_sibling_trait(F.Parameters.is_parameter)
        )
        == x_expected
    )


def test_abstract_lowpass():
    E = BoundExpressions()
    Li = E.parameter_op(units=E.U.H)
    C = E.parameter_op(units=E.U.Fa)
    fc = E.parameter_op(units=E.U.Hz)

    # formula
    E.is_(
        fc,
        E.divide(
            E.lit_op_single(1),
            E.multiply(E.sqrt(E.multiply(C, Li)), E.lit_op_single(2 * math.pi)),
        ),
        assert_=True,
    )

    # input
    E.is_(Li, E.lit_op_range_from_center_rel((1e-6, E.U.H), 0.01), assert_=True)
    E.is_(fc, E.lit_op_range_from_center_rel((1000, E.U.Hz), 0.01), assert_=True)

    # solve
    solver = DefaultSolver()
    solver.update_superset_cache(Li, C, fc)

    assert solver.inspect_get_known_supersets(
        C.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_range(((6.0 * 158765796, E.U.dl), (6.0 * 410118344, E.U.dl)))


def test_param_isolation():
    E = BoundExpressions()
    X = E.parameter_op()
    Y = E.parameter_op()

    E.is_(E.add(X, Y), E.lit_op_range_from_center_rel((3, E.U.dl), 0.01), assert_=True)
    E.is_(Y, E.lit_op_range_from_center_rel((1, E.U.dl), 0.01), assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(X, Y)

    assert solver.inspect_get_known_supersets(
        X.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_range_from_center_rel((2, E.U.dl), 0.02)


@pytest.mark.parametrize(
    "op",
    [
        F.Expressions.Add.c,
        F.Expressions.Multiply.c,
        F.Expressions.Subtract.c,
        F.Expressions.Divide.c,
    ],
)
def test_extracted_literal_folding(op: Callable[..., F.Parameters.can_be_operand]):
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    lit1 = E.lit_op_range(((0, 10)))
    lit2 = E.lit_op_range(((10, 20)))
    lito = op(lit1, lit2)

    E.is_(A, lit1, assert_=True)
    E.is_(B, lit2, assert_=True)
    E.is_(op(A, B), C, assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(A, B, C)

    assert (
        solver.inspect_get_known_supersets(
            C.get_sibling_trait(F.Parameters.is_parameter)
        )
        == lito
    )


def test_fold_pow():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    lit = E.lit_op_range((5, 6))
    lit_operand = E.lit_op_single(2)

    E.is_(A, lit)
    E.is_(B, E.power(A, lit_operand))

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map

    res = repr_map.try_get_literal(
        B.get_sibling_trait(F.Parameters.is_parameter_operatable)
    )
    assert res == E.power(lit, lit_operand)


def test_graph_split():
    E = BoundExpressions()

    class App(fabll.Node):
        A = F.Parameters.NumericParameter.MakeChild(unit=E.U.dl)
        B = F.Parameters.NumericParameter.MakeChild(unit=E.U.dl)

    app = App.bind_typegraph(tg=E.tg).create_instance(g=E.g)

    Aop = app.A.get().can_be_operand.get()
    Bop = app.B.get().can_be_operand.get()

    C = E.parameter_op()
    D = E.parameter_op()
    E.is_(Aop, C, assert_=True)
    E.is_(Bop, D, assert_=True)

    context = F.Parameters.ReprContext()
    for p in (Aop, Bop, C, D):
        p.get_sibling_trait(F.Parameters.is_parameter_operatable).compact_repr(context)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(
        E.tg, E.g, print_context=context
    ).data.mutation_map

    assert (
        not_none(
            repr_map.map_forward(
                not_none(Aop.get_sibling_trait(F.Parameters.is_parameter_operatable))
            ).maps_to
        ).g
        is not not_none(
            repr_map.map_forward(
                not_none(Bop.get_sibling_trait(F.Parameters.is_parameter_operatable))
            ).maps_to
        ).g
    )


def test_ss_single_into_alias():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_(A, E.lit_op_range((5, 10)), assert_=True)
    E.is_subset(B, E.lit_op_single(5), assert_=True)
    _ = E.add(A, B)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map

    assert (
        repr_map.try_get_literal(
            B.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
        == 5
    )
    assert repr_map.try_get_literal(
        A.get_sibling_trait(F.Parameters.is_parameter_operatable)
    ) == E.lit_op_range((5, 10))


@pytest.mark.parametrize(
    "op, invert",
    [
        (F.Expressions.GreaterOrEqual.c, False),
        (F.Expressions.LessOrEqual.c, True),
        (F.Expressions.Is.c, True),
        (F.Expressions.Is.c, False),
        (F.Expressions.IsSubset.c, True),
        (F.Expressions.IsSubset.c, False),
        (F.Expressions.IsSuperset.c, True),
        (F.Expressions.IsSuperset.c, False),
    ],
)
def test_find_contradiction_by_predicate(op, invert):
    """
    A > B, A is [0, 10], B is [20, 30], A further uncorrelated B
    -> [0,10] > [20, 30]
    """
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_(A, E.lit_op_range((0, 10)), assert_=True)
    E.is_(B, E.lit_op_range((20, 30)), assert_=True)

    if invert:
        op(B, A).get_sibling_trait(F.Expressions.is_assertable).assert_()
    else:
        op(A, B).get_sibling_trait(F.Expressions.is_assertable).assert_()

    solver = DefaultSolver()

    with pytest.raises(Contradiction):
        solver.simplify_symbolically(E.tg, E.g)


def test_find_contradiction_by_gt():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_(A, E.lit_op_range((0, 10)), assert_=True)
    E.is_(B, E.lit_op_range((20, 30)), assert_=True)

    E.greater_than(A, B, assert_=True)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(E.tg, E.g)


def test_can_add_parameters():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_(A, E.lit_op_range((10, 100)), assert_=True)
    E.is_(B, E.lit_op_range((10, 100)), assert_=True)
    C = E.add(A, B)

    solver = DefaultSolver()
    solver.update_superset_cache(A, B, C)

    assert solver.inspect_get_known_supersets(
        C.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_range((20, 200))


def test_ss_estimation_ge():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_subset(A, E.lit_op_range((0, 10)), assert_=True)
    E.greater_or_equal(B, A, assert_=True)

    solver = DefaultSolver()
    solver.simplify_symbolically(E.tg, E.g)


def test_fold_mul_zero():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_(A, E.lit_op_single(0), assert_=True)
    E.is_(B, E.lit_op_range((10, 20)), assert_=True)

    E.is_(C, E.multiply(A, B), assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(A, B, C)

    assert solver.inspect_get_known_supersets(
        C.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_single(0)


def test_fold_or_true():
    E = BoundExpressions()
    A = E.bool_parameter_op()
    B = E.bool_parameter_op()
    C = E.bool_parameter_op()

    E.is_(A, E.lit_bool(True), assert_=True)

    E.is_(E.or_(A, B), C, assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(A, B, C)
    assert solver.inspect_get_known_supersets(
        C.get_sibling_trait(F.Parameters.is_parameter)
    ).equals_singleton(True)


def test_fold_not():
    E = BoundExpressions()
    A = E.bool_parameter_op()
    B = E.bool_parameter_op()

    E.is_(A, E.lit_bool(False), assert_=True)
    E.is_(E.not_(A), B, assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(
        fabll.Traits(A).get_obj_raw(), fabll.Traits(B).get_obj_raw()
    )
    assert solver.inspect_get_known_supersets(
        B.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_bool(True)


def test_fold_ss_transitive():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(C, E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(B, C, assert_=True)
    E.is_subset(A, B, assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(A, B, C)
    assert solver.inspect_get_known_supersets(
        A.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_range((0, 10))


def test_ss_intersect():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_(A, E.lit_op_range((0, 15)), assert_=True)
    E.is_(B, E.lit_op_range((10, 20)), assert_=True)
    E.is_subset(C, A, assert_=True)
    E.is_subset(C, B, assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(A, B, C)
    assert solver.inspect_get_known_supersets(
        C.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_range((10, 15))


@pytest.mark.parametrize(
    "left_factory, right_factory, expected",
    [
        (
            lambda E: [E.lit_op_range((0, 10))],
            lambda E: [E.lit_op_range((0, 10))],
            (True, False),
        ),
        (
            lambda E: [E.lit_op_range((0, 10))],
            lambda E: [E.lit_op_range((10, 20))],
            (False, False),
        ),
        (
            lambda E: [E.add(E.lit_op_range((0, 10)), E.lit_op_range((0, 20)))],
            lambda E: [E.add(E.lit_op_range((0, 10)), E.lit_op_range((0, 20)))],
            (True, False),
        ),
        (
            lambda E: [E.add(E.lit_op_range((0, 10)), E.lit_op_range((0, 20)))],
            lambda E: [E.add(E.lit_op_range((0, 20)), E.lit_op_range((0, 10)))],
            (True, False),
        ),
        (
            lambda E: [E.not_(E.lit_bool(True))],
            lambda E: [E.not_(E.lit_bool(True))],
            (True, True),
        ),
        (
            lambda E: [E.not_(E.not_(E.lit_bool(True)))],
            lambda E: [E.not_(E.not_(E.lit_bool(True)))],
            (True, True),
        ),
        (
            lambda E: [E.multiply(E.lit_op_range((0, 10)), E.lit_op_range((0, 10)))],
            lambda E: [E.multiply(E.lit_op_range((0, 10)), E.lit_op_range((0, 10)))],
            (True, False),
        ),
        (
            lambda E: [
                E.multiply(
                    E.lit_op_range((0, math.inf)),
                    E.lit_op_range((0, math.inf)),
                    E.lit_op_range((0, math.inf)),
                )
            ],
            lambda E: [
                E.multiply(
                    E.lit_op_range((0, math.inf)), E.lit_op_range((0, math.inf))
                ),
            ],
            (False, False),
        ),
        (
            lambda E: [
                E.add(E.lit_op_range((0, math.inf)), E.lit_op_range((0, math.inf)))
            ],
            lambda E: [E.add(E.lit_op_range((0, math.inf)))],
            (False, False),
        ),
    ],
)
def test_congruence_lits(
    left_factory: Callable[[BoundExpressions], list[F.Parameters.can_be_operand]],
    right_factory: Callable[[BoundExpressions], list[F.Parameters.can_be_operand]],
    expected: tuple[bool, bool],
):
    E = BoundExpressions()
    left = left_factory(E)
    right = right_factory(E)
    assert (
        F.Expressions.is_expression.are_pos_congruent(
            left, right, g=E.g, tg=E.tg, allow_uncorrelated=True
        )
        == expected[0]
    )
    assert (
        F.Expressions.is_expression.are_pos_congruent(left, right, g=E.g, tg=E.tg)
        == expected[1]
    )


def test_fold_literals():
    E = BoundExpressions()
    A = E.parameter_op()
    E.is_(A, E.add(E.lit_op_range((0, 10)), E.lit_op_range((0, 10))))

    solver = DefaultSolver()
    solver.update_superset_cache(A)
    assert solver.inspect_get_known_supersets(
        A.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_range((0, 20))


def test_deduce_negative():
    E = BoundExpressions()
    A = E.bool_parameter_op()

    p = E.not_(A)

    solver = DefaultSolver()
    assert solver.try_fulfill(
        p.get_sibling_trait(F.Expressions.is_assertable), lock=False
    )


def test_empty_and():
    E = BoundExpressions()
    solver = DefaultSolver()

    p = E.and_()
    assert solver.try_fulfill(
        p.get_sibling_trait(F.Expressions.is_assertable), lock=False
    )


def test_implication():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_subset(A, E.lit_op_discrete_set(5, 10))

    E.implies(
        E.is_subset(A, E.lit_op_single(5), assert_=True),
        E.is_subset(
            B, E.lit_op_range_from_center_rel((100, E.U.dl), 0.1), assert_=True
        ),
        assert_=True,
    )
    E.implies(
        E.is_subset(A, E.lit_op_single(10), assert_=True),
        E.is_subset(
            B, E.lit_op_range_from_center_rel((500, E.U.dl), 0.1), assert_=True
        ),
        assert_=True,
    )

    E.is_subset(A, E.lit_op_single(10), assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(A, B)
    assert solver.inspect_get_known_supersets(
        B.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_range_from_center_rel((500, E.U.dl), 0.1)


@pytest.mark.parametrize("A_value", [5, 10, 15])
def test_mapping(A_value):
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    X = E.lit_op_range_from_center_rel((100, E.U.dl), 0.1)
    Y = E.lit_op_range_from_center_rel((200, E.U.dl), 0.1)
    Z = E.lit_op_range_from_center_rel((300, E.U.dl), 0.1)

    mapping = {5: X, 10: Y, 15: Z}
    fabll.Traits(A).get_obj(F.Parameters.NumericParameter).constrain_mapping(B, mapping)  # type: ignore

    E.is_subset(A, E.lit_op_single(A_value), assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(A, B)
    assert (
        solver.inspect_get_known_supersets(
            B.get_sibling_trait(F.Parameters.is_parameter)
        )
        == mapping[A_value]
    )


@pytest.mark.parametrize("op", [F.Expressions.Subtract.c, F.Expressions.Add.c])
def test_subtract_zero(op):
    E = BoundExpressions()

    A = E.parameter_op()
    E.is_(A, (op(E.lit_op_single(1), E.lit_op_single(0))))

    solver = DefaultSolver()
    solver.update_superset_cache(A)
    assert solver.inspect_get_known_supersets(
        A.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_single(1)


def test_canonical_subtract_zero():
    E = BoundExpressions()

    A = E.parameter_op()
    E.is_(A, (E.multiply(E.lit_op_single(0), E.lit_op_single(-1))))

    B = E.parameter_op()
    E.is_(
        B,
        (
            E.add(
                E.lit_op_single(1), E.multiply(E.lit_op_single(0), E.lit_op_single(-1))
            )
        ),
        assert_=True,
    )

    solver = DefaultSolver()
    solver.update_superset_cache(A, B)
    assert solver.inspect_get_known_supersets(
        A.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_single(0)
    assert solver.inspect_get_known_supersets(
        B.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_single(1)


def test_nested_fold_scalar():
    E = BoundExpressions()

    A = E.parameter_op()
    E.is_(
        A,
        E.add(E.lit_op_single(1), E.multiply(E.lit_op_single(2), E.lit_op_single(3))),
        assert_=True,
    )

    solver = DefaultSolver()
    solver.update_superset_cache(A)
    assert solver.inspect_get_known_supersets(
        A.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_single(7)


def test_regression_lit_mul_fold_powers():
    E = BoundExpressions()
    A = E.parameter_op()
    E.is_(
        A,
        (
            E.multiply(
                E.power(E.lit_op_single(2), E.lit_op_single(-1)),
                E.power(E.lit_op_single(2), E.lit_op_single(0.5)),
            )
        ),
        assert_=True,
    )

    solver = DefaultSolver()
    solver.update_superset_cache(A)
    assert solver.inspect_get_known_supersets(
        not_none(A.try_get_sibling_trait(F.Parameters.is_parameter))
    ) == E.lit_op_single(2**-0.5)


def test_nested_fold_interval():
    E = BoundExpressions()
    A = E.parameter_op()
    E.is_(
        A,
        (
            E.add(
                E.lit_op_range_from_center_rel((1, E.U.dl), 0.1),
                E.multiply(
                    E.lit_op_range_from_center_rel((2, E.U.dl), 0.1),
                    E.lit_op_range_from_center_rel((3, E.U.dl), 0.1),
                ),
            )
        ),
        assert_=True,
    )

    solver = DefaultSolver()
    solver.update_superset_cache(A)
    assert solver.inspect_get_known_supersets(
        A.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_range((5.76, 8.36))


def test_simplify_non_terminal_manual_test_1():
    """
    Test that non-terminal simplification works
    No assertions, run with
    FBRK_LOG_PICK_SOLVE=y FBRK_SLOG=y and read log
    """
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.V)
    B = E.add(A, A)

    solver = DefaultSolver()
    solver.simplify(E.g, E.tg)
    _ = E.add(B, A)
    E.is_(A, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)

    solver.simplify(E.g, E.tg)

    solver.simplify_symbolically(E.tg, E.g, terminal=True)

    solver.simplify(E.g, E.tg)


# TODO remove slow
@pytest.mark.slow
def test_simplify_non_terminal_manual_test_2():
    """
    Test that non-terminal simplification works
    No assertions, run with
    FBRK_LOG_PICK_SOLVE=y FBRK_SLOG=y and read log
    """
    E = BoundExpressions()
    context, ps = _create_letters(E, 3, units=E.U.V)
    A, B, C = ps

    INCREASE = (20, E.U.dl)
    TOLERANCE = 5
    increase = E.add(
        E.lit_op_range_from_center_rel(INCREASE, TOLERANCE),
        E.lit_op_single((100, E.U.dl)),
    )
    for p1, p2 in pairwise(ps):
        E.is_subset(
            p2.as_operand.get(), E.multiply(p1.as_operand.get(), increase), assert_=True
        )
        E.is_(
            p1.as_operand.get(), E.divide(p2.as_operand.get(), increase), assert_=True
        )

    solver = DefaultSolver()
    solver.simplify_symbolically(E.tg, E.g, terminal=False, print_context=context)

    origin = 1, E.lit_op_range(((9, E.U.V), (11, E.U.V)))
    E.is_(ps[origin[0]].as_operand.get(), (origin[1]), assert_=True)
    solver.simplify(E.g, E.tg)

    solver.update_superset_cache(*ps)
    for i, p in enumerate(ps):
        # _inc = increase ** (i - origin[0])
        _inc = E.lit_op_single(1)
        _i = i - origin[0]
        for _ in range(abs(_i)):
            if _i > 0:
                E.is_(_inc, E.multiply(_inc, increase), assert_=True)
            else:
                E.is_(_inc, E.divide(_inc, increase), assert_=True)

        p_lit = solver.inspect_get_known_supersets(p)
        print(f"{p.as_parameter_operatable.get().compact_repr(context)}, lit:", p_lit)
        print(f"{p_lit.as_operand.get()}, {E.multiply(origin[1], _inc)}")
        assert E.is_subset(p_lit.as_operand.get(), E.multiply(origin[1], _inc))
        E.is_(p.as_operand.get(), p_lit.as_operand.get(), assert_=True)
        solver.simplify(E.g, E.tg)


# XFAIL --------------------------------------------------------------------------------


# extra formula
# C.alias_is(1 / (4 * math.pi**2 * Li * fc**2))
# TODO test with only fc given
@pytest.mark.xfail(reason="Need more powerful expression reordering")  # TODO
def test_abstract_lowpass_ss():
    E = BoundExpressions()
    Li = E.parameter_op(units=E.U.H)
    C = E.parameter_op(units=E.U.Fa)
    fc = E.parameter_op(units=E.U.Hz)

    # formula
    E.is_(
        fc,
        E.divide(
            E.lit_op_single(1),
            E.multiply(E.lit_op_single(2 * math.pi), E.sqrt(E.multiply(C, Li))),
        ),
        assert_=True,
    )

    # input
    Li_const = E.lit_op_range_from_center_rel((1e-6, E.U.H), 0.01)
    fc_const = E.lit_op_range_from_center_rel((1000, E.U.Hz), 0.01)
    E.is_(Li, Li_const, assert_=True)
    E.is_(fc, fc_const, assert_=True)

    # solve
    solver = DefaultSolver()
    solver.simplify_symbolically(E.tg, E.g)

    C_expected = (
        E.divide(
            E.lit_op_single(1),
            E.multiply(
                E.lit_op_single(4),
                E.lit_op_single(math.pi**2),
                Li_const,
                E.power(fc_const, E.lit_op_single(2)),
            ),
        ),
    )

    solver.update_superset_cache(Li, C, fc)
    assert (
        solver.inspect_get_known_supersets(
            C.get_sibling_trait(F.Parameters.is_parameter)
        )
        == C_expected
    )


@pytest.mark.xfail(reason="Need more powerful expression reordering")  # TODO
def test_voltage_divider_find_r_bottom():
    E = BoundExpressions()
    r_top = E.parameter_op(units=E.U.Ohm)
    r_bottom = E.parameter_op(units=E.U.Ohm)
    v_in = E.parameter_op(units=E.U.V)
    v_out = E.parameter_op(units=E.U.V)

    # formula
    E.is_(v_out, E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)))

    # input
    E.is_(v_in, E.lit_op_range_from_center_rel((10, E.U.V), 0.01), assert_=True)
    E.is_(v_out, E.lit_op_range_from_center_rel((1, E.U.V), 0.01), assert_=True)
    E.is_(r_top, E.lit_op_range_from_center_rel((9, E.U.Ohm), 0.01), assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(v_in, v_out, r_top)
    assert solver.inspect_get_known_supersets(
        r_bottom.get_sibling_trait(F.Parameters.is_parameter)
    ) == E.lit_op_range_from_center_rel((1, E.U.Ohm), 0.01)


@pytest.mark.xfail(reason="TODO reenable ge fold")
def test_min_max_single():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    E.is_(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)

    p1 = E.parameter_op(units=E.U.V)
    E.is_(p1, E.max(p0), assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(p0, p1)
    out = solver.inspect_get_known_supersets(
        p1.get_sibling_trait(F.Parameters.is_parameter)
    )
    assert out == E.lit_op_single((10, E.U.V))


@pytest.mark.xfail(reason="TODO")
def test_min_max_multi():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    E.is_(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)
    p3 = E.parameter_op(units=E.U.V)
    E.is_(p3, E.lit_op_range(((4, E.U.V), (15, E.U.V))), assert_=True)

    p1 = E.parameter_op(units=E.U.V)
    E.is_(p1, E.max(p0, p3), assert_=True)

    solver = DefaultSolver()
    solver.update_superset_cache(p0, p1, p3)
    out = solver.inspect_get_known_supersets(
        p1.get_sibling_trait(F.Parameters.is_parameter)
    )
    assert out == E.lit_op_single((15, E.U.V))


@pytest.mark.xfail(
    reason="Behaviour not implemented https://github.com/atopile/atopile/issues/615"
)
def test_symmetric_inequality_uncorrelated():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    p1 = E.parameter_op(units=E.U.V)

    E.is_(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)
    E.is_(p1, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)

    E.greater_or_equal(p0, p1, assert_=True)
    E.less_or_equal(p0, p1, assert_=True)

    # This would only work if p0 is alias p1
    # but we never do implicit alias, because that's very dangerous
    # so this has to throw

    # strategy: if this kind of unequality exists, check if there is an alias
    # and if not, throw

    solver = DefaultSolver()

    with pytest.raises(Contradiction):
        solver.simplify_symbolically(E.tg, E.g)


def test_fold_correlated():
    """
    ```
    A is [5, 10], B is [10, 15]
    B is A + 5
    B - A | [10, 15] - [5, 10] = [0, 10] BUT SHOULD BE 5
    ```

    A and B correlated, thus B - A should do ss not alias
    """
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    op = E.add
    op_inv = E.subtract

    lit1 = E.lit_op_range((5, 10))
    lit_operand = E.lit_op_single(5)
    lit2 = op(lit1, lit_operand)

    E.is_(A, lit1, assert_=True)  # A is [5,10]
    E.is_(B, lit2, assert_=True)  # B is [10,15]
    # correlate A and B
    E.is_(B, op(A, lit_operand), assert_=True)  # B is A + 5
    E.is_(C, op_inv(B, A), assert_=True)  # C is B - A

    context = F.Parameters.ReprContext()
    for p in (A, B, C):
        p.get_sibling_trait(F.Parameters.is_parameter_operatable).compact_repr(context)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(
        E.tg, E.g, print_context=context
    ).data.mutation_map

    is_lit = repr_map.try_get_literal(
        C.get_sibling_trait(F.Parameters.is_parameter_operatable), allow_subset=False
    )
    ss_lit = repr_map.try_get_literal(
        C.get_sibling_trait(F.Parameters.is_parameter_operatable), allow_subset=True
    )
    assert ss_lit is not None

    # Test for ss estimation
    assert E.is_subset(
        ss_lit.as_operand.get(), (op_inv(lit2, lit1))
    )  # C ss [10, 15] - 5 == [5, 10]
    # Test for not wrongful is estimation
    assert not not_none(is_lit).equals(
        op_inv(lit2, lit1).get_sibling_trait(F.Literals.is_literal),
        g=repr_map.G_out,
        tg=repr_map.tg_out,
    )  # C not is [5, 10]

    # Test for correct is estimation
    try:
        assert not_none(is_lit).equals_singleton(5)  # C is 5
    except AssertionError:
        pytest.xfail("TODO")


_A: list[
    tuple[
        Callable[[BoundExpressions], Callable[..., F.Parameters.can_be_operand]],
        Callable[
            [BoundExpressions],
            list[F.Parameters.can_be_operand | F.Literals.LiteralValues],
        ],
        Callable[
            [BoundExpressions], F.Parameters.can_be_operand | F.Literals.LiteralValues
        ],
    ]
] = [
    # Add tests
    (lambda E: E.add, lambda E: [], lambda E: 0),
    (lambda E: E.add, lambda E: [1, 2, 3, 4, 5], lambda E: 15),
    # Multiply tests
    (lambda E: E.multiply, lambda E: [1, 2, 3, 4, 5], lambda E: 120),
    (lambda E: E.multiply, lambda E: [], lambda E: 1),
    # Power tests
    (lambda E: E.power, lambda E: [2, 3], lambda E: 8),
    # Round tests
    (lambda E: E.round, lambda E: [2.4], lambda E: 2),
    (
        lambda E: E.round,
        lambda E: [E.lit_op_range((-2.6, 5.3))],
        lambda E: E.lit_op_range((-3, 5)),
    ),
    # Abs tests
    (lambda E: E.abs, lambda E: [-2], lambda E: 2),
    (
        lambda E: E.abs,
        lambda E: [E.lit_op_range((-2, 3))],
        lambda E: E.lit_op_range((0, 3)),
    ),
    # Sin tests
    (lambda E: E.sin, lambda E: [0], lambda E: 0),
    (
        lambda E: E.sin,
        lambda E: [E.lit_op_range((0, 2 * math.pi))],
        lambda E: E.lit_op_range((-1, 1)),
    ),
    # Log tests
    (lambda E: E.log, lambda E: [10], lambda E: math.log(10)),
    (
        lambda E: E.log,
        lambda E: [E.lit_op_range((1, 10))],
        lambda E: E.lit_op_range((math.log(1), math.log(10))),
    ),
    # Or tests
    (lambda E: E.or_, lambda E: [False, False, True], lambda E: True),
    (
        lambda E: E.or_,
        lambda E: [False, E.lit_bool(True, False), True],
        lambda E: True,
    ),
    (lambda E: E.or_, lambda E: [], lambda E: False),
    # Not tests
    (lambda E: E.not_, lambda E: [False], lambda E: True),
    # Intersection tests
    (
        lambda E: E.intersection,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((10, 20))],
        lambda E: E.lit_op_range((10, 10)),
    ),
    # Union tests
    (
        lambda E: E.union,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((10, 20))],
        lambda E: E.lit_op_range((0, 20)),
    ),
    # SymmetricDifference tests
    (
        lambda E: E.symmetric_difference,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((10, 20))],
        lambda E: E.lit_op_range((0, 20)),
    ),
    (
        lambda E: E.symmetric_difference,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((5, 20))],
        lambda E: E.lit_op_ranges((0, 5), (10, 20)),
    ),
    # Is tests
    (
        lambda E: E.is_,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((0, 10))],
        lambda E: True,
    ),
    # GreaterOrEqual tests
    (
        lambda E: E.greater_or_equal,
        lambda E: [E.lit_op_range((10, 20)), E.lit_op_range((0, 10))],
        lambda E: True,
    ),
    (
        lambda E: E.greater_or_equal,
        lambda E: [E.lit_op_range((5, 20)), E.lit_op_range((0, 10))],
        lambda E: E.lit_bool(True, False),
    ),
    # GreaterThan tests
    (
        lambda E: E.greater_than,
        lambda E: [E.lit_op_range((10, 20)), E.lit_op_range((0, 10))],
        lambda E: E.lit_bool(True, False),
    ),
    (
        lambda E: E.greater_than,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((10, 20))],
        lambda E: False,
    ),
    # IsSubset tests
    (
        lambda E: E.is_subset,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((0, 20))],
        lambda E: True,
    ),
]


@pytest.mark.parametrize(
    "op_factory, lits_factory, expected_factory",
    _A,
)
def test_exec_pure_literal_expressions(
    op_factory: Callable[
        [BoundExpressions], Callable[..., F.Parameters.can_be_operand]
    ],
    lits_factory: Callable[
        [BoundExpressions], list[F.Parameters.can_be_operand | F.Literals.LiteralValues]
    ],
    expected_factory: Callable[
        [BoundExpressions], F.Parameters.can_be_operand | F.Literals.LiteralValues
    ],
):
    E = BoundExpressions()
    from faebryk.core.solver.symbolic.pure_literal import (
        _exec_pure_literal_expressions,
    )

    op = op_factory(E)
    lits = lits_factory(E)
    expected = expected_factory(E)

    lits_converted = [
        F.Literals.make_simple_lit_singleton(E.g, E.tg, lit).get_trait(
            F.Parameters.can_be_operand
        )
        if not isinstance(lit, fabll.Node)
        else lit
        for lit in lits
    ]
    expected_converted = (
        F.Literals.make_simple_lit_singleton(E.g, E.tg, expected).get_trait(
            F.Parameters.can_be_operand
        )
        if not isinstance(expected, fabll.Node)
        else expected
    ).get_sibling_trait(F.Literals.is_literal)

    expr = op(*lits_converted)  # type: ignore
    assert not_none(
        _exec_pure_literal_expressions(
            E.g, E.tg, expr.get_sibling_trait(F.Expressions.is_expression)
        )
    ).equals(expected_converted, g=E.g, tg=E.tg)

    if op == E.greater_than:
        pytest.xfail("GreaterThan is not supported in solver")

    def _get_param_from_lit(lit: F.Literals.is_literal):
        if fabll.Traits(lit).get_obj_raw().isinstance(F.Literals.Booleans):
            return E.bool_parameter_op()
        else:
            return E.parameter_op()

    result = _get_param_from_lit(expected_converted)
    E.is_(result, expr, assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify_symbolically(E.tg, E.g).data.mutation_map
    assert not_none(
        repr_map.try_get_literal(
            result.get_sibling_trait(F.Parameters.is_parameter_operatable)
        )
    ).equals(
        expected_converted,
        g=E.g,
        tg=E.tg,
    )


@pytest.mark.slow
# @pytest.mark.parametrize(
#    "v_in, v_out, total_current",
#    [
#        (
#            lit_op_range(((9.9, E.U.V), (10.1, E.U.V))),
#            lit_op_range(((3.0, E.U.V), (3.2, E.U.V))),
#            lit_op_range(((1, P.mA), (3, P.mA))),
#        ),
#    ],
# )
# def test_solve_voltage_divider_complex(v_in, v_out, total_current):
@pytest.mark.skip(
    reason="TODO: Removed Resistor Voltage Divider, add back with new implementation"
)
def test_solve_voltage_divider_complex():
    pass
    # E = BoundExpressions()
    # v_in, v_out, total_current = (
    #     E.lit_op_range(((9.9, E.U.V), (10.1, E.U.V))),
    #     E.lit_op_range(((3.0, E.U.V), (3.2, E.U.V))),
    #     E.lit_op_range(((1e-3, E.U.A), (3e-3, E.U.A))),
    # )

    # rdiv = F.ResistorVoltageDivider()

    # rdiv.v_in.alias_is(v_in)
    # rdiv.v_out.constrain_subset(v_out)
    # rdiv.max_current.constrain_subset(total_current)

    # # Solve for r_top
    # print("Solving for r_top")
    # solver = DefaultSolver()
    # solver.update_superset_cache(rdiv)

    # r_top = solver.inspect_get_known_supersets(rdiv.r_top.resistance)
    # assert isinstance(r_top, Quantity_Interval_Disjoint)
    # print(f"r_top: {r_top}")
    # expected_r_top = (v_in - v_out) / total_current
    # print(f"Expected r_top: {expected_r_top}")
    # assert r_top == expected_r_top

    # # Pick a random valid resistor for r_top
    # rand_ = Decimal(random())
    # r_any_nominal = r_top.min_elem + rand_ * (r_top.max_elem - r_top.min_elem)
    # assert isinstance(r_any_nominal, Quantity)
    # r_any = lit_op_range_from_center_rel(r_any_nominal, 0.01)
    # rdiv.r_top.resistance.alias_is(r_any)
    # print(f"Set r_top to {r_any}")

    # # Solve for r_bottom
    # solver.update_superset_cache(rdiv)
    # r_bottom = solver.inspect_get_known_supersets(rdiv.r_bottom.resistance)
    # assert isinstance(r_bottom, Quantity_Interval_Disjoint)
    # print(f"r_bottom: {r_bottom}")
    # expected_r_bottom_1 = (v_in / total_current) - r_any
    # expected_r_bottom_2 = v_out / total_current
    # expected_r_bottom_3 = v_out * r_any / (v_in - v_out)
    # print(f"Expected r_bottom subset by voltage: {expected_r_bottom_1}")
    # print(f"Expected r_bottom subset by current: {expected_r_bottom_2}")
    # print(f"Expected r_bottom subset by voltage and current: {expected_r_bottom_3}")
    # assert r_bottom.is_subset_of(expected_r_bottom_1)
    # assert r_bottom.is_subset_of(expected_r_bottom_2)
    # assert r_bottom.is_subset_of(expected_r_bottom_3)
    # # print results
    # res_total_current = v_in / (r_any + r_bottom)
    # # res_v_out = v_in * r_bottom / (r_any + r_bottom)
    # res_v_out = v_in / (1 + r_any / r_bottom)
    # solver_total_current = solver.inspect_get_known_supersets(rdiv.max_current)
    # solver_v_out = solver.inspect_get_known_supersets(rdiv.v_out)
    # print(f"Resulting current {res_total_current} ss! {total_current}")
    # print(f"Solver thinks current is {solver_total_current}")
    # print(f"Resulting v_out {res_v_out} ss! {v_out}")
    # print(f"Solver thinks v_out is {solver_v_out}")

    # # check valid result
    # assert res_total_current.is_subset_of(total_current)
    # if not res_v_out.is_subset_of(v_out) and res_v_out.is_subset_of(
    #     v_out * lit_op_range_from_center_rel(1, 0.05)
    # ):
    #     pytest.xfail("Slightly inaccurate, need more symbolic correlation")

    # assert res_v_out.is_subset_of(v_out)

    # # check solver knowing result
    # assert solver_v_out == res_v_out
    # assert solver_total_current == res_total_current


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()

    # typer.run(test_simplify)
    typer.run(
        lambda: test_super_simple_literal_folding(F.Expressions.Add.c, (5, 10), 15)
    )
