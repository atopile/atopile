# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class ResistorVoltageDivider(Module):
    resistor = L.list_field(2, F.Resistor)

    node = L.list_field(3, F.Electrical)

    ratio = L.p_field(units=P.dimensionless)
    max_current = L.p_field(units=P.A)

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.node[0], self.node[1])

    def __preinit__(self):
        self.node[0].connect_via(self.resistor[0], self.node[1])
        self.node[1].connect_via(self.resistor[1], self.node[2])
