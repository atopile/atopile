# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from collections.abc import Iterable, Iterator
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, overload, override, runtime_checkable

from faebryk.libs.units import Unit, dimensionless
from faebryk.libs.util import (
    Serializable,
    SerializableEnum,
)

if TYPE_CHECKING:
    from faebryk.libs.sets.quantity_sets import (
        Quantity_Interval_Disjoint,
        QuantitySetLike,
    )


# Protocols ----------------------------------------------------------------------------
@runtime_checkable
class P_Set[T](Serializable, Protocol):
    def is_empty(self) -> bool: ...

    def is_finite(self) -> bool: ...

    def __bool__(self) -> bool:
        raise Exception("don't use bool to check for emptiness, use is_empty()")

    def __contains__(self, item: T) -> bool: ...

    @staticmethod
    def from_value(value) -> "P_Set":
        from faebryk.libs.sets.quantity_sets import (
            Quantity_Interval_Disjoint,
            QuantitySetLikeR,
        )

        if isinstance(value, QuantitySetLikeR) and not isinstance(value, bool):
            return Quantity_Interval_Disjoint.from_value(value)
        if isinstance(value, (bool, BoolSet)):
            return BoolSet.from_value(value)
        if (
            isinstance(value, Enum)
            or isinstance(value, type)
            and issubclass(value, Enum)
        ):
            return EnumSet(value)
        if isinstance(value, PlainSet):
            return value
        raise ValueError(f"cannot convert {value} to P_Set")

    def is_subset_of(self, other: "P_Set[T]") -> bool:
        assert type(self) is not P_Set
        return self.is_subset_of(other)

    def is_superset_of(self, other: "P_Set[T]") -> bool:
        return P_Set.from_value(other).is_subset_of(self)

    @staticmethod
    def intersect_all[P: P_Set](*sets: P) -> P:
        if not sets:
            raise ValueError("no sets to intersect")
            # return PlainSet()
        out = sets[0]
        for s in sets[1:]:
            out = out & s
        return out

    def __and__[P: P_Set](self: P, other: P) -> P: ...

    def is_single_element(self) -> bool: ...

    def any(self) -> T: ...

    def serialize(self) -> dict:
        return {"type": type(self).__name__, "data": self.serialize_pset()}

    def serialize_pset(self) -> dict: ...

    @classmethod
    def deserialize(cls, data: dict) -> "P_Set":
        from faebryk.libs.sets.numeric_sets import (
            Numeric_Interval,
            Numeric_Interval_Disjoint,
        )
        from faebryk.libs.sets.quantity_sets import (
            Quantity_Interval,
            Quantity_Interval_Disjoint,
            Quantity_Set_Discrete,
        )

        types = [
            Numeric_Interval,
            Numeric_Interval_Disjoint,
            BoolSet,
            EnumSet,
            Quantity_Interval,
            Quantity_Interval_Disjoint,
            Quantity_Set_Discrete,
        ]
        cls_ = next((t for t in types if t.__name__ == data["type"]), None)
        if cls_ is None:
            raise ValueError(f"unknown type {data['type']}")
        return cls_.deserialize_pset(data["data"])

    @classmethod
    def deserialize_pset(cls, data: dict) -> "P_Set": ...


class P_IterableSet[T, IterT](P_Set[T], Iterable[IterT], Protocol): ...


class P_UnitSet[T](P_Set[T], Protocol):
    units: Unit


class P_IterableUnitSet[T, IterT](P_UnitSet[T], Iterable[IterT], Protocol): ...


# TODO consider making abstract
class PlainSet[U](P_IterableUnitSet[U, U]):
    def __init__(self, *elements: "U | PlainSet[U]"):
        self.units = dimensionless

        self.elements: frozenset[U] = frozenset(  # type: ignore
            {v for v in elements if not isinstance(v, PlainSet)}
            | {v for vb in elements if isinstance(vb, PlainSet) for v in vb.elements}
        )

    def is_empty(self) -> bool:
        return len(self.elements) == 0

    def __hash__(self) -> int:
        return hash(self.elements)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(repr(e) for e in self.elements)})"

    def __str__(self) -> str:
        # TODO move enum stuff to EnumSet
        return f"[{
            ', '.join(
                str(e) if not isinstance(e, Enum) else f'{e.name}'
                for e in self.elements
            )
        }]"

    def __iter__(self) -> Iterator[U]:
        return iter(self.elements)

    def op_intersection[T: PlainSet](self: T, other: U | T) -> T:
        return type(self)(*(self.elements & type(self).from_value(other).elements))

    def op_union[T: PlainSet](self: T, other: U | T) -> T:
        return type(self)(*(self.elements | type(self).from_value(other).elements))

    def is_subset_of[T: PlainSet](self: T, other: U | T) -> bool:
        try:
            other_set = type(self).from_value(other)
        except Exception:
            return False
        return self.elements.issubset(other_set.elements)

    def is_single_element(self) -> bool:
        return len(self.elements) == 1

    @classmethod
    def from_value[T: PlainSet](cls: type[T], value: Any) -> T:
        if isinstance(value, cls):
            return value
        return cls(value)

    # operators

    def __and__[T: PlainSet](self: T, other: U | T) -> T:
        return self.op_intersection(other)

    def __or__[T: PlainSet](self: T, other: U | T) -> T:
        return self.op_union(other)

    def __eq__(self, value: Any) -> bool:
        try:
            other = type(self).from_value(value)
        # TODO thats a bit whack
        except Exception:
            return False
        if not isinstance(other, PlainSet):
            return False
        return self.elements == other.elements

    def __contains__(self, item: U) -> bool:
        return item in self.elements

    def any(self) -> U:
        if self.is_empty():
            raise ValueError("no elements in set")
        return next(iter(self.elements))

    def is_finite(self) -> bool:
        return True


type BoolSetLike_ = bool | BoolSet | PlainSet[bool]


class BoolSet(PlainSet[bool]):
    # TODO rethink this
    @override
    def __contains__(self, item: BoolSetLike_) -> bool:
        return all(o_v in self.elements for o_v in BoolSet.from_value(item).elements)

    def op_not(self) -> "BoolSet":
        return BoolSet(*(not v for v in self.elements))

    def op_and(self, other: BoolSetLike_) -> "BoolSet":
        return BoolSet(
            *[
                v and o_v
                for v in self.elements
                for o_v in BoolSet.from_value(other).elements
            ]
        )

    def op_or(self, other: BoolSetLike_) -> "BoolSet":
        return BoolSet(
            *[
                v or o_v
                for v in self.elements
                for o_v in BoolSet.from_value(other).elements
            ]
        )

    @classmethod
    def unbounded(cls) -> "BoolSet":
        return cls(True, False)

    @override
    def serialize_pset(self) -> dict:
        return {"elements": list(self.elements)}

    @override
    @classmethod
    def deserialize_pset(cls, data: dict):
        return cls(*data["elements"])


BoolSetLike = bool | BoolSet | PlainSet[bool]


class EnumSet[E: Enum](PlainSet[SerializableEnum.Value[E]]):
    def __init__(
        self,
        *elements: "E | EnumSet[E] | type[E] | SerializableEnum.Value[E] | SerializableEnum",  # noqa: E501
    ):
        enum_types = (
            {e.enum.enum for e in elements if isinstance(e, EnumSet)}
            | {type(e) for e in elements if isinstance(e, Enum)}
            | {e for e in elements if isinstance(e, type) and issubclass(e, Enum)}
            | {e._enum.enum for e in elements if isinstance(e, SerializableEnum.Value)}
        )
        assert len(enum_types) == 1
        self.enum = SerializableEnum(next(iter(enum_types)))

        elements_raw = [
            *[elem for e in elements if isinstance(e, EnumSet) for elem in e.elements],
            *[e for e in elements if isinstance(e, self.enum.enum)],
            *[e for e in elements if isinstance(e, SerializableEnum.Value)],
        ]
        elements_ser = [self.enum.make_value(e) for e in elements_raw]

        super().__init__(*elements_ser)

    def __contains__(self, item: E) -> bool:
        return super().__contains__(self.enum.make_value(item))

    @classmethod
    def empty(cls, enum: type[E]) -> "EnumSet[E]":
        return cls(enum)

    @classmethod
    def unbounded(cls, enum: type[E]) -> "EnumSet[E]":
        return cls(*enum)

    @override
    def serialize_pset(self) -> dict:
        return {
            "elements": [
                e.serialize() for e in sorted(self.elements, key=lambda e: e.name)
            ],
            "enum": self.enum.serialize(),
        }

    @override
    @classmethod
    def deserialize_pset(cls, data: dict):
        enum = SerializableEnum.deserialize(data["enum"])
        return cls(*(enum.deserialize_value(e) for e in data["elements"]), enum)


# Helpers ------------------------------------------------------------------------------
@overload
def as_lit(x: BoolSetLike) -> BoolSet: ...


@overload
def as_lit(x: "QuantitySetLike") -> "Quantity_Interval_Disjoint": ...


@overload
def as_lit(x: Enum) -> EnumSet: ...


def as_lit(x):
    return P_Set.from_value(x)
