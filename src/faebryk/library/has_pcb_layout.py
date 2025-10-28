# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll


class has_pcb_layout(fabll.Node):
    @abstractmethod
    def apply(self): ...
