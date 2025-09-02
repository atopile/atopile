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
        #pragma experiment("BRIDGE_CONNECT")
        import SWD, ElectricPower, Resistor, ElectricLogic

        module UsageExample:
            swd = new SWD

            # Connect power reference for logic levels
            power_3v3 = new ElectricPower
            assert power_3v3.voltage within 3.3V +/- 5%
            swd.reference_shim ~ power_3v3

            # Connect to microcontroller GPIO pins
            mcu_gpio0 = new ElectricLogic
            mcu_gpio1 = new ElectricLogic
            mcu_gpio2 = new ElectricLogic
            mcu_reset = new ElectricLogic
            
            mcu_gpio0 ~ swd.clk
            mcu_gpio1 ~ swd.dio
            mcu_gpio2 ~ swd.swo
            mcu_reset ~ swd.reset

            # Optional pullup resistors for robust operation
            reset_pullup = new Resistor
            reset_pullup.resistance = 10kohm +/- 5%
            swd.reset.line ~> reset_pullup ~> swd.reset.reference.hv
        """,
        language=F.has_usage_example.Language.ato,
    )
