# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class ResistorArray(Module):
    resistance = L.p_field(units=P.ohm)
    rated_power = L.p_field(units=P.W)
    rated_voltage = L.p_field(units=P.V)

    @L.rt_field
    def resistors(self):
        return times(self._resistor_count, F.Resistor)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.R
    )

    def __init__(self, resistor_count: int = 4):
        super().__init__()
        self._resistor_count = resistor_count

    def __preinit__(self):
        for resistor in self.resistors:
            resistor.resistance = self.resistance
            resistor.max_power = self.rated_power
            resistor.max_voltage = self.rated_voltage
