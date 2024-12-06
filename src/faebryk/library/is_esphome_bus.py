# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.util import cast_assert, find


class is_esphome_bus(ModuleInterface.TraitT):
    ...

    @abstractmethod
    def get_bus_id(self) -> str: ...

    @staticmethod
    def find_connected_bus[T: ModuleInterface](bus: T) -> T:
        connected_mifs = bus.get_connected()
        try:
            return cast_assert(
                type(bus),
                find(connected_mifs, lambda mif: mif.has_trait(is_esphome_bus)),
            )
        except ValueError:
            raise Exception(f"No esphome bus connected to {bus}: {connected_mifs}")
