# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll
from faebryk.core.parameter import Parameter


class has_capacitance(fabll.Node):
    @abstractmethod
    def get_capacitance(self) -> Parameter: ...
