# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Generic, Iterable, Self, TypeVar

from faebryk.core.core import Parameter

PV = TypeVar("PV")


class Set(Generic[PV], Parameter[PV]):
    def __init__(self, params: Iterable[Parameter]) -> None:
        super().__init__()
        self.params = Set.flatten(set(params))

    @staticmethod
    def flatten(params: set[Parameter]) -> set[Parameter]:
        return set(p for p in params if not isinstance(p, Set)) | set(
            x for p in params if isinstance(p, Set) for x in Set.flatten(p.params)
        )

    def __str__(self) -> str:
        return super().__str__() + f"({self.params})"

    def __repr__(self):
        return super().__repr__() + f"({self.params!r})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Set):
            return False

        return self.params == other.params

    def __hash__(self) -> int:
        return sum(hash(p) for p in self.params)

    # comparison operators
    def __le__(self, other) -> bool:
        return all(p <= other for p in self.params)

    def __lt__(self, other) -> bool:
        return all(p < other for p in self.params)

    def __ge__(self, other) -> bool:
        return all(p >= other for p in self.params)

    def __gt__(self, other) -> bool:
        return all(p > other for p in self.params)

    def copy(self) -> Self:
        return type(self)(self.params)
