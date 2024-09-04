# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Iterable, Self

import faebryk.library._F as F
from faebryk.core.parameter import Parameter, _resolved
from faebryk.libs.units import UnitsContainer


class Set[PV](Parameter[PV], Parameter[PV].SupportsSetOps):
    type LIT_OR_PARAM = Parameter[PV].LIT_OR_PARAM

    def __init__(self, params: Iterable[Parameter[LIT_OR_PARAM]]) -> None:
        super().__init__()

        # make primitves to constants
        self._params = set(
            p if isinstance(p, Parameter) else F.Constant(p) for p in params
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

    @_resolved
    def __contains__(self, other: Parameter[PV]) -> bool:
        def nested_in(p):
            if other == p:
                return True
            if isinstance(p, F.Range):
                return other in p
            return False

        return any(nested_in(p) for p in self.params)

    def try_compress(self) -> Parameter[PV]:
        # compress into constant if possible
        if len(set(map(id, self.params))) == 1:
            return Parameter.from_literal(next(iter(self.params)))
        return super().try_compress()

    def _max(self):
        return max(p.get_max() for p in self.params)

    def _as_unit(self, unit: UnitsContainer, base: int, required: bool) -> str:
        return (
            "Set("
            + ", ".join(x.as_unit(unit, required=True) for x in self.params)
            + ")"
        )

    def _as_unit_with_tolerance(
        self, unit: UnitsContainer, base: int, required: bool
    ) -> str:
        return (
            "Set("
            + ", ".join(
                x.as_unit_with_tolerance(unit, base, required) for x in self.params
            )
            + ")"
        )

    def _enum_parameter_representation(self, required: bool) -> str:
        return (
            "Set("
            + ", ".join(p.enum_parameter_representation(required) for p in self.params)
            + ")"
        )
