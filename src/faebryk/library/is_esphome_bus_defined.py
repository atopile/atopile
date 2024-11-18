# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class is_esphome_bus_defined(F.is_esphome_bus.impl()):
    def __init__(self, bus_id: str):
        super().__init__()
        self._bus_id = bus_id

    def get_bus_id(self) -> str:
        return self._bus_id
