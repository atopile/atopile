# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.node import Node, f_field
from faebryk.libs.sets import Range
from faebryk.libs.units import Quantity, Unit

logger = logging.getLogger(__name__)


class Parameter(Node):
    def __init__(self, unit: Unit, within: Range[Quantity]):
        super().__init__()
        if not within.is_compatible_with_unit(unit):
            raise ValueError("incompatible units")
        self.unit = unit
        self.within = within


p_field = f_field(Parameter)
