# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class VoltageDivider(Module):
    resistor = L.list_field(2, F.Resistor)

    power_in: F.ElectricPower
    power_out: F.ElectricPower

    total_resistance = L.p_field(units=P.Ω)
    ratio = L.p_field(units=P.dimensionless)
    max_current = L.p_field(units=P.A)

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power_in, self.power_out)

    def __preinit__(self):
        self.power_in.hv.connect_via(self.resistor[0], self.power_out.hv)
        self.power_out.hv.connect_via(self.resistor[1], self.power_out.lv)
        self.power_in.lv.connect(self.power_out.lv)

        self.power_in.make_sink()
        self.power_out.make_source()

        # maximum sinkable current
        self.max_current.alias_is(self.power_out.max_current)
        self.ratio.alias_is(self.resistor[0].resistance / self.total_resistance)
        self.total_resistance.alias_is(
            self.resistor[0].resistance + self.resistor[1].resistance
        )
        # help solver
        # TODO: can be removed when solver can take hints
        self.resistor[0].resistance.alias_is(
            self.total_resistance - self.resistor[1].resistance
        )
        self.resistor[1].resistance.alias_is(
            self.total_resistance - self.resistor[0].resistance
        )
        # TODO: calculate maximum power dissipation of resistors
