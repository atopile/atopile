# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class GenericBusProtection(Module):
    type T = ModuleInterface

    @L.rt_field
    def bus_unprotected(self):
        return self.bus_factory()

    @L.rt_field
    def bus_protected(self):
        return self.bus_factory()

    def __init__(self, bus_factory: Callable[[], T]) -> None:
        super().__init__()
        self.bus_factory = bus_factory

    def __preinit__(self):
        def get_mifs[U: ModuleInterface](
            bus: "GenericBusProtection.T", mif_type: type[U]
        ) -> set[U]:
            return bus.get_children(direct_only=True, types=mif_type)

        raw = list(
            zip(
                get_mifs(self.bus_unprotected, F.Electrical),
                get_mifs(self.bus_protected, F.Electrical),
            )
        )
        signals = list(
            zip(
                get_mifs(self.bus_unprotected, F.ElectricLogic),
                get_mifs(self.bus_protected, F.ElectricLogic),
            )
        )
        power = list(
            zip(
                get_mifs(self.bus_unprotected, F.ElectricPower),
                get_mifs(self.bus_protected, F.ElectricPower),
            )
        )

        fuse = L.list_field(len(power), F.Fuse)

        # Pass through except hv
        for power_unprotected, power_protected in power:
            power_unprotected.lv.connect(power_protected.lv)
        for logic_unprotected, logic_protected in signals:
            logic_unprotected.connect_shallow(logic_protected, signal=True, lv=True)
        for raw_unprotected, raw_protected in raw:
            raw_unprotected.connect(raw_protected)

        # Fuse
        for (power_unprotected, power_protected), fuse in zip(power, fuse):
            power_unprotected.hv.connect_via(fuse, power_protected.hv)
            # TODO maybe shallow connect?
            power_protected.voltage.alias_is(power_unprotected.voltage)

        # TVS
        if self.bus_protected.has_trait(F.can_be_surge_protected):
            self.bus_protected.get_trait(F.can_be_surge_protected).protect(self)
        else:
            for line_unprotected, line_protected in signals + power + raw:
                line_protected.get_trait(F.can_be_surge_protected).protect(self)

        # TODO add shallow connect

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.bus_unprotected, self.bus_protected)
