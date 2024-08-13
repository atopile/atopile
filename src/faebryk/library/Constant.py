# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Generic, SupportsAbs, TypeVar

from faebryk.core.core import Parameter
from faebryk.library.is_representable_by_single_value_defined import (
    is_representable_by_single_value_defined,
)

PV = TypeVar("PV")


class Constant(Generic[PV], Parameter[PV]):
    def __init__(self, value: PV) -> None:
        super().__init__()
        self.value = value
        self.add_trait(is_representable_by_single_value_defined(self.value))

    def __str__(self) -> str:
        return super().__str__() + f"({self.value})"

    def __repr__(self):
        return super().__repr__() + f"({self.value})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Constant):
            return False

        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    # comparison operators
    def __le__(self, other) -> bool:
        return self.value <= other

    def __lt__(self, other) -> bool:
        return self.value < other

    def __ge__(self, other) -> bool:
        return self.value >= other

    def __gt__(self, other) -> bool:
        return self.value > other

    def __abs__(self):
        assert isinstance(self.value, SupportsAbs)
        return Constant(abs(self.value))

    def __format__(self, format_spec):
        return f"{super().__str__()}({format(self.value, format_spec)})"
