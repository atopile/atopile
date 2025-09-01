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

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.clk.line.add(
            F.has_net_name("SWD_CLK", level=F.has_net_name.Level.SUGGESTED)
        )
        self.dio.line.add(
            F.has_net_name("SWD_DIO", level=F.has_net_name.Level.SUGGESTED)
        )
        self.swo.line.add(
            F.has_net_name("SWD_SWO", level=F.has_net_name.Level.SUGGESTED)
        )
        self.reset.line.add(
            F.has_net_name("SWD_RESET", level=F.has_net_name.Level.SUGGESTED)
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import SWD, ElectricPower, Resistor

        from "x/y/y.ato" import SomeMCU
        from "a/b/c.ato" import SomeDebugger

        swd = new SWD
        microcontroller = new SomeMCU
        debugger = new SomeDebugger

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        swd.reference_shim ~ power_3v3

        # Connect to microcontroller specific pins (mcu has no SWD interface)
        microcontroller.gpio[0] ~ swd.clk
        microcontroller.gpio[1] ~ swd.dio
        microcontroller.gpio[2] ~ swd.swo
        microcontroller.reset ~ swd.reset

        # Connect to debugger (has SWD interface)
        debugger.swd ~ swd

        # Optional pullup resistors for robust operation
        # mostly only on target side, not debugger side
        reset_pullup = new Resistor
        reset_pullup.resistance = 10kohm +/- 5%
        swd.reset.line ~> reset_pullup ~> swd.reset.reference.hv

        # SWD is commonly used for ARM Cortex-M debugging and programming
        """,
        language=F.has_usage_example.Language.ato,
    )
