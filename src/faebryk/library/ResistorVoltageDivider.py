# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class ResistorVoltageDivider(Module):
    """
    A voltage divider using two resistors.
    node[0] ~ resistor[1] ~ node[1] ~ resistor[2] ~ node[2]
    power.hv ~ node[0]
    power.lv ~ node[2]
    output.line ~ node[1]
    output.reference.lv ~ node[2]
    """

    r_bottom: F.Resistor
    r_top: F.Resistor
    power: F.ElectricPower
    # input: F.ElectricSignal
    output: F.ElectricSignal

    total_resistance = L.p_field(units=P.Ω)
    ratio = L.p_field(units=P.dimensionless)
    max_current = L.p_field(units=P.A)

    v_in = L.p_field(units=P.V)
    v_out = L.p_field(units=P.V)

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power.hv, self.power.lv)

    def __preinit__(self):
        # Connections
        self.power.hv.connect_via(
            [self.r_top, self.output.line, self.r_bottom], self.power.lv
        )

        # self.power.connect(self.input.reference)
        # self.power.hv.connect(self.input.line)

        # Variables
        ratio = self.ratio
        r_total = self.total_resistance
        r_top = self.r_top.resistance
        r_bottom = self.r_bottom.resistance
        v_out = self.v_out
        v_in = self.v_in
        max_current = self.max_current

        # Link variables
        v_out.alias_is(self.output.reference.voltage)
        v_in.alias_is(self.power.voltage)

        # Equations
        r_top.alias_is((v_in / max_current) - r_bottom)
        r_bottom.alias_is((v_in / max_current) - r_top)
        r_top.alias_is((v_in - v_out) / max_current)
        r_bottom.alias_is(v_out / max_current)

        # Calculate outputs
        r_total.alias_is(r_top + r_bottom)
        v_out.alias_is(v_in * r_bottom / r_total)
        max_current.alias_is(v_in / r_total)
        ratio.alias_is(r_bottom / r_total)
