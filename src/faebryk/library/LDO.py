# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

from faebryk.core.core import Module
from faebryk.core.util import as_unit, as_unit_with_tolerance
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_pin_association_heuristic_lookup_table import (
    has_pin_association_heuristic_lookup_table,
)
from faebryk.library.has_simple_value_representation_based_on_params import (
    has_simple_value_representation_based_on_params,
)
from faebryk.library.TBD import TBD


class LDO(Module):
    class OutputType(Enum):
        FIXED = auto()
        ADJUSTABLE = auto()

    class OutputPolarity(Enum):
        POSITIVE = auto()
        NEGATIVE = auto()

    @classmethod
    def PARAMS(cls):
        class _PARAMs(super().PARAMS()):
            max_input_voltage = TBD[float]()
            output_voltage = TBD[float]()
            output_polarity = TBD[LDO.OutputPolarity]()
            output_type = TBD[LDO.OutputType]()
            output_current = TBD[float]()
            psrr = TBD[float]()
            dropout_voltage = TBD[float]()
            quiescent_current = TBD[float]()

        return _PARAMs

    def __init__(self):
        super().__init__()

        self.PARAMs = self.PARAMS()(self)

        class _IFs(super().IFS()):
            enable = ElectricLogic()
            power_in = ElectricPower()
            power_out = ElectricPower()

        self.IFs = _IFs(self)

        self.IFs.power_in.PARAMs.voltage.merge(self.PARAMs.max_input_voltage)
        self.IFs.power_out.PARAMs.voltage.merge(self.PARAMs.output_voltage)

        self.IFs.power_in.get_trait(can_be_decoupled).decouple()
        self.IFs.power_out.get_trait(can_be_decoupled).decouple()

        self.IFs.enable.IFs.reference.connect(self.IFs.power_in)
        if self.PARAMs.output_polarity == self.OutputPolarity.POSITIVE:
            self.IFs.power_in.IFs.lv.connect(self.IFs.power_out.IFs.lv)
        else:
            self.IFs.power_in.IFs.hv.connect(self.IFs.power_out.IFs.hv)

        self.add_trait(can_bridge_defined(self.IFs.power_in, self.IFs.power_out))
        self.add_trait(
            has_simple_value_representation_based_on_params(
                (
                    self.PARAMs.output_polarity,
                    self.PARAMs.output_type,
                    self.PARAMs.output_voltage,
                    self.PARAMs.output_current,
                    self.PARAMs.psrr,
                    self.PARAMs.dropout_voltage,
                    self.PARAMs.max_input_voltage,
                    self.PARAMs.quiescent_current,
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
        )
        self.add_trait(has_designator_prefix_defined("U"))
        self.add_trait(
            has_pin_association_heuristic_lookup_table(
                mapping={
                    self.IFs.power_in.IFs.hv: ["Vin", "Vi", "in"],
                    self.IFs.power_out.IFs.hv: ["Vout", "Vo", "out"],
                    self.IFs.power_in.IFs.lv: ["GND", "V-"],
                    self.IFs.enable.IFs.signal: ["EN", "Enable"],
                },
                accept_prefix=False,
                case_sensitive=False,
            )
        )
