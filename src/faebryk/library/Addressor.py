# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import ClassVar

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.util import not_none, once

logger = logging.getLogger(__name__)


class AbstractAddressor(fabll.Node):
    address = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Bit, domain=F.NumberDomain.Args(negative=False, integer=True)
    )
    offset = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Bit, domain=F.NumberDomain.Args(negative=False, integer=True)
    )
    base = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Bit, domain=F.NumberDomain.Args(negative=False, integer=True)
    )

    _address_bits_identifier: ClassVar[str] = "address_bits"
    _address_lines_identifier: ClassVar[str] = "address_lines"

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    def get_address_lines(self) -> list[F.ElectricLogic]:
        address_lines_child = not_none(
            fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=self.instance,
                child_identifier=self._address_lines_identifier,
            )
        )
        return [
            F.ElectricLogic.bind_instance(line.instance)
            for line in F.Collections.PointerSet.bind_instance(
                address_lines_child
            ).as_list()
        ]

    def get_address_bits(self) -> int:
        address_bits_child = not_none(
            fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=self.instance, child_identifier=self._address_bits_identifier
            )
        )
        return int(F.Literals.Numbers.bind_instance(address_bits_child).get_single())

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


@once
def AddressorFactory(address_bits: int) -> type[AbstractAddressor]:
    ConcreteAddressor = fabll.Node._copy_type(AbstractAddressor)

    elecs = []
    for i in range(address_bits):
        elec = F.ElectricLogic.MakeChild().put_on_type()
        ConcreteAddressor._add_field(
            f"address_line_{i}",
            elec,
        )
        elecs.append(elec)
    address_lines_pointer_set = F.Collections.PointerSet.MakeChild(elecs)

    ConcreteAddressor._add_field(
        ConcreteAddressor._address_lines_identifier,
        address_lines_pointer_set,
    )
    ConcreteAddressor._add_field(
        ConcreteAddressor._address_bits_identifier,
        F.Literals.Numbers.MakeChild_SingleValue(
            value=address_bits, unit=F.Units.Dimensionless
        ),
    )
    return ConcreteAddressor


@pytest.mark.parametrize("address_bits", [1, 2, 3])
def test_addressor_x_bit(address_bits: int):
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    addressor = (
        AddressorFactory(address_bits=address_bits)
        .bind_typegraph(tg=tg)
        .create_instance(g=g)
    )
    assert addressor.get_address_bits() == address_bits
    address_lines = addressor.get_address_lines()
    assert len(address_lines) == address_bits
