# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import Self, SupportsAbs

import numpy as np

from faebryk.core.parameter import Parameter, _resolved
from faebryk.libs.units import Quantity, UnitsContainer, to_si_str
from faebryk.libs.util import once


class Constant(Parameter):
    type LIT_OR_PARAM = Parameter.LIT_OR_PARAM

    def __init__(self, value: LIT_OR_PARAM) -> None:
        super().__init__()
        self.value = value

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
        if self is other:
            return True

        if not isinstance(other, Constant):
            return False

        try:
            return np.allclose(self.value, other.value)
        except (TypeError, np.exceptions.DTypePromotionError):
            ...

        return self.value == other.value

    @once
    def _hash_val(self):
        # assert not isinstance(self.value, Parameter)
        return hash(self.value)

    def __hash__(self) -> int:
        if isinstance(self.value, Parameter):
            return hash(self.value)
        return self._hash_val()

    # comparison operators
    @_resolved
    def __le__(self, other) -> bool:
        if isinstance(other, Constant):
            if self == other:
                return True
            return self.value <= other.value
        return other >= self.value

    @_resolved
    def __lt__(self, other) -> bool:
        if isinstance(other, Constant):
            if self == other:
                return False
            return self.value < other.value
        return other > self.value

    @_resolved
    def __ge__(self, other) -> bool:
        if isinstance(other, Constant):
            if self == other:
                return True
            return self.value >= other.value
        return other <= self.value

    @_resolved
    def __gt__(self, other) -> bool:
        if isinstance(other, Constant):
            if self == other:
                return False
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
    def __contains__(self, other: Parameter) -> bool:
        if not isinstance(other, Constant):
            return False
        return other.value == self.value

    def try_compress(self) -> Parameter:
        if isinstance(self.value, Parameter):
            return self.value
        return super().try_compress()

    def _max(self):
        return self.value

    def _as_unit(self, unit: UnitsContainer, base: int, required: bool) -> str:
        return to_si_str(self.value, unit)

    def _enum_parameter_representation(self, required: bool) -> str:
        return self.value.name if isinstance(self.value, Enum) else str(self.value)
