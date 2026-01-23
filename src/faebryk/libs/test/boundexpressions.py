# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.Units import UnitExpressionFactory

_Unit = type[fabll.NodeT]
_Quantity = tuple[float, _Unit]
_Range = tuple[float, float] | tuple[_Quantity, _Quantity]

Range = F.Literals.Numbers

dimensionless = F.Units.Dimensionless


class BoundExpressions:
    """
    A class to bind expressions to a graph and typegraph for concise test code.
    """

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
        rpm = F.Units.Rpm

        # Data units
        bit = F.Units.Bit
        B = F.Units.Byte
        bps = F.Units.BitsPerSecond

        # Compound units
        Ah = F.Units.AmpereHour
        As = F.Units.AmpereSecond
        Vps = F.Units.VoltsPerSecond

        # Prefixed units for test convenience
        mA = UnitExpressionFactory(
            ("mA",),
            ((F.Units.Ampere, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["m"],
        )
        uA = UnitExpressionFactory(
            ("uA",),
            ((F.Units.Ampere, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["u"],
        )
        mV = UnitExpressionFactory(
            ("mV",),
            ((F.Units.Volt, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["m"],
        )
        kOhm = UnitExpressionFactory(
            ("kΩ",),
            ((F.Units.Ohm, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["k"],
        )
        MOhm = UnitExpressionFactory(
            ("MΩ",),
            ((F.Units.Ohm, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["M"],
        )
        pF = UnitExpressionFactory(
            ("pF",),
            ((F.Units.Farad, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["p"],
        )
        nF = UnitExpressionFactory(
            ("nF",),
            ((F.Units.Farad, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["n"],
        )
        uF = UnitExpressionFactory(
            ("uF",),
            ((F.Units.Farad, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["u"],
        )
        mF = UnitExpressionFactory(
            ("mF",),
            ((F.Units.Farad, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["m"],
        )
        GF = UnitExpressionFactory(
            ("GF",),
            ((F.Units.Farad, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["G"],
        )
        uH = UnitExpressionFactory(
            ("uH",),
            ((F.Units.Henry, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["u"],
        )
        mH = UnitExpressionFactory(
            ("mH",),
            ((F.Units.Henry, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["m"],
        )
        kHz = UnitExpressionFactory(
            ("kHz",),
            ((F.Units.Hertz, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["k"],
        )
        MHz = UnitExpressionFactory(
            ("MHz",),
            ((F.Units.Hertz, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["M"],
        )
        GHz = UnitExpressionFactory(
            ("GHz",),
            ((F.Units.Hertz, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["G"],
        )
        mW = UnitExpressionFactory(
            ("mW",),
            ((F.Units.Watt, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["m"],
        )
        kW = UnitExpressionFactory(
            ("kW",),
            ((F.Units.Watt, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["k"],
        )
        mm = UnitExpressionFactory(
            ("mm",),
            ((F.Units.Meter, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["m"],
        )
        cm = UnitExpressionFactory(
            ("cm",),
            ((F.Units.Meter, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["c"],
        )
        km = UnitExpressionFactory(
            ("km",),
            ((F.Units.Meter, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["k"],
        )
        nH = UnitExpressionFactory(
            ("nH",),
            ((F.Units.Henry, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["n"],
        )
        kohm = UnitExpressionFactory(
            ("kΩ",),
            ((F.Units.Ohm, 1),),
            multiplier=F.Units.is_si_prefixed_unit.SI_PREFIXES["k"],
        )

        def __init__(self, E: "BoundExpressions") -> None:
            self.E = E

        def make_dl(self) -> "F.Units.is_unit":
            return (
                F.Units.Dimensionless.bind_typegraph(tg=self.E.tg)
                .create_instance(g=self.E.g)
                .is_unit.get()
            )

        def make_H(self) -> "F.Units.is_unit":
            return (
                F.Units.Henry.bind_typegraph(tg=self.E.tg)
                .create_instance(g=self.E.g)
                .is_unit.get()
            )

        def make_Hz(self) -> "F.Units.is_unit":
            return (
                F.Units.Hertz.bind_typegraph(tg=self.E.tg)
                .create_instance(g=self.E.g)
                .is_unit.get()
            )

    def __init__(
        self, g: graph.GraphView | None = None, tg: fbrk.TypeGraph | None = None
    ):
        self.g = g or graph.GraphView.create()
        self.tg = tg or fbrk.TypeGraph.create(g=self.g)

        self.u = self.U(self)

    def _resolve_unit(self, unit: type[fabll.Node]) -> F.Units.is_unit | None:
        instance = unit.bind_typegraph(tg=self.tg).create_instance(g=self.g)

        if is_unit_expr := instance.try_get_trait(F.Units.is_unit_expression):
            is_unit_expr.get_obj().setup(cast(type[F.Units.UnitExpression], unit))
            resolved = F.Units.resolve_unit_expression(
                g=self.g, tg=self.tg, expr=instance.instance
            )
            if resolved is None:
                return None
            return resolved.get_trait(F.Units.is_unit)

        return instance.get_trait(F.Units.is_unit)

    def parameter_op(
        self,
        units: "type[fabll.Node] | None" = None,
        within: "F.Literals.Numbers | None" = None,
        domain: "F.NumberDomain.Args | type[F.Parameters.NumericParameter.DOMAIN_SKIP] | None" = None,  # noqa: E501
        attach_to: "tuple[fabll.Node, str] | None" = None,
        name: "str | None" = None,
    ) -> F.Parameters.can_be_operand:
        is_unit_node = (
            self._resolve_unit(units) if units else self._resolve_unit(self.U.dl)
        )
        param = (
            F.Parameters.NumericParameter.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .setup(
                is_unit=is_unit_node,
                within=within,
                domain=domain,
            )
        )

        if name is not None:
            param.is_parameter.get().set_name(name)

        out = param.can_be_operand.get()

        if attach_to:
            parent, p_name = attach_to
            self.g.insert_edge(
                edge=fbrk.EdgeComposition.create(
                    parent=parent.instance.node(),
                    child=fabll.Traits(out).get_obj_raw().instance.node(),
                    child_identifier=p_name,
                )
            )
        return out

    def enum_parameter_op(
        self, enum_type, name: "str | None" = None
    ) -> F.Parameters.can_be_operand:
        param = (
            F.Parameters.EnumParameter.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .setup(enum=enum_type)
        )
        if name is not None:
            param.is_parameter.get().set_name(name)
        return param.can_be_operand.get()

    def bool_parameter_op(
        self, name: "str | None" = None
    ) -> F.Parameters.can_be_operand:
        param = F.Parameters.BooleanParameter.bind_typegraph(
            tg=self.tg
        ).create_instance(g=self.g)
        if name is not None:
            param.is_parameter.get().set_name(name)
        return param.can_be_operand.get()

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

    def is_(
        self,
        *operands: F.Parameters.can_be_operand,
        assert_: bool = False,
        tg: fbrk.TypeGraph | None = None,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Is.c(*operands, g=self.g, tg=self.tg, assert_=assert_)

    def correlated(
        self,
        *operands: F.Parameters.can_be_operand,
        assert_: bool = False,
    ) -> F.Parameters.can_be_operand:
        return F.Expressions.Correlated.c(
            *operands, g=self.g, tg=self.tg, assert_=assert_
        )

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

    def numbers(self) -> F.Literals.Numbers:
        return F.Literals.Numbers.bind_typegraph(tg=self.tg).create_instance(g=self.g)

    def lit_op_single(self, value: float | _Quantity) -> F.Parameters.can_be_operand:
        unit = None
        if isinstance(value, tuple):
            unit: type[fabll.Node] | None = value[1]
            value = value[0]
        else:
            unit = self.U.dl
        is_unit = self._resolve_unit(unit)

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
        is_unit = self._resolve_unit(lower_unit)
        out_lit = (
            F.Literals.Numbers.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .setup_from_min_max(min=lower_value, max=upper_value, unit=is_unit)
        ).is_literal.get()
        return out_lit.as_operand.get()

    def lit_op_ranges(self, *ranges: _Range) -> F.Parameters.can_be_operand:
        ranges_values = [self._range_to(range) for range in ranges]
        assert len(set(range_value[2] for range_value in ranges_values)) == 1
        is_unit = self._resolve_unit(ranges_values[0][2])
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
        ).can_be_operand.get()

    def lit_op_range_from_center_rel(
        self, center: _Quantity, rel: float
    ) -> F.Parameters.can_be_operand:
        value, unit_t = center
        is_unit = self._resolve_unit(unit_t)
        return (
            (
                F.Literals.Numbers.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .setup_from_center_rel(center=value, rel=rel, unit=is_unit)
            )
            .is_literal.get()
            .as_operand.get()
        )

    def lit_op_range_from_center(
        self, center: _Quantity, tolerance: _Quantity
    ) -> F.Parameters.can_be_operand:
        value, unit_t = center
        is_unit = self._resolve_unit(unit_t)

        tol_value, tol_unit_t = tolerance
        tol_is_unit = self._resolve_unit(tol_unit_t)

        tol_scale_factor, tol_offset = tol_is_unit.get_conversion_to(is_unit)
        tol_value = tol_value * tol_scale_factor + tol_offset

        return (
            (
                F.Literals.Numbers.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .setup(
                    numeric_set=F.Literals.NumericSet.bind_typegraph(tg=self.tg)
                    .create_instance(g=self.g)
                    .setup_from_values(values=[(value - tol_value, value + tol_value)]),
                    unit=is_unit,
                )
            )
            .is_literal.get()
            .as_operand.get()
        )

    def lit_bool(self, *values: bool) -> F.Parameters.can_be_operand:
        return (
            F.Literals.Booleans.bind_typegraph(tg=self.tg)
            .create_instance(
                g=self.g,
            )
            .setup_from_values(*values)
            .is_literal.get()
            .as_operand.get()
        )

    def lit_op_enum(self, *values: Enum) -> F.Parameters.can_be_operand:
        concrete_enum = F.Literals.EnumsFactory(type(values[0]))
        _ = fabll.TypeNodeBoundTG.get_or_create_type_in_tg(tg=self.tg, t=concrete_enum)
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
        self, *values: float, unit: type[fabll.Node] | None = None
    ) -> F.Parameters.can_be_operand:
        is_unit = self._resolve_unit(unit or self.U.dl)
        return (
            F.Literals.Numbers.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .setup_from_singletons(values=list(values), unit=is_unit)
            .is_literal.get()
            .as_operand.get()
        )
