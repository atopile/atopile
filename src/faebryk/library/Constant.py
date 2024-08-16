# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Generic, Self, SupportsAbs, TypeVar

from faebryk.core.core import Parameter
from faebryk.library.is_representable_by_single_value_defined import (
    is_representable_by_single_value_defined,
)
from faebryk.libs.units import Quantity

PV = TypeVar("PV")


class Constant(Generic[PV], Parameter[PV]):
    def __init__(self, value: PV) -> None:
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

    def __eq__(self, other) -> bool:
        if not isinstance(other, Parameter):
            return self.value == other

        if not isinstance(other, Constant):
            return False

        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    # comparison operators
    def __le__(self, other) -> bool:
        return other >= self.value

    def __lt__(self, other) -> bool:
        return other > self.value

    def __ge__(self, other) -> bool:
        return other <= self.value

    def __gt__(self, other) -> bool:
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
