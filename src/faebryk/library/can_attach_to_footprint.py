# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.library._F as F
from faebryk.core.module import Module


class can_attach_to_footprint(Module.TraitT):
    @abstractmethod
    def attach(self, footprint: F.Footprint): ...
