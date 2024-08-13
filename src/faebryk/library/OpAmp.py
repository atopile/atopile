# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.core.util import as_unit
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_pin_association_heuristic_lookup_table import (
    has_pin_association_heuristic_lookup_table,
)
from faebryk.library.has_simple_value_representation_based_on_params import (
    has_simple_value_representation_based_on_params,
)
from faebryk.library.TBD import TBD


class OpAmp(Module):
    def __init__(self):
        super().__init__()

        class _PARAMs(self.PARAMS()):
            bandwidth = TBD[float]()
            common_mode_rejection_ratio = TBD[float]()
            input_bias_current = TBD[float]()
            input_offset_voltage = TBD[float]()
            gain_bandwidth_product = TBD[float]()
            output_current = TBD[float]()
            slew_rate = TBD[float]()

        self.PARAMs = _PARAMs(self)

        class _IFs(super().IFS()):
            power = ElectricPower()
            inverting_input = Electrical()
            non_inverting_input = Electrical()
            output = Electrical()

        self.IFs = _IFs(self)

        self.add_trait(
            has_simple_value_representation_based_on_params(
                [
                    self.PARAMs.bandwidth,
                    self.PARAMs.common_mode_rejection_ratio,
                    self.PARAMs.input_bias_current,
                    self.PARAMs.input_offset_voltage,
                    self.PARAMs.gain_bandwidth_product,
                    self.PARAMs.output_current,
                    self.PARAMs.slew_rate,
                ],
                lambda p: (
                    f"{as_unit(p[0], 'Hz')} BW, {p[1]} CMRR, {as_unit(p[2], 'A')} Ib, "
                    f"{as_unit(p[3], 'V')} Vos, {as_unit(p[4], 'Hz')} GBW, "
                    f"{as_unit(p[5], 'A')} Iout, {as_unit(p[6], 'V/s')} SR"
                ),
            )
        )
        self.add_trait(
            has_pin_association_heuristic_lookup_table(
                mapping={
                    self.IFs.power.IFs.hv: ["V+", "Vcc", "Vdd"],
                    self.IFs.power.IFs.lv: ["V-", "Vee", "Vss", "GND"],
                    self.IFs.inverting_input: ["-", "IN-"],
                    self.IFs.non_inverting_input: ["+", "IN+"],
                    self.IFs.output: ["OUT"],
                },
                accept_prefix=False,
                case_sensitive=False,
            )
        )
        self.add_trait(has_designator_prefix_defined("U"))
