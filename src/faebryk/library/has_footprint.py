# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import TYPE_CHECKING

from faebryk.core.module import Module

if TYPE_CHECKING:
    from faebryk.library.Footprint import Footprint


class has_footprint(Module.TraitT):
    @abstractmethod
    def get_footprint(self) -> "Footprint": ...
