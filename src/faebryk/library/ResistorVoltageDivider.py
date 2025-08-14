# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import R
from faebryk.libs.library import L
from faebryk.libs.sets.quantity_sets import Quantity_Interval
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

    # External interfaces
    power: F.ElectricPower
    output: F.ElectricSignal

    # Components
    r_bottom: F.Resistor
    r_top: F.Resistor

    # Variables
    v_in = L.p_field(units=P.V, domain=R.Domains.Numbers.REAL())
    v_out = L.p_field(units=P.V, domain=R.Domains.Numbers.REAL())
    max_current = L.p_field(units=P.A)
    total_resistance = L.p_field(units=P.Ω)
    ratio = L.p_field(units=P.dimensionless, within=Quantity_Interval(0.0, 1.0))

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power.hv, self.output.line)

    def __preinit__(self):
        # Connections
        self.power.hv.connect_via(
            [self.r_top, self.output.line, self.r_bottom], self.power.lv
        )

        # Short variables
        ratio = self.ratio
        r_top = self.r_top.resistance
        r_bottom = self.r_bottom.resistance
        r_total = self.total_resistance
        v_out = self.v_out
        v_in = self.v_in
        max_current = self.max_current

        # Link interface voltages
        v_out.alias_is(self.output.reference.voltage)
        v_in.alias_is(self.power.voltage)

        # Equations
        r_top.alias_is((abs(v_in) / max_current) - r_bottom)
        r_bottom.alias_is((abs(v_in) / max_current) - r_top)
        r_top.alias_is(abs(v_in - v_out) / max_current)
        r_bottom.alias_is(abs(v_out) / max_current)
        r_bottom.alias_is(r_total * ratio)
        r_top.alias_is(r_total * (1 - ratio))
        r_bottom.alias_is(v_out * r_top / (v_in - v_out))
        r_top.alias_is(r_bottom * (v_in / v_out - 1))

        # Calculate outputs
        r_total.alias_is(r_top + r_bottom)
        v_out.alias_is(v_in * r_bottom / r_total)
        v_out.alias_is(v_in * ratio)
        max_current.alias_is(abs(v_in) / r_total)
        ratio.alias_is(r_bottom / r_total)

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.output.line.add(
            F.has_net_name("VDIV_OUTPUT", level=F.has_net_name.Level.SUGGESTED)
        )
