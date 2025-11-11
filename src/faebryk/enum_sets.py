from enum import Enum
from typing import Protocol, Self, cast

import faebryk.core.node as fabll
import faebryk.core.zig.gen.graph.graph as graph
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition


class EnumValue(fabll.Node):
    value = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, enum_value: F.Literals.LiteralValues) -> fabll.ChildField[Self]:
        out = fabll.ChildField(cls)
        literal = F.Literals.make_lit_child(value=enum_value)
        out.add_dependant(
            F.Collections.Pointer.EdgeField(
                [out, cls.value],
                [literal],
            )
        )
        out.add_dependant(literal, before=True)
        return out

    def get_name(self) -> str:
        _, name = self.get_parent_force()
        return name

    def get_value(self) -> fabll.NodeT:
        return self.value.get().deref()


class EnumsProtocol(Protocol):
    def setup(self, *enum_values: Enum) -> Self: ...
    @classmethod
    def get_enum_value_type(
        cls, tg: fabll.TypeGraph, enum_value: Enum
    ) -> EnumValue: ...

    @classmethod
    def create_instance(cls, tg: fabll.TypeGraph, g: graph.GraphView) -> Self: ...

    def get_elements(self) -> list[EnumValue]: ...


def EnumsFactory(enum_type: type[Enum]) -> type[EnumsProtocol]:
    class ConcreteEnums(fabll.Node):
        _is_literal = F.Literals.is_literal.MakeChild()
        values = F.Collections.PointerSet.MakeChild()

        @classmethod
        def get_enum_value_type(
            cls, tg: fabll.TypeGraph, enum_value: Enum
        ) -> EnumValue:
            bound_e = cls.bind_typegraph(tg)
            e_val = EdgeComposition.get_child_by_identifier(
                bound_node=bound_e.get_or_create_type(),
                child_identifier=enum_value.name,
            )
            if e_val is None:
                raise ValueError(f"Enum value {enum_value.name} not found in enum type")
            return EnumValue.bind_instance(instance=e_val)

        def setup(self, *enum_values: Enum) -> Self:
            for enum_value in enum_values:
                self.values.get().append(
                    type(self).get_enum_value_type(tg=self.tg, enum_value=enum_value)
                )
            return self

        def get_elements(self) -> list[EnumValue]:
            return [
                EnumValue.bind_instance(instance=e_val.instance)
                for e_val in self.values.get().as_set()
            ]

        @classmethod
        def create_instance(cls, tg: fabll.TypeGraph, g: graph.GraphView) -> Self:
            return cls.bind_typegraph(tg=tg).create_instance(g=g)

    ConcreteEnums.__name__ = f"{enum_type.__name__}"

    for e_val in enum_type:
        ConcreteEnums._add_field(
            e_val.name, EnumValue.MakeChild(enum_value=e_val.value).put_on_type()
        )
    return cast(type[EnumsProtocol], ConcreteEnums)


def test_enums_basic():
    from faebryk.core.node import _make_graph_and_typegraph

    g, tg = _make_graph_and_typegraph()

    class MyEnum(Enum):
        A = "a"
        B = "bc"
        D = "d"

    EnumT = EnumsFactory(MyEnum)

    my_enum_set = EnumT.create_instance(tg=tg, g=g).setup(MyEnum.A, MyEnum.D)
    for e_val in my_enum_set.get_elements():
        print(e_val.get_name(), e_val.get_value())
