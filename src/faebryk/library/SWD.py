# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class SWD(ModuleInterface):
    clk: F.ElectricLogic
    dio: F.ElectricLogic
    swo: F.ElectricLogic
    reset: F.ElectricLogic

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import SWD, ElectricPower, Resistor

        swd = new SWD

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        swd.clk.reference ~ power_3v3
        swd.dio.reference ~ power_3v3
        swd.swo.reference ~ power_3v3
        swd.reset.reference ~ power_3v3

        # Connect to microcontroller SWD interface
        microcontroller.swd_clk ~ swd.clk.line
        microcontroller.swd_dio ~ swd.dio.line
        microcontroller.swd_swo ~ swd.swo.line
        microcontroller.reset_n ~ swd.reset.line

        # Connect to debugger/programmer
        debugger.swd ~ swd

        # Optional pullup resistors for robust operation
        reset_pullup = new Resistor
        reset_pullup.resistance = 10kohm +/- 5%
        swd.reset.line ~> reset_pullup ~> power_3v3.hv

        # SWD is commonly used for ARM Cortex-M debugging and programming
        """,
        language=F.has_usage_example.Language.ato,
    )
