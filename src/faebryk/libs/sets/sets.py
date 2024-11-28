# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from collections.abc import Iterable, Iterator
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from faebryk.libs.units import Unit, dimensionless


# Protocols ----------------------------------------------------------------------------
@runtime_checkable
class P_Set[T](Protocol):
    def is_empty(self) -> bool: ...

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
        if isinstance(value, PlainSet):
            return value
        return PlainSet(value)

    def is_subset_of(self, other: "P_Set[T]") -> bool: ...

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


class P_IterableSet[T, IterT](P_Set[T], Iterable[IterT], Protocol): ...


class P_UnitSet[T](P_Set[T], Protocol):
    units: Unit


class P_IterableUnitSet[T, IterT](P_UnitSet[T], Iterable[IterT], Protocol): ...


class PlainSet[U](P_IterableUnitSet[U, U]):
    def __init__(self, *elements: U):
        self.units = dimensionless
        self.elements = set(elements)

    def is_empty(self) -> bool:
        return len(self.elements) == 0

    def __contains__(self, item: U) -> bool:
        return item in self.elements

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, PlainSet):
            return False
        return self.elements == value.elements

    def __hash__(self) -> int:
        return sum(hash(e) for e in self.elements)

    def __repr__(self) -> str:
        return f"PlainSet({', '.join(repr(e) for e in self.elements)})"

    def __str__(self) -> str:
        # TODO move enum stuff to new EnumSet
        return f"{{{', '.join(str(e) if not isinstance(e, Enum) else f'{e.name}' for e in self.elements)}}}"

    def __iter__(self) -> Iterator[U]:
        return iter(self.elements)

    def op_intersection(self, other: "PlainSet[U]") -> "PlainSet[U]":
        return PlainSet(*(self.elements & other.elements))

    def is_subset_of(self, other: "PlainSet[U]") -> bool:
        return self.elements.issubset(other.elements)

    def __and__(self, other: "PlainSet[U]") -> "PlainSet[U]":
        return self.op_intersection(other)

    def is_single_element(self) -> bool:
        return len(self.elements) == 1


type BoolSetLike_ = bool | BoolSet


# TODO think about inheriting from plainset
class BoolSet(P_Set[bool]):
    def __init__(self, *values: BoolSetLike_):
        assert all(isinstance(v, (bool, BoolSet)) for v in values)
        # flatten
        self.values = frozenset(
            {v for v in values if isinstance(v, bool)}
            | {v for vb in values if isinstance(vb, BoolSet) for v in vb.values}
        )

    @staticmethod
    def from_value(value: BoolSetLike_) -> "BoolSet":
        if isinstance(value, BoolSet):
            return value
        return BoolSet(value)

    def __contains__(self, item: BoolSetLike_) -> bool:
        return all(o_v in self.values for o_v in BoolSet.from_value(item).values)

    def is_empty(self) -> bool:
        return not len(self.values)

    def op_intersection(self, other: BoolSetLike_) -> "BoolSet":
        return BoolSet(*(self.values & BoolSet.from_value(other).values))

    def op_not(self) -> "BoolSet":
        return BoolSet(*(not v for v in self.values))

    def op_and(self, other: BoolSetLike_) -> "BoolSet":
        return BoolSet(
            *[
                v and o_v
                for v in self.values
                for o_v in BoolSet.from_value(other).values
            ]
        )

    def op_or(self, other: BoolSetLike_) -> "BoolSet":
        return BoolSet(
            *[v or o_v for v in self.values for o_v in BoolSet.from_value(other).values]
        )

    def __eq__(self, value: Any) -> bool:
        if value is None:
            return False
        if not isinstance(value, BoolSetLike):
            return False
        return self.values == BoolSet.from_value(value).values

    def is_subset_of(self, other: BoolSetLike_) -> bool:
        other_b = BoolSet.from_value(other)
        return self.values.issubset(other_b.values)

    def __hash__(self) -> int:
        return hash(self.values)

    def __repr__(self) -> str:
        return f"BoolSet({', '.join(repr(v) for v in self.values)})"

    # TODO rethink this
    def __and__(self, other: BoolSetLike_) -> "BoolSet":
        return self.op_intersection(other)

    def is_single_element(self) -> bool:
        return len(self.values) == 1


BoolSetLike = bool | BoolSet
