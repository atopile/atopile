# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class Electrical(ModuleInterface):
    potential: F.TBD

    def get_net(self):
        from faebryk.library.Net import Net

        nets = {
            net
            for mif in self.get_connected()
            if (net := mif.get_parent_of_type(Net)) is not None
        }

        if not nets:
            return None

        assert len(nets) == 1
        return next(iter(nets))
