# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import ClassVar, Self, cast

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph, graph_render
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import UserDesignCheckException

logger = logging.getLogger(__name__)


class Addressor(fabll.Node):
    """
    Configures I2C/SPI device addresses via hardware address pins.

    The Addressor creates a number of ElectricLogic address lines based on the
    address_bits parameter. After the solver resolves the offset value, each
    address line is connected to either hv (high/1) or lv (low/0) based on the
    corresponding bit in the offset.

    The final device address is calculated as: address = base + offset

    Example usage in ato:
        addressor = new Addressor<address_bits=2>
        addressor.base = 0x48  # Device base address from datasheet
        assert addressor.address is i2c.address
        addressor.address_lines[0].line ~ device.ADDR0
        addressor.address_lines[0].reference ~ power
    """

    is_abstract = fabll.Traits.MakeEdge(fabll.is_abstract.MakeChild()).put_on_type()
    address = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Bit,
        domain=F.NumberDomain.Args(negative=False, integer=True),
    )
    offset = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Bit,
        domain=F.NumberDomain.Args(negative=False, integer=True),
    )
    base = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Bit,
        domain=F.NumberDomain.Args(negative=False, integer=True),
    )

    # address lines made by the factory
    address_lines: ClassVar[list[fabll._ChildField[F.ElectricLogic]]] = []

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    # Design check trait for post-solve address line configuration
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    class OffsetNotResolvedError(F.implements_design_check.UnfulfilledCheckException):
        """Raised when the offset parameter is not constrained to a single value."""

        def __init__(self, addressor: "Addressor"):
            super().__init__(
                "Addressor offset must be constrained to a single value. "
                "Use 'assert addressor.offset is <value>' to constrain it.",
                nodes=[addressor],
            )

    @F.implements_design_check.register_post_solve_check
    def __check_post_solve__(self):
        """
        Set address lines high/low based on the solved offset value.

        Called during POST_SOLVE stage after the solver has resolved parameter values.
        For each bit in the offset value, the corresponding address line is connected
        to either hv (bit=1) or lv (bit=0) of its reference power.
        """
        solver = self.design_check.get().get_solver()

        # Get the resolved offset value
        offset_lit = solver.inspect_get_known_supersets(
            self.offset.get().is_parameter.get()
        )

        # Verify offset is resolved to a singleton
        if not offset_lit.is_singleton():
            raise Addressor.OffsetNotResolvedError(self)

        # Cast to Numbers and extract the single value
        # We know this is a Numbers literal since offset is a NumericParameter
        offset_numbers = fabll.Traits(offset_lit).get_obj_raw().cast(F.Literals.Numbers)
        offset_value = int(offset_numbers.get_single())

        # Set each address line based on corresponding bit in offset
        for i, line_field in enumerate(self.address_lines):
            bit_set = bool((offset_value >> i) & 1)
            line_field.get().set(bit_set)

        logger.debug(
            f"Addressor: Set address lines for offset={offset_value} "
            f"(binary: {bin(offset_value)})"
        )

    @classmethod
    def MakeChild(
        cls, address_bits: int, offset: int = 0, base: int = 0
    ) -> fabll._ChildField[Self]:
        if address_bits <= 0:
            raise ValueError("At least one address bit is required")
        addressor = Addressor.factory(address_bits=address_bits)

        out = fabll._ChildField(addressor)

        # Constrain base parameter to the provided value
        out.add_dependant(
            F.Literals.Numbers.MakeChild_ConstrainToSingleton(
                [out, addressor.base],
                value=base,
                unit=F.Units.Bit,
            )
        )

        # Constrain offset parameter to the provided value
        out.add_dependant(
            F.Literals.Numbers.MakeChild_ConstrainToSingleton(
                [out, addressor.offset],
                value=offset,
                unit=F.Units.Bit,
            )
        )

        # Create expression constraint: address = base + offset
        # First create the Add expression for base + offset
        add_expr = F.Expressions.Add.MakeChild(
            [out, addressor.base],
            [out, addressor.offset],
        )
        out.add_dependant(add_expr)

        # Then create the Is constraint that equates address to the sum
        is_constraint = F.Expressions.Is.MakeChild(
            [out, addressor.address],
            [add_expr],
            assert_=True,
        )
        out.add_dependant(is_constraint)

        # Add offset constraint: offset must be in valid range [0, 2^address_bits - 1]
        # This is expressed as: max_offset >= offset (i.e., offset <= max_offset)
        max_offset_value = (1 << address_bits) - 1
        max_offset_lit = F.Literals.Numbers.MakeChild(
            min=max_offset_value,
            max=max_offset_value,
            unit=F.Units.Bit,
        )
        # Note: RefPaths must include "can_be_operand" trait reference for GreaterOrEqual #noqa: E501
        offset_bound_constraint = F.Expressions.GreaterOrEqual.MakeChild(
            [max_offset_lit, "can_be_operand"],  # left: max_offset
            [out, addressor.offset, "can_be_operand"],  # right: offset
            assert_=True,
        )
        out.add_dependant(max_offset_lit)
        out.add_dependant(offset_bound_constraint)

        return cast(fabll._ChildField[Self], out)

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

    @classmethod
    def factory(cls, address_bits: int) -> type[Self]:
        ConcreteAddressor = fabll.Node._copy_type(cls)
        ConcreteAddressor.__name__ = f"Addressor<address_bits={address_bits}>"
        address_lines = [F.ElectricLogic.MakeChild() for _ in range(address_bits)]
        ConcreteAddressor._handle_cls_attr("address_lines", address_lines)

        return ConcreteAddressor


@pytest.mark.parametrize("address_bits", [1, 2, 3])
def test_addressor_x_bit(address_bits: int):
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    addressor_type = Addressor.factory(address_bits=address_bits)
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
    address_lines = [al.get() for al in addressor.address_lines]
    assert len(address_lines) == address_bits
    for line in address_lines:
        assert isinstance(line, F.ElectricLogic)


def test_addressor_make_child():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        addressor = Addressor.MakeChild(address_bits=3, offset=1, base=0x48)

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    assert app.addressor.get().offset.get().force_extract_literal().get_single() == 1
    assert (
        int(app.addressor.get().base.get().force_extract_literal().get_single()) == 0x48
    )
    address_lines = [al.get() for al in app.addressor.get().address_lines]
    assert len(address_lines) == 3
    for line in address_lines:
        assert isinstance(line, F.ElectricLogic)


@pytest.mark.parametrize(
    "address_bits,offset,expected_bits",
    [
        (1, 0, [False]),  # 0b0
        (1, 1, [True]),  # 0b1
        (2, 0, [False, False]),  # 0b00
        (2, 1, [True, False]),  # 0b01
        (2, 2, [False, True]),  # 0b10
        (2, 3, [True, True]),  # 0b11
        (3, 5, [True, False, True]),  # 0b101
        (4, 10, [False, True, False, True]),  # 0b1010
    ],
)
def test_addressor_sets_address_lines(
    address_bits: int, offset: int, expected_bits: list[bool]
):
    """Test that address lines are set correctly based on offset bits."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()

    # Dynamically add the addressor with the correct bit count
    addressor_type = Addressor.factory(address_bits=address_bits)
    App._handle_cls_attr("addressor", fabll._ChildField(addressor_type))

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Connect address line references to power
    for line_field in addressor.address_lines:
        line_field.get().reference.get()._is_interface.get().connect_to(app.power.get())

    # Set the offset value
    addressor.offset.get().alias_to_literal(g, float(offset))

    # Run solver and attach has_solver trait
    solver = DefaultSolver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # Run post-solve checks (this triggers address line setting)
    check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)

    # Verify each address line is connected to the correct rail
    for i, (line_field, expected_high) in enumerate(
        zip(addressor.address_lines, expected_bits)
    ):
        line = line_field.get()
        ref = line.reference.get()

        if expected_high:
            # Should be connected to hv (high)
            assert line.line.get()._is_interface.get().is_connected_to(ref.hv.get()), (
                f"Address line {i} should be HIGH for offset={offset}"
            )
        else:
            # Should be connected to lv (low)
            assert line.line.get()._is_interface.get().is_connected_to(ref.lv.get()), (
                f"Address line {i} should be LOW for offset={offset}"
            )


def test_addressor_unresolved_offset_raises():
    """Test that an error is raised if offset is not constrained to singleton."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Use factory directly to create an addressor without default offset value
    addressor_type = Addressor.factory(address_bits=2)

    class App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()

    # Add addressor without the default offset constraint from MakeChild
    App._handle_cls_attr("addressor", fabll._ChildField(addressor_type))

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Connect address line references to power
    for line_field in addressor.address_lines:
        line_field.get().reference.get()._is_interface.get().connect_to(app.power.get())

    # Give offset a range constraint instead of a singleton
    # This simulates user doing: assert addressor.offset within 0 to 3
    addressor.offset.get().alias_to_literal(
        g,
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g)
        .setup_from_min_max(
            min=0.0,
            max=3.0,
            unit=F.Units.Bit.bind_typegraph(tg).create_instance(g).is_unit.get(),
        ),
    )

    solver = DefaultSolver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # Should raise because offset is not constrained to singleton (it's a range)
    with pytest.raises(UserDesignCheckException, match="offset must be constrained"):
        check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)


class ConfigurableI2CClient(fabll.Node):
    # Use factory directly so tests can set offset/base dynamically
    # (MakeChild would constrain them to defaults which can't be overridden)
    _addressor_type: ClassVar[type[Addressor]] = Addressor.factory(address_bits=3)
    addressor = fabll._ChildField(_addressor_type)
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
        # Set base address for this I2C client
        self.addressor.get().base.get().alias_to_literal(g, 16.0)

        for a, b in zip(self.addressor.get().address_lines, self.config):
            a.get()._is_interface.get().connect_to(b.get())

        # Connect address line references to power
        for line_field in self.addressor.get().address_lines:
            line_field.get().reference.get()._is_interface.get().connect_to(
                self.ref.get()
            )

        return self


def test_addressor():
    from faebryk.core.solver.defaultsolver import DefaultSolver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = ConfigurableI2CClient.bind_typegraph(tg).create_instance(g=g).setup(g, tg)
    app.setup(g, tg)

    app.addressor.get().offset.get().alias_to_literal(g, 3.0)
    app.i2c.get().address.get().alias_to_literal(
        g,
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g)
        .setup_from_singleton(
            value=16 + 3,
            unit=F.Units.Bit.bind_typegraph(tg).create_instance(g).is_unit.get(),
        ),
    )

    solver = DefaultSolver()
    solver.simplify(g, tg)

    # Attach solver and run post-solve design checks (which sets address lines)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)
    check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)

    assert solver.inspect_get_known_supersets(
        app.i2c.get().address.get().is_parameter.get()
    ).equals(
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g)
        .setup_from_singleton(
            value=16 + 3,
            unit=F.Units.Bit.bind_typegraph(tg).create_instance(g).is_unit.get(),
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

    def setup(self, g, tg, isolated=False) -> Self:
        # Set up each client (connects address lines to power, sets base address)
        for client in self.clients:
            client.get().setup(g, tg)

        if not isolated:
            self.server.get()._is_interface.get().connect_to(
                *[c.get().i2c.get() for c in self.clients]
            )
        else:
            self.server.get()._is_interface.get().connect_shallow_to(
                *[c.get().i2c.get() for c in self.clients]
            )
        return self


def test_i2c_unique_addresses():
    from faebryk.core.solver.defaultsolver import DefaultSolver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = I2CBusTopology.bind_typegraph(tg).create_instance(g=g).setup(g, tg)
    app.clients[0].get().addressor.get().offset.get().alias_to_literal(g, 1.0)
    app.clients[1].get().addressor.get().offset.get().alias_to_literal(g, 2.0)
    app.clients[2].get().addressor.get().offset.get().alias_to_literal(g, 3.0)

    solver = DefaultSolver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)


@pytest.mark.skip(
    reason="I2C.requires_unique_addresses not yet implemented in new core"
)
def test_i2c_duplicate_addresses():
    from faebryk.core.solver.defaultsolver import DefaultSolver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = I2CBusTopology.bind_typegraph(tg).create_instance(g=g).setup(g, tg)
    app.clients[0].get().addressor.get().offset.get().alias_to_literal(g, 1.0)
    app.clients[1].get().addressor.get().offset.get().alias_to_literal(g, 3.0)
    app.clients[2].get().addressor.get().offset.get().alias_to_literal(g, 3.0)

    solver = DefaultSolver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # with pytest.raises(F.I2C.requires_unique_addresses.DuplicateAddressException):
    with pytest.raises(ExceptionGroup) as e:
        check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)
    assert e.group_contains(
        UserDesignCheckException, match="Duplicate I2C addresses found on the bus:"
    )


@pytest.mark.skip(
    reason="I2C.requires_unique_addresses not yet implemented in new core"
)
def test_i2c_duplicate_addresses_isolated():
    from faebryk.core.solver.defaultsolver import DefaultSolver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = (
        I2CBusTopology.bind_typegraph(tg)
        .create_instance(g=g)
        .setup(g, tg, isolated=True)
    )
    app.clients[0].get().addressor.get().offset.get().alias_to_literal(g, 1.0)
    app.clients[1].get().addressor.get().offset.get().alias_to_literal(g, 3.0)
    app.clients[2].get().addressor.get().offset.get().alias_to_literal(g, 3.0)

    solver = DefaultSolver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # with pytest.raises(F.I2C.requires_unique_addresses.DuplicateAddressException):
    with pytest.raises(ExceptionGroup) as e:
        check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)
    assert e.group_contains(
        UserDesignCheckException, match="Duplicate I2C addresses found on the bus:"
    )
