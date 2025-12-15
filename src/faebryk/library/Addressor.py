# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import ClassVar, Self

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph, graph_render
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import UserDesignCheckException
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
        address_lines_pointer = not_none(
            fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=self.instance,
                child_identifier=self._address_lines_identifier,
            )
        )
        return [
            F.ElectricLogic.bind_instance(line.instance)
            for line in F.Collections.Pointer.bind_instance(
                address_lines_pointer
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

    address_lines_pointer = F.Collections.Pointer.MakeChild()
    for i in range(address_bits):
        elec = F.ElectricLogic.MakeChild()
        ConcreteAddressor._add_field(
            f"address_line_{i}",
            elec,
        )
        ConcreteAddressor._add_field(
            f"address_line_{i}_pointer",
            F.Collections.Pointer.MakeEdge(
                [ConcreteAddressor._address_lines_identifier, address_lines_pointer],
                [elec],
            ),
        )
    ConcreteAddressor._add_field(
        ConcreteAddressor._address_lines_identifier,
        address_lines_pointer,
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

    addressor_type = AddressorFactory(address_bits=address_bits)
    addressor = addressor_type.bind_typegraph(tg=tg).create_instance(g=g)
    # TODO: remove this
    print(
        graph_render.GraphRenderer.render(
            addressor.instance,
            show_traits=True,
            show_pointers=True,
            show_connections=True,
        )
    )
    assert addressor.get_address_bits() == address_bits
    address_lines = addressor.get_address_lines()
    assert len(address_lines) == address_bits


class ConfigurableI2CClient(fabll.Node):
    addressor = AddressorFactory(address_bits=3).MakeChild()
    i2c = F.I2C.MakeChild()
    config = [F.ElectricLogic.MakeChild() for _ in range(3)]
    ref = F.ElectricPower.MakeChild()

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    def setup(self, g, tg) -> Self:
        F.Expressions.Is.c(
            self.addressor.get().address.get().can_be_operand.get(),
            self.i2c.get().address.get().can_be_operand.get(),
            g=g,
            tg=tg,
            assert_=True,
        )
        self.addressor.get().base.get().alias_to_literal(
            g,
            F.Literals.Numbers.bind_typegraph(tg)
            .create_instance(g)
            .setup_from_singleton(
                value=16,
                unit=F.Units.Dimensionless.bind_typegraph(tg)
                .create_instance(g)
                .is_unit.get(),
            ),
        )

        for a, b in zip(self.addressor.get().get_address_lines(), self.config):
            a._is_interface.get().connect_to(b.get())

        return self


def test_addressor():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = ConfigurableI2CClient.bind_typegraph(tg).create_instance(g=g).setup(g, tg)
    app.setup(g, tg)

    app.addressor.get().offset.get().alias_to_literal(g, 3)
    app.i2c.get().address.get().alias_to_literal(
        g,
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g)
        .setup_from_singleton(
            value=16 + 3,
            unit=F.Units.Dimensionless.bind_typegraph(tg)
            .create_instance(g)
            .is_unit.get(),
        ),
    )

    solver = DefaultSolver()
    solver.simplify(g, tg)

    # TODO: fix on_obj_set logic
    # app.addressor.get().on_obj_set()

    assert solver.inspect_get_known_supersets(
        app.i2c.get().address.get().is_parameter.get()
    ).equals(
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g)
        .setup_from_singleton(
            value=16 + 3,
            unit=F.Units.Dimensionless.bind_typegraph(tg)
            .create_instance(g)
            .is_unit.get(),
        )
    )

    print(app.config[0].get().line.get()._is_interface.get().get_connected())
    assert (
        app.config[0]
        .get()
        .line.get()
        ._is_interface.get()
        .is_connected_to(app.ref.get().hv.get())
    )
    assert (
        app.config[1]
        .get()
        .line.get()
        ._is_interface.get()
        .is_connected_to(app.ref.get().hv.get())
    )
    assert (
        app.config[2]
        .get()
        .line.get()
        ._is_interface.get()
        .is_connected_to(app.ref.get().lv.get())
    )


class I2CBusTopology(fabll.Node):
    server = F.I2C.MakeChild()
    clients = [ConfigurableI2CClient.MakeChild() for _ in range(3)]

    def setup(self, isolated=False) -> Self:
        # self.server.address.alias_is(0)
        if not isolated:
            self.server.get()._is_interface.get().connect_to(
                *[c.get().i2c.get() for c in self.clients]
            )
            # self.server.get().terminate(self)
        else:
            self.server.get()._is_interface.get().connect_shallow_to(
                *[c.get().i2c.get() for c in self.clients]
            )
            # for c in [self.server] + [c.i2c for c in self.clients]:
            #    c.terminate(self)
        return self


def test_i2c_unique_addresses():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = I2CBusTopology.bind_typegraph(tg).create_instance(g=g).setup()
    app.clients[0].get().addressor.get().offset.get().alias_to_literal(g, 1)
    app.clients[1].get().addressor.get().offset.get().alias_to_literal(g, 2)
    app.clients[2].get().addressor.get().offset.get().alias_to_literal(g, 3)

    solver = DefaultSolver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)


def test_i2c_duplicate_addresses():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = I2CBusTopology.bind_typegraph(tg).create_instance(g=g).setup()
    app.clients[0].get().addressor.get().offset.get().alias_to_literal(g, 1)
    app.clients[1].get().addressor.get().offset.get().alias_to_literal(g, 3)
    app.clients[2].get().addressor.get().offset.get().alias_to_literal(g, 3)

    solver = DefaultSolver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # with pytest.raises(F.I2C.requires_unique_addresses.DuplicateAddressException):
    with pytest.raises(ExceptionGroup) as e:
        check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)
    assert e.group_contains(
        UserDesignCheckException, match="Duplicate I2C addresses found on the bus:"
    )


def test_i2c_duplicate_addresses_isolated():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = I2CBusTopology.bind_typegraph(tg).create_instance(g=g).setup(isolated=True)
    app.clients[0].get().addressor.get().offset.get().alias_to_literal(g, 1)
    app.clients[1].get().addressor.get().offset.get().alias_to_literal(g, 3)
    app.clients[2].get().addressor.get().offset.get().alias_to_literal(g, 3)

    solver = DefaultSolver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # with pytest.raises(F.I2C.requires_unique_addresses.DuplicateAddressException):
    with pytest.raises(ExceptionGroup) as e:
        check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)
    assert e.group_contains(
        UserDesignCheckException, match="Duplicate I2C addresses found on the bus:"
    )
