# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Addressor(ModuleInterface):
    address = L.p_field(domain=L.Domains.Numbers.NATURAL())
    offset = L.p_field(domain=L.Domains.Numbers.NATURAL())
    base = L.p_field(domain=L.Domains.Numbers.NATURAL())

    @L.rt_field
    def address_lines(self):
        return times(self._address_bits, F.ElectricLogic)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __init__(self, address_bits: int):
        self._address_bits = address_bits
        super().__init__()

    def __preinit__(self) -> None:
        for x in (self.address, self.offset, self.base):
            x.constrain_ge(0)

        self.offset.constrain_le(1 << self._address_bits)

        self.address.alias_is(self.base + self.offset)
        # TODO: not implemented yet
        # self.offset.constrain_cardinality(1)

        for i, line in enumerate(self.address_lines):
            (self.offset.operation_is_bit_set(i)).if_then_else(
                lambda line=line: line.set(True),
                lambda line=line: line.set(False),
            )
