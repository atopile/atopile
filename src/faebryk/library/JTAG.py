# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class JTAG(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    dbgrq = F.ElectricLogic.MakeChild()
    tdo = F.ElectricLogic.MakeChild()
    tdi = F.ElectricLogic.MakeChild()
    tms = F.ElectricLogic.MakeChild()
    tck = F.ElectricLogic.MakeChild()
    rtck = F.ElectricLogic.MakeChild()
    n_trst = F.ElectricLogic.MakeChild()
    n_reset = F.ElectricLogic.MakeChild()
    vtref = F.ElectricPower.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.dbgrq.get(), trait=F.has_net_name_suggestion
        ).setup(name="DBGRQ", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.tdo.get(), trait=F.has_net_name_suggestion
        ).setup(name="TDO", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.tdi.get(), trait=F.has_net_name_suggestion
        ).setup(name="TDI", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.tms.get(), trait=F.has_net_name_suggestion
        ).setup(name="TMS", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.tck.get(), trait=F.has_net_name_suggestion
        ).setup(name="TCK", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.rtck.get(), trait=F.has_net_name_suggestion
        ).setup(name="RTCK", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.n_trst.get(), trait=F.has_net_name_suggestion
        ).setup(name="N_TRST", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.n_reset.get(), trait=F.has_net_name_suggestion
        ).setup(name="N_RESET", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.vtref.get(), trait=F.has_net_name_suggestion
        ).setup(name="VTREF", level=F.has_net_name_suggestion.Level.SUGGESTED)

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
        ).put_on_type()
    )
