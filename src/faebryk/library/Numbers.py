from dataclasses import dataclass

# from re import I
from typing import ClassVar

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph import graph


@dataclass(frozen=True)
class NumericAttributes(fabll.NodeAttributes):
    value: float


class Numeric(fabll.Node[NumericAttributes]):
    Attributes = NumericAttributes

    @classmethod
    def MakeChild(cls, value: float) -> fabll._ChildField:
        out = fabll._ChildField(cls, attributes=NumericAttributes(value=value))
        return out

    F.Literals.Numbers.MakeChild_ConstrainToLiteral

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
    def MakeChild(cls, min: float, max: float) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        min_numeric = Numeric.MakeChild(min)
        max_numeric = Numeric.MakeChild(max)
        out.add_dependant(min_numeric, identifier=cls._min_identifier)
        out.add_dependant(max_numeric, identifier=cls._max_identifier)
        fabll.MakeEdge(lhs=[out], rhs=[min_numeric], edge=EdgeComposition)
        return out

    def get_min(self) -> Numeric:
        numeric_instance = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._min_identifier
        )
        print("numeric_instance:", numeric_instance)
        assert numeric_instance is not None
        return Numeric.bind_instance(numeric_instance)

    def get_max(self) -> Numeric:
        numeric_instance = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._max_identifier
        )
        assert numeric_instance is not None
        return Numeric.bind_instance(numeric_instance)

    def create(self, g: graph.GraphView) -> "NumericInterval":
        return NumericInterval.bind_typegraph(tg=self.tg).create_instance(g=g)

    # def setup(self, min: float, max: float) -> "NumericInterval":
    #     # Validate that min is a number. Raise TypeError if not.
    #     if not isinstance(min, (int, float)):
    #         raise TypeError(
    #             f"'min' must be a number (int or float), got {type(min).__name__}"
    #         )
    #     if not isinstance(max, (int, float)):
    #         raise TypeError(
    #             f"'max' must be a number (int or float), got {type(max).__name__}"
    #         )
    #     if min > max:
    #         raise ValueError(
    #             f"'min' must be less than or equal to 'max', got {min} > {max}"
    #         )

    #     #  Add numeric literals to the node min and max fields
    #     g = self.instance.g()
    #     _ = EdgeComposition.add_child(
    #         bound_node=self.instance,
    #         child=Numeric.init(g, min).instance.node,
    #         child_identifier=self._min_identifier,
    #     )
    #     _ = EdgeComposition.add_child(
    #         bound_node=self.instance,
    #         child=Numeric.init(max).instance.node,
    #         child_identifier=self._max_identifier,
    #     )


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


class QuantityInterval(fabll.Node):
    _numeric_interval_identifier: ClassVar[str] = "numeric_interval"
    unit = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(
        cls, min: float, max: float, unit: type[fabll.Node]
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            NumericInterval.MakeChild(min, max),
            identifier=cls._numeric_interval_identifier,
        )
        # TODO: Requires ref_path to support type as an input
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.unit], [unit, "_is_unit"])
        )
        return out

    @classmethod
    def MakeChild_FromCenter(
        cls, center: float, abs_tol: float, unit: type[fabll.Node]
    ) -> fabll._ChildField:
        min = center - abs_tol
        max = center + abs_tol
        return cls.MakeChild(min, max, unit)

    @classmethod
    def MakeChild_FromCenter_Rel(
        cls, center: float, rel_tol: float, unit: type[fabll.Node]
    ) -> fabll._ChildField:
        min = center - center * rel_tol
        max = center + center * rel_tol
        return cls.MakeChild(min, max, unit)

    def setup(self, min: float, max: float, unit: fabll.Node) -> "QuantityInterval":
        # Add child intance of NumericInterval
        numeric_interval = NumericInterval.create(self.instance.g())

        EdgeComposition.add_child(
            bound_node=self.instance,
            child=numeric_interval.instance.node,
            child_identifier=QuantityInterval._numeric_interval_identifier,
        )

        # Get the is_unit trait from the unit node
        is_unit = unit.get_trait(F.Units.IsUnit)

        # Add pointer to the unit trait
        EdgePointer.point_to(
            bound_node=self.instance,
            target_node=is_unit.instance.node(),
            identifier=None,
            order=None,
        )

    def create(self, min: float, max: float, unit: fabll.Node) -> "QuantityInterval":
        tg = self.tg
        g = self.instance.g()
        return QuantityInterval.bind_typegraph(tg=tg).create_instance(g=g)

    def get_min(self) -> "QuantityInterval":
        interval = self.get_numeric_interval()
        return self.base_to_units(interval.get_min())

    def get_numeric_interval(self) -> "NumericInterval":
        numeric_interval_node = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._numeric_interval_identifier
        )
        assert numeric_interval_node is not None
        return NumericInterval.bind_instance(instance=numeric_interval_node)

    def get_unit(self) -> type[fabll.Node]:
        # Get the is_unit trait that is pointed to by the unit field
        # Get the parent unit node
        # Return the unit node
        raise NotImplementedError


# class MagnitudeSet(fabll.Node):
#     intervals = F.Collections.PointerSequence.MakeChild()

#     @classmethod
#     def MakeChild_Empty(cls) -> fabll._ChildField:
#         return fabll._ChildField(cls)

#     @classmethod
#     def MakeChild(cls, min: float, max: float) -> fabll._ChildField:
#         out = fabll._ChildField(cls)
#         out.get().intervals.add_dependant(ContinuousNumeric.MakeChild(min, max))
#         return out


# class QuantitySet(fabll.Node):
#     unit = F.Collections.Pointer.MakeChild()
#     _magnitude_set_identifier: ClassVar[str] = "magnitude_set"

#     @classmethod
#     def MakeChild_FromRange(
#         cls, min: float, max: float, unit: fabll._ChildField[F.Units.IsUnit]
#     ) -> fabll._ChildField:
#         out = fabll._ChildField(cls)
#         magnitude_set = MagnitudeSet.MakeChild(min, max)
#         out.add_dependant(magnitude_set, identifier=cls._magnitude_set_identifier)
#         out.get().unit.add_dependant(
#             F.Collections.Pointer.MakeEdge([out, cls.unit], [unit])
#         )
#         return out

#     @classmethod
#     def MakeChild_FromCenter(
#         cls, center: float, abs_tol: float, unit: fabll._ChildField[F.Units.IsUnit]
#     ) -> fabll._ChildField:
#         min, max = center - abs_tol, center + abs_tol
#         return cls.MakeChild_FromRange(min, max, unit)

#     @classmethod
#     def MakeChild_FromCenter_Rel(
#         cls, center: float, rel_tol: float, unit: fabll._ChildField[F.Units.IsUnit]
#     ) -> fabll._ChildField:
#         min, max = center - center * rel_tol, center + center * rel_tol
#         return cls.MakeChild_FromRange(min, max, unit)
