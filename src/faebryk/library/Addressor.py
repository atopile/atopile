# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Addressor(fabll.Node):
    address = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Natural)
    offset = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Natural)
    base = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Natural)

    # def address_lines(self):
    #     return times(self._address_bits, F.ElectricLogic)

    _single_electric_reference = fabll._ChildField(F.has_single_electric_reference)
    address_bits_ = fabll._ChildField(F.Parameters.NumericParameter)
    address_lines_ = [F.ElectricLogic.MakeChild() for _ in range(4)]

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

    @property
    def address_lines(self) -> list[F.ElectricLogic]:
        return [
            F.ElectricLogic.bind_instance(line.instance) for line in self.address_lines_
        ]

    @classmethod
    def MakeChild(cls, address_bits: int) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.address_bits_], address_bits
            )
        )
        for i in range(address_bits):
            cls.address_lines[i].add_dependant(
                F.has_net_name.MakeChild(
                    name=f"address_bit_{i}", level=F.has_net_name.Level.SUGGESTED
                )
            )

    def setup(self, address_bits: int) -> Self:
        self.address_bits_.get().constrain_to_literal(
            g=self.instance.g(), value=address_bits
        )
        for i, line in enumerate(self.address_lines_):
            fabll.Traits.create_and_add_instance_to(
                node=line.get(), trait=F.has_net_name
            ).setup(name=f"address_bit_{i}", level=F.has_net_name.Level.SUGGESTED)
        return self

    usage_example = F.has_usage_example.MakeChild(
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
    ).put_on_type()
