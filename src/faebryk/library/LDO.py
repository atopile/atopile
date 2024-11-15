# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import math
from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import assert_once, join_if_non_empty


class LDO(Module):
    @assert_once
    def enable_output(self):
        self.enable.set(True)

    class OutputType(Enum):
        FIXED = auto()
        ADJUSTABLE = auto()

    class OutputPolarity(Enum):
        POSITIVE = auto()
        NEGATIVE = auto()

    max_input_voltage: F.TBD
    output_voltage: F.TBD
    output_polarity: F.TBD
    output_type: F.TBD
    output_current: F.TBD
    psrr: F.TBD
    dropout_voltage: F.TBD
    quiescent_current: F.TBD

    enable: F.ElectricLogic
    power_in: F.ElectricPower
    power_out = L.d_field(lambda: F.ElectricPower().make_source())

    def __preinit__(self):
        self.max_input_voltage.merge(F.Range(self.power_in.voltage, math.inf * P.V))
        self.power_out.voltage.merge(self.output_voltage)

        self.enable.reference.connect(self.power_in)
        # TODO: should be implemented differently (see below)
        # if self.output_polarity == self.OutputPolarity.NEGATIVE:
        #    self.power_in.hv.connect(self.power_out.hv)
        # else:
        #    self.power_in.lv.connect(self.power_out.lv)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        )

    @L.rt_field
    def decoupled(self):
        return F.can_be_decoupled_rails(self.power_in, self.power_out)

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power_in, self.power_out)

    @L.rt_field
    def simple_value_representation(self):
        return F.has_simple_value_representation_based_on_params(
            (
                self.output_polarity,
                self.output_type,
                self.output_voltage,
                self.output_current,
                self.psrr,
                self.dropout_voltage,
                self.max_input_voltage,
                self.quiescent_current,
            ),
            lambda output_polarity,
            output_type,
            output_voltage,
            output_current,
            psrr,
            dropout_voltage,
            max_input_voltage,
            quiescent_current: "LDO "
            + join_if_non_empty(
                " ",
                output_voltage.as_unit_with_tolerance("V"),
                output_current.as_unit("A"),
                psrr.as_unit("dB"),
                dropout_voltage.as_unit("V"),
                f"Vin max {max_input_voltage.as_unit("V")}",
                f"Iq {quiescent_current.as_unit("A")}",
            ),
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power_in.hv: ["Vin", "Vi", "in"],
                self.power_out.hv: ["Vout", "Vo", "out"],
                self.power_in.lv: ["GND", "V-"],
                self.enable.signal: ["EN", "Enable"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )
