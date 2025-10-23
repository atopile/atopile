# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import TYPE_CHECKING

import faebryk.core.node as fabll

if TYPE_CHECKING:
    from faebryk.library.Pad import Pad


class has_linked_pad(ModuleInterface.TraitT):
    @abstractmethod
    def get_pads(self) -> set["Pad"]: ...
