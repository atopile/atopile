# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.util import times


class ElectricLogicGate(F.LogicGate):
    @L.rt_field
    def inputs(self):
        return times(self._input_cnt, F.ElectricLogic)

    @L.rt_field
    def outputs(self):
        return times(self._output_cnt, F.ElectricLogic)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import ElectricLogicGate, ElectricLogic, ElectricPower

        module UsageExample:
            # Power supply for the logic gate
            power_3v3 = new ElectricPower
            power_3v3.voltage = 3.3V +/- 5%
            
            # Input and output signals
            input_a = new ElectricLogic
            input_b = new ElectricLogic
            output_signal = new ElectricLogic
            
            # Connect power references
            input_a.reference ~ power_3v3
            input_b.reference ~ power_3v3
            output_signal.reference ~ power_3v3
            
            # Note: ElectricLogicGate requires constructor arguments
            # This example shows the interface connections
            # Actual usage would require proper instantiation with 
            # input_cnt, output_cnt, and functions parameters
        """,
        language=F.has_usage_example.Language.ato,
    )
