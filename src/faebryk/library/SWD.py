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
