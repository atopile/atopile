# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Addressor(ModuleInterface):
    address = L.p_field()
    offset = L.p_field()
    base = L.p_field()

    @L.rt_field
    def address_lines(self):
        return times(self._address_bits, F.ElectricLogic)

    def __init__(self, address_bits: int):
        self._address_bits = address_bits

    def __preinit__(self) -> None:
        self.address.alias_is(self.base + self.offset)
        # TODO: constrain cardinality to 1 for address
        # self.address.constrain_cardinality(1)

        for i, line in enumerate(self.address_lines):
            (self.address & (1 << i)).if_then_else(
                lambda: line.set(True),
                lambda: line.set(False),
            )
