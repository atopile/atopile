# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll


class has_simple_value_representation(fabll.Node):
    @abstractmethod
    def get_value(self) -> str: ...
