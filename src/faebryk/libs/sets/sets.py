# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from collections.abc import Iterable, Iterator
from typing import Any, Protocol, runtime_checkable

from faebryk.libs.units import Unit


# Protocols ----------------------------------------------------------------------------
@runtime_checkable
class P_Set[T](Protocol):
    def is_empty(self) -> bool: ...

    def __bool__(self) -> bool:
        raise Exception("don't use bool to check for emptiness, use is_empty()")

    def __contains__(self, item: T) -> bool: ...


class P_IterableSet[T, IterT](P_Set[T], Iterable[IterT], Protocol): ...


class P_UnitSet[T](P_Set[T], Protocol):
    units: Unit


class P_IterableUnitSet[T, IterT](P_UnitSet[T], Iterable[IterT], Protocol): ...


class PlainSet[U](P_IterableSet[U, U]):
    def __init__(self, *elements: U):
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

    def __iter__(self) -> Iterator[U]:
        return self.elements.__iter__()
