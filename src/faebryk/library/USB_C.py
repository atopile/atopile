# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class USB_C(ModuleInterface):
    usb3: F.USB3
    cc1: F.Electrical
    cc2: F.Electrical
    sbu1: F.Electrical
    sbu2: F.Electrical
    rx: F.DifferentialPair
    tx: F.DifferentialPair

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.cc1.add(F.has_net_name("CC1", level=F.has_net_name.Level.SUGGESTED))
        self.cc2.add(F.has_net_name("CC2", level=F.has_net_name.Level.SUGGESTED))
        self.sbu1.add(F.has_net_name("SBU1", level=F.has_net_name.Level.SUGGESTED))
        self.sbu2.add(F.has_net_name("SBU2", level=F.has_net_name.Level.SUGGESTED))
        self.rx.p.line.add(F.has_net_name("RX", level=F.has_net_name.Level.SUGGESTED))
        self.rx.n.line.add(F.has_net_name("RX", level=F.has_net_name.Level.SUGGESTED))
        self.tx.p.line.add(F.has_net_name("TX", level=F.has_net_name.Level.SUGGESTED))
        self.tx.n.line.add(F.has_net_name("TX", level=F.has_net_name.Level.SUGGESTED))
