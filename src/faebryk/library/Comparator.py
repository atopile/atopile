# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

from faebryk.core.core import Module
from faebryk.core.util import as_unit
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_simple_value_representation_based_on_params import (
    has_simple_value_representation_based_on_params,
)
from faebryk.library.TBD import TBD


class Comparator(Module):
    class OutputType(Enum):
        Differential = auto()
        PushPull = auto()
        OpenDrain = auto()

    def __init__(self):
        super().__init__()

        class _PARAMs(self.PARAMS()):
            common_mode_rejection_ratio = TBD[float]()
            input_bias_current = TBD[float]()
            input_hysteresis_voltage = TBD[float]()
            input_offset_voltage = TBD[float]()
            propagation_delay = TBD[float]()
            output_type = TBD[Comparator.OutputType]()

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
                    self.PARAMs.common_mode_rejection_ratio,
                    self.PARAMs.input_bias_current,
                    self.PARAMs.input_hysteresis_voltage,
                    self.PARAMs.input_offset_voltage,
                    self.PARAMs.propagation_delay,
                ],
                lambda p: (
                    f"{p[0]} CMRR, {as_unit(p[1], 'A')} Ib, {as_unit(p[2], 'V')} Vhys, "
                    f"{as_unit(p[3], 'V')} Vos, {as_unit(p[4], 's')} tpd"
                ),
            )
        )
        self.add_trait(has_designator_prefix_defined("U"))
