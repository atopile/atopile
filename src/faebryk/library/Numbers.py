from dataclasses import dataclass
from typing import ClassVar

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition


@dataclass(frozen=True)
class NumericAttributes(fabll.NodeAttributes):
    value: float


class Numeric(fabll.Node[NumericAttributes]):
    Attributes = NumericAttributes

    @classmethod
    def MakeChild(cls, value: float) -> fabll._ChildField:
        out = fabll._ChildField(cls, attributes=NumericAttributes(value=value))
        return out


# TODO: rename to NumericInterval
class ContinuousNumeric(fabll.Node):
    _min_identifier: ClassVar[str] = "min"
    _max_identifier: ClassVar[str] = "max"

    @classmethod
    def MakeChild(cls, min: float, max: float) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(Numeric.MakeChild(min), identifier=cls._min_identifier)
        out.add_dependant(Numeric.MakeChild(max), identifier=cls._max_identifier)
        return out

    def get_min(self) -> fabll.Node[NumericAttributes]:
        numeric_instance = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._min_identifier
        )
        assert numeric_instance is not None
        return Numeric(instance=numeric_instance)

    def get_max(self) -> fabll.Node[NumericAttributes]:
        numeric_instance = EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=self._max_identifier
        )
        assert numeric_instance is not None
        return Numeric(instance=numeric_instance)


class QuantityInterval(fabll.Node):
    _numeric_interval_identifier: ClassVar[str] = "numeric_interval"
    unit = F.Collections.Pointer.MakeChild()


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
