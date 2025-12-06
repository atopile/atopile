# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class ResistorVoltageDivider(fabll.Node):
    """
    A voltage divider using two resistors.
    node[0] ~ resistor[1] ~ node[1] ~ resistor[2] ~ node[2]
    power.hv ~ node[0]
    power.lv ~ node[2]
    output.line ~ node[1]
    output.reference.lv ~ node[2]
    """

    # External interfaces
    power = F.ElectricPower.MakeChild()
    output = F.ElectricSignal.MakeChild()

    # Components
    r_bottom = F.Resistor.MakeChild()
    r_top = F.Resistor.MakeChild()

    # Variables
    v_in = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    v_out = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    max_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    total_resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)
    ratio = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    # _can_bridge = fabll.Traits.MakeEdge(
    #     F.can_bridge.MakeChild(in_=power.get().hv, out_=output.get().line)
    # )

    # def __preinit__(self):
    #     # Connections
    #     self.power.hv.connect_via(
    #         [self.r_top, self.output.line, self.r_bottom], self.power.lv
    #     )

    #     # Short variables
    #     ratio = self.ratio
    #     r_top = self.r_top.resistance
    #     r_bottom = self.r_bottom.resistance
    #     r_total = self.total_resistance
    #     v_out = self.v_out
    #     v_in = self.v_in
    #     max_current = self.max_current

    #     # Link interface voltages
    #     v_out.alias_is(self.output.reference.voltage)
    #     v_in.alias_is(self.power.voltage)

    #     # Equations
    #     r_top.alias_is((abs(v_in) / max_current) - r_bottom)
    #     r_bottom.alias_is((abs(v_in) / max_current) - r_top)
    #     r_top.alias_is(abs(v_in - v_out) / max_current)
    #     r_bottom.alias_is(abs(v_out) / max_current)
    #     r_bottom.alias_is(r_total * ratio)
    #     r_top.alias_is(r_total * (1 - ratio))
    #     r_bottom.alias_is(v_out * r_top / (v_in - v_out))
    #     r_top.alias_is(r_bottom * (v_in / v_out - 1))

    #     # Calculate outputs
    #     r_total.alias_is(r_top + r_bottom)
    #     v_out.alias_is(v_in * r_bottom / r_total)
    #     v_out.alias_is(v_in * ratio)
    #     max_current.alias_is(abs(v_in) / r_total)
    #     ratio.alias_is(r_bottom / r_total)

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.output.get().line.get(), trait=F.has_net_name
        ).setup(name="VDIV_OUTPUT", level=F.has_net_name.Level.SUGGESTED)
