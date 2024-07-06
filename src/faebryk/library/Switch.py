# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Generic, TypeGuard, TypeVar

from faebryk.core.core import Module, ModuleInterface
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.libs.util import times

T = TypeVar("T", bound=ModuleInterface)


class _TSwitch(Generic[T], Module):
    def __init__(self, t: type[T]):
        super().__init__()
        self.t = t

    @staticmethod
    def is_instance(obj: Module, t: type[T]) -> bool:
        return isinstance(obj, _TSwitch) and issubclass(obj.t, t)


def Switch(interface_type: type[T]):
    class _Switch(_TSwitch[interface_type]):
        def __init__(self) -> None:
            super().__init__(interface_type)

            self.add_trait(has_designator_prefix_defined("SW"))
            self.add_trait(can_attach_to_footprint_symmetrically())

            class _IFs(super().IFS()):
                unnamed = times(2, interface_type)

            self.IFs = _IFs(self)
            self.add_trait(can_bridge_defined(*self.IFs.unnamed))

        @staticmethod
        def is_instance(obj: Module) -> "TypeGuard[_Switch]":
            return _TSwitch.is_instance(obj, interface_type)

    return _Switch
