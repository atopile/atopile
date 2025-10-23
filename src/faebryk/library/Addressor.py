# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Addressor(ModuleInterface):
    address = fabll.p_field(domain=fabll.Domains.Numbers.NATURAL())
    offset = fabll.p_field(domain=fabll.Domains.Numbers.NATURAL())
    base = fabll.p_field(domain=fabll.Domains.Numbers.NATURAL())

    @fabll.rt_field
    def address_lines(self):
        return times(self._address_bits, F.ElectricLogic)

    @fabll.rt_field
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

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        for i, line in enumerate(self.address_lines):
            line.add(
                F.has_net_name(f"address_bit_{i}", level=F.has_net_name.Level.SUGGESTED)
            )

    usage_example = fabll.f_field(F.has_usage_example)(
        example="""
        import Addressor, I2C, ElectricPower

        # For I2C device with 2 address pins (4 possible addresses)
        addressor = new Addressor<address_bits=2>
        addressor.base = 0x48  # Base address from datasheet

        # Connect power reference for address pins
        power_3v3 = new ElectricPower
        for line in addressor.address_lines:
            line.reference ~ power_3v3

        # Connect address pins to device
        device.addr0 ~ addressor.address_lines[0].line
        device.addr1 ~ addressor.address_lines[1].line

        # Connect to I2C interface
        i2c_bus = new I2C
        assert i2c_bus.address is addressor.address
        device.i2c ~ i2c_bus
        """,
        language=F.has_usage_example.Language.ato,
    )
