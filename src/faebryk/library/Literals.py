from dataclasses import dataclass
from enum import Enum
from typing import Self, cast

from typing_extensions import deprecated

import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none, once


class is_literal(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def is_subset_of(self, other: "is_literal") -> bool:
        # TODO
        return False

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

    @staticmethod
    def intersect_all(*objs: "is_literal") -> "is_literal":
        # TODO
        pass

    def equals(self, other: "is_literal") -> bool:
        return self.switch_cast().equals(other.switch_cast())

    def equals_singleton(self, singleton: "LiteralValues") -> bool:
        # TODO
        pass

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
        raise ValueError(f"Cannot cast literal {self} to any of {types}")

    def pretty_repr(self) -> str:
        # TODO
        lit = self.switch_cast()
        return f"{lit.get_type_name()}({lit.get_values()})"


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

    _is_literal = fabll.Traits.MakeEdge(is_literal.MakeChild())
    _can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

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
    def MakeChild(cls, *values: str) -> fabll._ChildField[Self]:
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

    @staticmethod
    def make_lit(tg: graph.TypeGraph, value: str) -> "Strings":
        return Strings.bind_typegraph(tg=tg).create_instance(
            g=tg.get_graph_view(), attributes=LiteralsAttributes(value=value)
        )


class Numbers(fabll.Node):
    from faebryk.library.Parameters import can_be_operand

    _is_literal = fabll.Traits.MakeEdge(is_literal.MakeChild())
    _can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    def setup(self, *intervals: fabll.NodeT, unit: fabll.NodeT) -> Self:
        # TODO
        return self

    def setup_from_interval(
        self,
        lower: float | None,
        upper: float | None,
        unit: "F.Units.IsUnit | type[fabll.NodeT] | None" = None,
    ) -> Self:
        # TODO
        return self

    def setup_from_singleton(
        self,
        value: float,
        unit: "F.Units.IsUnit | type[fabll.NodeT] | None" = None,
    ) -> Self:
        # TODO
        return self

    def deserialize(self, data: dict) -> Self:
        # TODO
        return self

    @classmethod
    def bind_from_interval(cls, tg: graph.TypeGraph, g: graph.GraphView):
        from faebryk.library.Units import Dimensionless

        class NumbersBound:
            def __init__(self, tg: graph.TypeGraph, g: graph.GraphView):
                self.tg = tg
                self.g = g

            def setup_from_interval(
                self,
                lower: float | None,
                upper: float | None,
                unit: type[fabll.NodeT] = Dimensionless,
            ) -> Self:
                return (
                    cls.bind_typegraph(tg=tg)
                    .create_instance(g=g)
                    .setup_from_interval(lower=lower, upper=upper, unit=unit)
                )

        return NumbersBound(tg=tg, g=g).setup_from_interval

    def get_value(self) -> float:
        return float(self.instance.node().get_dynamic_attrs().get("value", 0))

    @classmethod
    def MakeChild(cls, value: float) -> fabll._ChildField[Self]:
        assert isinstance(value, float), "Value of number literal must be a float"
        return fabll._ChildField(cls, attributes=LiteralsAttributes(value=value))

    @classmethod
    def MakeChild_ConstrainToLiteral(
        cls, ref: fabll.RefPath, value: float
    ) -> fabll._ChildField[Self]:
        from faebryk.library.Expressions import Is

        assert isinstance(value, float) or isinstance(value, int), (
            "Value of number literal must be a float or int"
        )
        value = float(value)
        lit = cls.MakeChild(value=value)
        out = Is.MakeChild_Constrain([ref, [lit]])
        out.add_dependant(lit, identifier="lit", before=True)
        return out

    @classmethod
    def unbounded(cls, units: fabll.NodeT) -> "Numbers": ...
    def is_empty(self) -> bool: ...
    def min_elem(self) -> "Numbers": ...
    def max_elem(self) -> "Numbers": ...
    def closest_elem(self, target: "Numbers") -> "Numbers": ...
    def is_superset_of(self, other: "Numbers") -> bool: ...
    def is_subset_of(self, other: "Numbers") -> bool: ...
    def op_greater_or_equal(self, other: "Numbers") -> "Booleans": ...
    def op_greater_than(self, other: "Numbers") -> "Booleans": ...

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
    def are_units_compatible(self, unit: "F.Units.IsUnit") -> bool: ...

    @staticmethod
    def make_lit(tg: graph.TypeGraph, value: float) -> "Numbers":
        return Numbers.bind_typegraph(tg=tg).create_instance(
            g=tg.get_graph_view(), attributes=LiteralsAttributes(value=value)
        )


@dataclass(frozen=True)
class BooleansAttributes(fabll.NodeAttributes):
    has_true: bool
    has_false: bool


class Booleans(fabll.Node[BooleansAttributes]):
    from faebryk.library.Parameters import can_be_operand

    Attributes = BooleansAttributes
    _is_literal = fabll.Traits.MakeEdge(is_literal.MakeChild())
    _can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    def setup(self) -> Self:
        return self

    def get_single(self) -> bool:
        # TODO
        pass

    @classmethod
    def MakeChild(cls, *values: bool) -> fabll._ChildField[Self]:
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
        attrs = self.attributes()
        return [True] * attrs.has_true + [False] * attrs.has_false

    def op_or(self, other: "Booleans") -> "Booleans": ...
    def op_and(self, other: "Booleans") -> "Booleans": ...
    def op_not(self) -> "Booleans": ...
    def op_xor(self, other: "Booleans") -> "Booleans": ...
    def op_implies(self, other: "Booleans") -> "Booleans": ...

    def is_true(self) -> bool:
        return self.get_values() == [True]

    def is_false(self) -> bool:
        return self.get_values() == [False]

    def equals(self, other: "Booleans") -> bool:
        return self.get_values() == other.get_values()


class EnumValue(fabll.Node):
    from faebryk.library.Parameters import StringParameter

    name_ = StringParameter.MakeChild()
    value_ = StringParameter.MakeChild()

    @classmethod
    def MakeChild(cls, name: str, value: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(Strings.MakeChild_ConstrainToLiteral([out, cls.name_], name))
        out.add_dependant(
            Strings.MakeChild_ConstrainToLiteral([out, cls.value_], value)
        )
        return out

    @property
    def name(self) -> str:
        return self.name_.get().force_extract_literal().get_values()[0]

    @property
    def value(self) -> str:
        return self.value_.get().force_extract_literal().get_values()[0]


class AbstractEnums(fabll.Node):
    from faebryk.library.Literals import is_literal
    from faebryk.library.Parameters import can_be_operand

    _is_literal = fabll.Traits.MakeEdge(is_literal.MakeChild())
    _can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())
    _values = F.Collections.PointerSet.MakeChild()

    def get_enum_value(self, enum_member: Enum) -> EnumValue:
        for enum_value in self.get_children(direct_only=True, types=EnumValue):
            enum_value_bound = EnumValue.bind_instance(instance=enum_value.instance)
            if enum_value_bound.name == enum_member.name:
                return enum_value_bound
        raise ValueError(f"Enum member {enum_member.name} not found in enum type")

    def setup(self, *enum_values: Enum) -> Self:
        atype = EnumsFactory(type(enum_values[0]))
        atype_n = AbstractEnums.bind_instance(
            atype.bind_typegraph(tg=self.tg).get_or_create_type()
        )
        for enum_value in enum_values:
            self._values.get().append(atype_n.get_enum_value(enum_member=enum_value))
        return self

    def get_values(self) -> list[str]:
        enum_values = list[str]()
        values = self._values.get().as_list()
        for value in values:
            enum_value = EnumValue.bind_instance(instance=value.instance)
            enum_values.append(enum_value.value)

        return enum_values

    def get_all_members(self) -> list[EnumValue]:
        if (
            self.get_type_node() is None
        ):  # TODO better to do if self.try_get_trait(fabll.ImplementsType) is not None
            return list(self.get_children(direct_only=True, types=EnumValue))
        else:
            return list(
                fabll.Node.bind_instance(
                    instance=not_none(self.get_type_node())
                ).get_children(direct_only=True, types=EnumValue)
            )

    def get_enum_as_dict(self) -> dict[str, str]:
        return {member.name: member.value for member in self.get_all_members()}

    def get_single_value(self) -> str | None:
        values = self.get_values()
        return None if len(values) == 0 else values[0]

    @classmethod
    def MakeChild(cls, *enum_members: Enum) -> fabll._ChildField:
        atype = EnumsFactory(type(enum_members[0]))
        cls_n = cast(type[fabll.NodeT], atype)
        out = fabll._ChildField(cls)

        for value in enum_members:
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge(
                    [out, cls._values],
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


def make_lit(tg: graph.TypeGraph, value: LiteralValues) -> LiteralNodes:
    match value:
        case bool():
            return Booleans.bind_typegraph(tg=tg).create_instance(
                g=tg.get_graph_view(),
                attributes=BooleansAttributes(has_true=value, has_false=not value),
            )
        case float() | int():
            value = float(value)
            return Numbers.make_lit(tg=tg, value=value)
        case Enum():
            return AbstractEnums.bind_typegraph(tg=tg).create_instance(
                g=tg.get_graph_view(), attributes=LiteralsAttributes(value=value)
            )
        case str():
            return Strings.make_lit(tg=tg, value=value)


# TODO
def MakeChild_Literal(
    value: LiteralValues, enum_type: type[Enum] | None = None
) -> (
    fabll._ChildField[Strings]
    | fabll._ChildField[Booleans]
    | fabll._ChildField[Numbers]
    | fabll._ChildField[AbstractEnums]
):
    match value:
        case bool():
            return Booleans.MakeChild(value=value)
        case float() | int():
            value = float(value)
            return Numbers.MakeChild(value=value)
        case Enum():
            if enum_type is None:
                raise ValueError("Enum must be provided when creating an enum literal")
            return AbstractEnums.MakeChild(*enum_type)
        case str():
            return Strings.MakeChild(value)


# Binding context ----------------------------------------------------------------------


class BoundLiteralContext:
    def __init__(self, tg: graph.TypeGraph, g: graph.GraphView):
        self.tg = tg
        self.g = g

    @property
    @once
    def Numbers(self):
        return Numbers.bind_typegraph(tg=self.tg)

    @property
    @once
    def Booleans(self):
        return Booleans.bind_typegraph(tg=self.tg)

    @property
    @once
    def Enums(self):
        return AbstractEnums.bind_typegraph(tg=self.tg)

    @property
    @once
    def Strings(self):
        return Strings.bind_typegraph(tg=self.tg)

    def create_numbers(self) -> "Numbers":
        return self.Numbers.create_instance(g=self.g)

    def create_booleans(self) -> "Booleans":
        return self.Booleans.create_instance(g=self.g)

    def create_enums(self) -> "AbstractEnums":
        return self.Enums.create_instance(g=self.g)

    def create_strings(self) -> "Strings":
        return self.Strings.create_instance(g=self.g)

    def create_numbers_from_singleton(
        self, value: float, unit: "F.Units.IsUnit | type[fabll.NodeT] | None" = None
    ) -> "Numbers":
        return self.create_numbers().setup_from_singleton(value=value, unit=unit)

    def create_numbers_from_interval(
        self, lower: float | None, upper: float | None, unit: "F.Units.IsUnit"
    ) -> "Numbers":
        return self.create_numbers().setup_from_interval(
            lower=lower, upper=upper, unit=unit
        )

    # TODO add other literal constructors


def test_bound_context():
    g = graph.GraphView.create()
    tg = graph.TypeGraph.create(g=g)
    ctx = BoundLiteralContext(tg=tg, g=g)

    my_number = ctx.create_numbers_from_singleton(value=1.0)

    print(my_number)


def test_string_literal_instance():
    values = ["a", "b", "c"]
    g = graph.GraphView.create()
    tg = graph.TypeGraph.create(g=g)

    string_set = (
        Strings.bind_typegraph(tg=tg).create_instance(g=g).setup_from_values(*values)
    )

    assert string_set.get_values() == values


def test_string_literal_make_child():
    values = ["a", "b", "c"]
    g = graph.GraphView.create()
    tg = graph.TypeGraph.create(g=g)

    class MyType(fabll.Node):
        string_set = Strings.MakeChild(*values)

    my_instance = MyType.bind_typegraph(tg=tg).create_instance(g=g)

    print(my_instance.string_set.get().get_values())
    assert my_instance.string_set.get().get_values() == values


# def test_string_literal_on_type():
#     values = ["a", "b", "c"]
#     g = graph.GraphView.create()
#     tg = graph.TypeGraph.create(g=g)

#     class MyType(fabll.Node):
#         string_set = Strings.MakeChild(*values).put_on_type()

# my_type = MyType.bind_typegraph(tg=tg).get_or_create_type()

# TODO


def test_string_literal_alias_to_literal():
    from faebryk.library.Parameters import StringParameter, is_parameter_operatable

    values = ["a", "b", "c"]
    g = graph.GraphView.create()
    tg = graph.TypeGraph.create(g=g)

    class MyType(fabll.Node):
        string_param = StringParameter.MakeChild()

        @classmethod
        def MakeChild(cls, *values: str) -> fabll._ChildField[Self]:
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
