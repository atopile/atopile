# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P


class USB2_0_IF(ModuleInterface):
    class Data(F.DifferentialPair):
        # FIXME: this should be in diffpair right?
        @L.rt_field
        def single_electric_reference(self):
            return F.has_single_electric_reference_defined(
                F.ElectricLogic.connect_all_module_references(self)
            )

        def __preinit__(self):
            self.single_electric_reference.get_reference().voltage.constrain_subset(
                L.Range(0 * P.V, 3.6 * P.V)
            )

    d: Data
    buspower: F.ElectricPower

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.d.p.line.add(F.has_net_name("USB_D", level=F.has_net_name.Level.SUGGESTED))
        self.d.n.line.add(F.has_net_name("USB_D", level=F.has_net_name.Level.SUGGESTED))
        self.buspower.hv.add(
            F.has_net_name("USB_VBUS", level=F.has_net_name.Level.SUGGESTED)
        )
