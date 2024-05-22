# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ModuleInterface, ModuleInterfaceTrait
from faebryk.libs.util import find


class is_esphome_bus(ModuleInterfaceTrait):
    ...

    @abstractmethod
    def get_bus_id(self) -> str:
        ...

    @staticmethod
    def find_connected_bus(bus: ModuleInterface):
        connected_mifs = bus.get_direct_connections()
        try:
            return find(connected_mifs, lambda mif: mif.has_trait(is_esphome_bus))
        except ValueError:
            raise Exception(f"No esphome bus connected to {bus}: {connected_mifs}")
