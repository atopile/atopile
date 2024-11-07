# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.util import find


class is_esphome_bus(ModuleInterface.TraitT):
    ...

    @abstractmethod
    def get_bus_id(self) -> str: ...

    @staticmethod
    def find_connected_bus(bus: ModuleInterface):
        connected_mifs = list(bus.get_connected())
        try:
            return find(connected_mifs, lambda mif: mif.has_trait(is_esphome_bus))
        except ValueError:
            raise Exception(f"No esphome bus connected to {bus}: {connected_mifs}")
