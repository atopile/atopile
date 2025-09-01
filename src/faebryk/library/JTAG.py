# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class JTAG(ModuleInterface):
    dbgrq: F.ElectricLogic
    tdo: F.ElectricLogic
    tdi: F.ElectricLogic
    tms: F.ElectricLogic
    tck: F.ElectricLogic
    rtck: F.ElectricLogic
    n_trst: F.ElectricLogic
    n_reset: F.ElectricLogic
    vtref: F.ElectricPower

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.dbgrq.line.add(
            F.has_net_name("DBGRQ", level=F.has_net_name.Level.SUGGESTED)
        )
        self.tdo.line.add(F.has_net_name("TDO", level=F.has_net_name.Level.SUGGESTED))
        self.tdi.line.add(F.has_net_name("TDI", level=F.has_net_name.Level.SUGGESTED))
        self.tms.line.add(F.has_net_name("TMS", level=F.has_net_name.Level.SUGGESTED))
        self.tck.line.add(F.has_net_name("TCK", level=F.has_net_name.Level.SUGGESTED))
        self.rtck.line.add(F.has_net_name("RTCK", level=F.has_net_name.Level.SUGGESTED))
        self.n_trst.line.add(
            F.has_net_name("N_TRST", level=F.has_net_name.Level.SUGGESTED)
        )
        self.n_reset.line.add(
            F.has_net_name("N_RESET", level=F.has_net_name.Level.SUGGESTED)
        )
        self.vtref.add(F.has_net_name("VTREF", level=F.has_net_name.Level.SUGGESTED))

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import JTAG, ElectricPower, Resistor

        from "x/y/y.ato" import SomeMCU
        from "a/b/c.ato" import SomeDebugger

        jtag = new JTAG
        microcontroller = new SomeMCU
        debugger = new SomeDebugger

        # Connect voltage reference for all logic signals
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        jtag.vtref ~ power_3v3

        # Connect to microcontroller specific pins (mcu has no JTAG interface)
        microcontroller.gpio[0] ~ jtag.tdo
        microcontroller.gpio[1] ~ jtag.tdi
        microcontroller.gpio[2] ~ jtag.tms
        microcontroller.gpio[3] ~ jtag.tck
        microcontroller.reset ~ jtag.n_reset

        # Connect to JTAG debugger (has JTAG interface)
        debugger.jtag ~ jtag

        # Pullup resistors for reset lines
        # mostly only on target side, not debugger side
        trst_pullup = new Resistor
        reset_pullup = new Resistor
        trst_pullup.resistance = 10kohm +/- 5%
        reset_pullup.resistance = 10kohm +/- 5%
        jtag.n_trst.line ~> trst_pullup ~> jtag.n_trst.reference.hv
        jtag.n_reset.line ~> reset_pullup ~> jtag.n_reset.reference.hv
        """,
        language=F.has_usage_example.Language.ato,
    )
