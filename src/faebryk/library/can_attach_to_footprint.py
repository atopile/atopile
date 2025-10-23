# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.library._F as F
import faebryk.core.node as fabll


class can_attach_to_footprint(Module.TraitT):
    @abstractmethod
    def attach(self, footprint: F.Footprint): ...
