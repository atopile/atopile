# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable, Generic, TypeVar

from faebryk.core.core import (
    Module,
    ModuleInterface,
)
from faebryk.library.can_be_surge_protected import can_be_surge_protected
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.Fuse import Fuse
from faebryk.libs.util import times

T = TypeVar("T", bound=ModuleInterface)


class GenericBusProtection(Generic[T], Module):
    def __init__(self, bus_factory: Callable[[], T]) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            bus_unprotected = bus_factory()
            bus_protected = bus_factory()

        self.IFs = _IFs(self)

        U = TypeVar("U", bound=ModuleInterface)

        def get_mifs(bus: T, mif_type: type[U]) -> list[U]:
            return [i for i in bus.IFs.get_all() if isinstance(i, mif_type)]

        raw = list(
            zip(
                get_mifs(self.IFs.bus_unprotected, Electrical),
                get_mifs(self.IFs.bus_protected, Electrical),
            )
        )
        signals = list(
            zip(
                get_mifs(self.IFs.bus_unprotected, ElectricLogic),
                get_mifs(self.IFs.bus_protected, ElectricLogic),
            )
        )
        power = list(
            zip(
                get_mifs(self.IFs.bus_unprotected, ElectricPower),
                get_mifs(self.IFs.bus_protected, ElectricPower),
            )
        )

        class _NODEs(Module.NODES()):
            fuse = times(len(power), Fuse)

        self.NODEs = _NODEs(self)

        # Pass through except hv
        for power_unprotected, power_protected in power:
            power_unprotected.IFs.lv.connect(power_protected.IFs.lv)
        for logic_unprotected, logic_protected in signals:
            logic_unprotected.connect_shallow(logic_protected, signal=True, lv=True)
        for raw_unprotected, raw_protected in raw:
            raw_unprotected.connect(raw_protected)

        # Fuse
        for (power_unprotected, power_protected), fuse in zip(power, self.NODEs.fuse):
            power_unprotected.IFs.hv.connect_via(fuse, power_protected.IFs.hv)
            # TODO maybe shallow connect?
            power_protected.PARAMs.voltage.merge(power_unprotected.PARAMs.voltage)

        # TVS
        if self.IFs.bus_protected.has_trait(can_be_surge_protected):
            self.IFs.bus_protected.get_trait(can_be_surge_protected).protect()
        else:
            for line_unprotected, line_protected in signals + power + raw:
                line_protected.get_trait(can_be_surge_protected).protect()

        # TODO add shallow connect
        self.add_trait(
            can_bridge_defined(self.IFs.bus_unprotected, self.IFs.bus_protected)
        )
