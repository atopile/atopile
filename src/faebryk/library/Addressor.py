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

    address_bits_ = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Natural)
    address_lines_ = F.Collections.PointerSet.MakeChild()

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    @property
    def address_lines(self) -> list[F.ElectricLogic]:
        return [
            F.ElectricLogic.bind_instance(line.instance)
            for line in self.address_lines_.get().as_list()
        ]

    @classmethod
    def MakeChild(cls, address_bits: int) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Numbers.MakeChild_ConstrainToLiteral(
                [out, cls.address_bits_], address_bits
            )
        )
        for i in range(address_bits):
            address_line = F.ElectricLogic.MakeChild()
            out.add_dependant(address_line)
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge(
                    [out, cls.address_lines_], [address_line]
                )
            )
        return out

    def on_obj_set(self):
        # set net names for address lines
        for i, line in enumerate(self.address_lines):
            fabll.Traits.create_and_add_instance_to(
                node=line, trait=F.has_net_name
            ).setup(name=f"address_bit_{i}", level=F.has_net_name.Level.SUGGESTED)

        # constrain parameters
        for x in (self.address, self.offset, self.base):
            x.get().force_extract_literal().op_greater_or_equal(
                F.Literals.Numbers.MakeChild(value=0).get()
            )

        # TODO: ops not implemented yet
        # self.offset.get().force_extract_literal().op_less_or_equal(
        #     F.Literals.Numbers.MakeChild(
        #        value=1 << self.address_bits_.get().force_extract_literal().get_value()
        #     ).get()
        # )

        # self.address.get().force_extract_literal().alias_is(self.base + self.offset)
        # # TODO: not implemented yet
        # # self.offset.constrain_cardinality(1)

        # for i, line in enumerate(self.address_lines):
        #     (
        #         self.offset.get()
        #         .force_extract_literal()
        #         .op_is_bit_set(F.Literals.Numbers.MakeChild(value=i).get())
        #     ).if_then_else(
        #         lambda line=line: line.set(True),
        #         lambda line=line: line.set(False),
        #     )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
    )
