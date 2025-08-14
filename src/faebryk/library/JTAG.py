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
        self.n_trst.line.add(
            F.has_net_name("N_TRST", level=F.has_net_name.Level.SUGGESTED)
        )
        self.n_reset.line.add(
            F.has_net_name("N_RESET", level=F.has_net_name.Level.SUGGESTED)
        )
        self.vtref.add(F.has_net_name("VTREF", level=F.has_net_name.Level.SUGGESTED))
