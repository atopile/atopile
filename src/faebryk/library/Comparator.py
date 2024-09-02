# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import Quantity


class Comparator(Module):
    class OutputType(Enum):
        Differential = auto()
        PushPull = auto()
        OpenDrain = auto()

    common_mode_rejection_ratio: F.TBD[Quantity]
    input_bias_current: F.TBD[Quantity]
    input_hysteresis_voltage: F.TBD[Quantity]
    input_offset_voltage: F.TBD[Quantity]
    propagation_delay: F.TBD[Quantity]
    output_type: F.TBD[OutputType]

    power: F.ElectricPower
    inverting_input: F.Electrical
    non_inverting_input: F.Electrical
    output: F.Electrical

    @L.rt_field
    def simple_value_representation(self):
        from faebryk.core.util import as_unit

        return F.has_simple_value_representation_based_on_params(
            [
                self.common_mode_rejection_ratio,
                self.input_bias_current,
                self.input_hysteresis_voltage,
                self.input_offset_voltage,
                self.propagation_delay,
            ],
            lambda p: (
                f"{p[0]} CMRR, {as_unit(p[1], 'A')} Ib, {as_unit(p[2], 'V')} Vhys, "
                f"{as_unit(p[3], 'V')} Vos, {as_unit(p[4], 's')} tpd"
            ),
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")
