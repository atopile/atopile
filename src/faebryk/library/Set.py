# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Iterable, Self

from faebryk.core.core import Parameter


class Set[PV](Parameter[PV]):
    def __init__(self, params: Iterable[Parameter[PV] | PV]) -> None:
        from faebryk.library.Constant import Constant

        super().__init__()

        # make primitves to constants
        self._params = set(
            p if isinstance(p, Parameter) else Constant(p) for p in params
        )

    @staticmethod
    def _flatten(params: set[Parameter[PV]]) -> set[Parameter[PV]]:
        param_set = set(
            p for p in params if not isinstance(p, Set) and isinstance(p, Parameter)
        )
        set_set = set(x for p in params if isinstance(p, Set) for x in p.params)

        return param_set | set_set

    def flat(self) -> set[Parameter[PV]]:
        return Set._flatten(self._params)

    @property
    def params(self) -> set[Parameter[PV]]:
        return self.flat()

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

    def __contains__(self, other: PV | Parameter[PV]) -> bool:
        from faebryk.library.Range import Range

        def nested_in(p):
            if other == p:
                return True
            if isinstance(p, Range):
                return other in p
            return False

        return any(nested_in(p) for p in self.params)
