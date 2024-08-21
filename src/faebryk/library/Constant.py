# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self, SupportsAbs

from faebryk.core.core import Parameter, _resolved
from faebryk.library.is_representable_by_single_value_defined import (
    is_representable_by_single_value_defined,
)
from faebryk.libs.units import Quantity


class Constant[PV](Parameter[PV], Parameter[PV].SupportsSetOps):
    type LIT_OR_PARAM = Parameter[PV].LIT_OR_PARAM

    def __init__(self, value: LIT_OR_PARAM) -> None:
        super().__init__()
        self.value = value
        self.add_trait(is_representable_by_single_value_defined(self.value))

    def _pretty_val(self):
        val = repr(self.value)
        # TODO
        if isinstance(self.value, Quantity):
            val = f"{self.value:.2f#~P}"
        return val

    def __str__(self) -> str:
        return super().__str__() + f"({self._pretty_val()})"

    def __repr__(self):
        return super().__repr__() + f"({self._pretty_val()})"

    @_resolved
    def __eq__(self, other) -> bool:
        if not isinstance(other, Constant):
            return False

        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    # comparison operators
    @_resolved
    def __le__(self, other) -> bool:
        if isinstance(other, Constant):
            return self.value <= other.value
        return other >= self.value

    @_resolved
    def __lt__(self, other) -> bool:
        if isinstance(other, Constant):
            return self.value < other.value
        return other > self.value

    @_resolved
    def __ge__(self, other) -> bool:
        if isinstance(other, Constant):
            return self.value >= other.value
        return other <= self.value

    @_resolved
    def __gt__(self, other) -> bool:
        if isinstance(other, Constant):
            return self.value > other.value
        return other < self.value

    def __abs__(self):
        assert isinstance(self.value, SupportsAbs)
        return Constant(abs(self.value))

    def __format__(self, format_spec):
        return f"{super().__str__()}({format(self.value, format_spec)})"

    def copy(self) -> Self:
        return type(self)(self.value)

    def unpack(self):
        if isinstance(self.value, Constant):
            return self.value.unpack()

        return self.value

    def __int__(self):
        return int(self.value)

    @_resolved
    def __contains__(self, other: Parameter[PV]) -> bool:
        if not isinstance(other, Constant):
            return False
        return other.value == self.value

    def try_compress(self) -> Parameter[PV]:
        if isinstance(self.value, Parameter):
            return self.value
        return super().try_compress()
