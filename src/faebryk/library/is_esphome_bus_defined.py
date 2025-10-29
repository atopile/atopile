# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class is_esphome_bus_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(self, bus_id: str):
        super().__init__()
        self._bus_id = bus_id

    def get_bus_id(self) -> str:
        return self._bus_id
