# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Addressor(fabll.Node):
    address = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Bit, integer=True, negative=False
    )
    offset = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Bit, integer=True, negative=False
    )
    base = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Bit, integer=True, negative=False
    )

    address_bits_ = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless, integer=True, negative=False
    )
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
    def MakeChild(cls, address_bits: int) -> fabll._ChildField[Self]:  # type: ignore
        out = fabll._ChildField(cls)
        # Store address bits as a dimensionless literal
        out.add_dependant(
            F.Literals.Numbers.MakeChild_ConstrainToSingleton(
                [out, cls.address_bits_],
                value=address_bits,
                unit=F.Units.Dimensionless,
            )
        )
        # Make a pointer to each address line
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
        # for i, line in enumerate(self.address_lines):
        #     fabll.Traits.create_and_add_instance_to(
        #         node=line, trait=F.has_net_name
        #     ).setup(name=f"address_bit_{i}", level=F.has_net_name.Level.SUGGESTED)

        # Constrain offset to be less than 2^address_bits

        # Calculate max offset value
        max_offset_value = 1 << int(
            self.address_bits_.get().force_extract_literal().get_value()
        )
        # Create dimensionless unit
        dimensionles_unit = (
            F.Units.Dimensionless.bind_typegraph(self.offset.get().tg)
            .create_instance(self.offset.get().instance.g())
            .is_unit.get()
        )
        # Create max offset literal
        max_offset = (
            F.Literals.Numbers.bind_typegraph(self.offset.get().tg)
            .create_instance(self.offset.get().instance.g())
            .setup_from_singleton(
                value=max_offset_value,
                unit=dimensionles_unit,
            )
        )
        # Create greater than or equal expression
        greater_or_equal_expression = F.Expressions.GreaterOrEqual.bind_typegraph(
            self.offset.get().tg
        ).create_instance(self.offset.get().instance.g())
        # Setup greater than or equal expression
        greater_or_equal_expression.setup(
            left=self.offset.get().can_be_operand.get(),
            right=max_offset.is_literal.get().as_operand.get(),
            assert_=True,
        )

        # # Constrain offset, base and address to be greater than or equal to 0
        # for x in (self.offset, self.base, self.address):
        # zero = (
        #     F.Literals.Numbers.bind_typegraph(self.offset.get().tg)
        #     .create_instance(g=self.offset.get().instance.g())
        #     .setup_from_singleton(
        #         g=self.offset.get().instance.g(),
        #         tg=self.offset.get().tg,
        #         value=0,
        #         unit=dimensionles_unit,
        #     )
        # )
        # greater_or_equal = F.Expressions.GreaterOrEqual.bind_typegraph(
        #     self.offset.get().tg
        # ).create_instance(self.offset.get().instance.g())
        # greater_or_equal.setup(
        #     left=self.offset.get().get_trait(F.Parameters.can_be_operand),
        #     right=zero.get_trait(F.Parameters.can_be_operand),
        #     assert_=True,
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
