# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TypeVar

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


class _TSwitch(Module):
    ...


def Switch(interface_type: type[T]):
    class _Switch(_TSwitch):
        def __init__(self) -> None:
            super().__init__()

            self.add_trait(has_designator_prefix_defined("SW"))
            self.add_trait(can_attach_to_footprint_symmetrically())

            class _IFs(super().IFS()):
                unnamed = times(2, interface_type)

            self.IFs = _IFs(self)
            self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    return _Switch
