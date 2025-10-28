# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll
import faebryk.library._F as F


class can_attach_to_footprint(fabll.Node):
    @abstractmethod
    def attach(self, footprint: F.Footprint): ...
