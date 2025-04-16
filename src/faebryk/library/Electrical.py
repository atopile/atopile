# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.moduleinterface import ModuleInterface


class Electrical(ModuleInterface):
    # potential= L.p_field(units=P.dimensionless)

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

    def crosses_footprint_boundary(self):
        net = self.get_net()

        if net is None:
            return False

        return len(net.get_footprints()) > 1
