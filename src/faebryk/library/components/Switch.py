# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TypeGuard

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.util import once


class _TSwitch(Module):
    T = ModuleInterface

    def __init__(self, t: type[T]):
        super().__init__()
        self.t = t

    @staticmethod
    def is_instance(obj: Module, t: type[T]) -> bool:
        return isinstance(obj, _TSwitch) and issubclass(obj.t, t)


@once  # This means we can use a normal "isinstance" to test for them
def Switch[T: ModuleInterface](interface_type: type[T]):
    class _Switch(_TSwitch):
        def __init__(self) -> None:
            super().__init__(interface_type)

        designator_prefix = L.f_field(F.has_designator_prefix)(
            F.has_designator_prefix.Prefix.S
        )
        attach_to_footprint: F.can_attach_to_footprint_symmetrically

        unnamed = L.list_field(2, interface_type)

        @L.rt_field
        def can_bridge(self):
            return F.can_bridge_defined(*self.unnamed)

        @staticmethod
        def is_instance(obj: Module) -> "TypeGuard[_Switch]":
            return _TSwitch.is_instance(obj, interface_type)

    return _Switch
