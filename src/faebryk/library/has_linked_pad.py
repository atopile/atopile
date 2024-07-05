# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import (
    ModuleInterfaceTrait,
)
from faebryk.library.Pad import Pad


class has_linked_pad(ModuleInterfaceTrait):
    @abstractmethod
    def get_pad(self) -> Pad: ...
