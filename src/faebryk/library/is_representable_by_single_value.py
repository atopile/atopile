# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll


class is_representable_by_single_value(fabll.Node):
    @abstractmethod
    def get_single_representing_value(self): ...
