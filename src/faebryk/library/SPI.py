# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class SPI(ModuleInterface):
    sclk: F.ElectricLogic
    miso: F.ElectricLogic
    mosi: F.ElectricLogic

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.sclk.line.add(F.has_net_name("SCLK", level=F.has_net_name.Level.SUGGESTED))
        self.miso.line.add(F.has_net_name("MISO", level=F.has_net_name.Level.SUGGESTED))
        self.mosi.line.add(F.has_net_name("MOSI", level=F.has_net_name.Level.SUGGESTED))
