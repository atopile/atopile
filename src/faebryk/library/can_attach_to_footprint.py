# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ModuleTrait
from faebryk.library.Footprint import Footprint


class can_attach_to_footprint(ModuleTrait):
    @abstractmethod
    def attach(self, footprint: Footprint): ...
