# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import Quantity


class LDO(Module):
    class OutputType(Enum):
        FIXED = auto()
        ADJUSTABLE = auto()

    class OutputPolarity(Enum):
        POSITIVE = auto()
        NEGATIVE = auto()

    max_input_voltage: F.TBD[Quantity]
    output_voltage: F.TBD[Quantity]
    output_polarity: F.TBD[OutputPolarity]
    output_type: F.TBD[OutputType]
    output_current: F.TBD[Quantity]
    psrr: F.TBD[Quantity]
    dropout_voltage: F.TBD[Quantity]
    quiescent_current: F.TBD[Quantity]

    enable: F.ElectricLogic
    power_in: F.ElectricPower
    power_out = L.d_field(lambda: F.ElectricPower().make_source())

    def __preinit__(self):
        self.power_in.voltage.merge(self.max_input_voltage)
        self.power_out.voltage.merge(self.output_voltage)

        self.power_in.decoupled.decouple()
        self.power_out.decoupled.decouple()

        self.enable.reference.connect(self.power_in)
        # TODO: should be implemented differently (see below)
        # if self.output_polarity == self.OutputPolarity.NEGATIVE:
        #    self.power_in.hv.connect(self.power_out.hv)
        # else:
        #    self.power_in.lv.connect(self.power_out.lv)

        # LDO in & out share gnd reference
        F.ElectricLogic.connect_all_node_references(
            [self.power_in, self.power_out], gnd_only=True
        )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power_in, self.power_out)

    @L.rt_field
    def simple_value_representation(self):
        from faebryk.core.util import as_unit, as_unit_with_tolerance

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
            lambda ps: "LDO "
            + " ".join(
                [
                    as_unit_with_tolerance(ps[2], "V"),
                    as_unit(ps[3], "A"),
                    as_unit(ps[4], "dB"),
                    as_unit(ps[5], "V"),
                    f"Vin max {as_unit(ps[6], 'V')}",
                    f"Iq {as_unit(ps[7], 'A')}",
                ]
            ),
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")

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
