# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import Self, cast

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
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
        unit=F.Units.Dimensionless,
        domain=F.NumberDomain.Args(negative=False, integer=True),
    )
    offset = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless,
        domain=F.NumberDomain.Args(negative=False, integer=True),
    )
    base = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless,
        domain=F.NumberDomain.Args(negative=False, integer=True),
    )

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
                "Addressor offset must be constrained to a single value.",
                nodes=[addressor],
            )

    @F.implements_design_check.register_post_solve_check
    def __check_post_solve__(self):
        """Set address lines based on the solved offset value."""

        # Try direct constraint first (returns Numbers)
        numbers = self.offset.get().try_extract_aliased_literal()
        if numbers is not None and numbers.is_literal.get().is_singleton():
            offset = int(numbers.get_single())
        else:
            # Use solver to deduce from address = base + offset
            solver = self.design_check.get().get_solver()

            # If solver is NullSolver, we can't deduce the offset
            from faebryk.core.solver.defaultsolver import DefaultSolver
            from faebryk.core.solver.nullsolver import NullSolver

            if isinstance(solver, NullSolver):
                logger.warning(
                    "Solver is NullSolver, can't use it to deduce the offset"
                )
                return
            assert isinstance(solver, DefaultSolver)
            offset_op = self.offset.get().can_be_operand.get()
            offset_param = self.offset.get().is_parameter.get()
            solver.update_superset_cache(offset_op)
            lit = solver.inspect_get_known_supersets(offset_param)
            if lit is None or not lit.is_singleton():
                # raise Addressor.OffsetNotResolvedError(self)
                raise Warning(
                    "Offset not resolved"
                )  # TODO: make the check only valid for external use
            # lit is an is_literal trait - get the actual node it's attached to
            lit_node = fabll.Traits(lit).get_obj_raw()
            offset = int(lit_node.cast(F.Literals.Numbers).get_single())

        # address_lines is a PointerSequence (dynamically added by factory())
        lines = self.address_lines.get().as_list()  # type: ignore[attr-defined]
        address_bits = len(lines)
        max_offset = (1 << address_bits) - 1
        if not 0 <= offset <= max_offset:
            raise ValueError(f"Offset {offset} out of range [0, {max_offset}]")

        for i, line_node in enumerate(lines):
            line = F.ElectricLogic.bind_instance(line_node.instance)
            line.set(bool((offset >> i) & 1))

    @classmethod
    def MakeChild(cls, address_bits: int) -> fabll._ChildField[Self]:
        """
        Create an Addressor child field with the specified number of address bits.

        Uses factory() to create a concrete type with address_lines as a proper
        list of ElectricLogic children.
        """
        logger.info(f"Addressor.MakeChild called: address_bits={address_bits}")

        # Use factory to create a concrete type with the right number of address lines
        ConcreteAddressor = cls.factory(address_bits)
        out = fabll._ChildField(ConcreteAddressor)

        # Setup constraint: address = base + offset
        add_expr = F.Expressions.Add.MakeChild(
            [out, ConcreteAddressor.base],
            [out, ConcreteAddressor.offset],
        )
        is_addr_constraint = F.Expressions.Is.MakeChild(
            [out, ConcreteAddressor.address],
            [add_expr],
            assert_=True,
        )
        out.add_dependant(add_expr)
        out.add_dependant(is_addr_constraint)

        # Constrain offset to valid range [0, 2^address_bits - 1]
        max_offset_value = (1 << address_bits) - 1
        max_offset_lit = F.Literals.Numbers.MakeChild(
            min=max_offset_value,
            max=max_offset_value,
            unit=F.Units.Dimensionless,
        )
        offset_bound_constraint = F.Expressions.GreaterOrEqual.MakeChild(
            [max_offset_lit],
            [out, ConcreteAddressor.offset],
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
        """
        Create a concrete Addressor type with a fixed number of address bits.

        This creates:
        1. A PointerSequence named `address_lines` for for-loop iteration in ato
        2. ElectricLogic children named `address_lines[0]`, `address_lines[1]`, etc.
           for direct indexed access
        3. MakeLink edges from the PointerSequence to each ElectricLogic element
        """
        if address_bits <= 0:
            raise ValueError("At least one address bit is required")

        ConcreteAddressor = fabll.Node._copy_type(cls)
        ConcreteAddressor.__name__ = f"Addressor<address_bits={address_bits}>"

        # 1. Create the PointerSequence for for-loop iteration
        address_lines_seq = F.Collections.PointerSequence.MakeChild()
        ConcreteAddressor._handle_cls_attr("address_lines", address_lines_seq)

        # 2. Create ElectricLogic children with indexed names
        # These become direct children: address_lines[0], address_lines[1], etc.
        for i in range(address_bits):
            line = F.ElectricLogic.MakeChild()
            ConcreteAddressor._handle_cls_attr(f"address_lines[{i}]", line)

            # 3. Create MakeLink edge from PointerSequence to element
            # This allows iteration: for line in addressor.address_lines
            edge = F.Collections.PointerSequence.MakeEdge(
                seq_ref=[address_lines_seq],
                elem_ref=[line],
                index=i,
            )
            # Add edge as a class field so it gets processed
            ConcreteAddressor._handle_cls_attr(f"_address_line_link_{i}", edge)

        return ConcreteAddressor


@pytest.mark.parametrize("address_bits", [1, 2, 3])
def test_addressor_x_bit(address_bits: int):
    """Test Addressor with various address bit counts via MakeChild."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        pass

    # Dynamically add the addressor with the correct bit count
    App._handle_cls_attr("addressor", Addressor.MakeChild(address_bits=address_bits))

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # address_lines is a PointerSequence pointing to ElectricLogic children
    lines = addressor.address_lines.get().as_list()
    assert len(lines) == address_bits
    for line in lines:
        assert line.try_cast(F.ElectricLogic) is not None


def test_addressor_make_child():
    """Test basic Addressor instantiation via MakeChild."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        addressor = Addressor.MakeChild(address_bits=3)

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    # Set offset and base (MakeChild only sets address_bits)
    app.addressor.get().offset.get().alias_to_literal(g, 1.0)
    app.addressor.get().base.get().alias_to_literal(g, float(0x48))

    assert app.addressor.get().offset.get().force_extract_literal().get_single() == 1
    assert (
        int(app.addressor.get().base.get().force_extract_literal().get_single()) == 0x48
    )
    # address_lines is a PointerSequence pointing to ElectricLogic children
    lines = app.addressor.get().address_lines.get().as_list()
    assert len(lines) == 3
    for line in lines:
        assert line.try_cast(F.ElectricLogic) is not None


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
    from faebryk.core.solver.defaultsolver import DefaultSolver

    """Test that address lines are set correctly based on offset bits."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()

    # Dynamically add the addressor with the correct bit count via MakeChild
    App._handle_cls_attr("addressor", Addressor.MakeChild(address_bits=address_bits))

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Get address lines from PointerSequence
    address_lines = addressor.address_lines.get().as_list()

    # Connect address line references to power
    for line in address_lines:
        # Cast to ElectricLogic for proper typing
        el = F.ElectricLogic.bind_instance(line.instance)
        el.reference.get()._is_interface.get().connect_to(app.power.get())

    # Set the offset value
    addressor.offset.get().alias_to_literal(g, float(offset))

    # Run solver and attach has_solver trait
    solver = DefaultSolver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # Run post-solve checks (this triggers address line setting)
    check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)

    # Get fresh address_lines after solve
    address_lines = addressor.address_lines.get().as_list()

    # Verify each address line is connected to the correct rail
    for i, (line_node, expected_high) in enumerate(zip(address_lines, expected_bits)):
        line = F.ElectricLogic.bind_instance(line_node.instance)
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


@pytest.mark.skip(reason="Currently just a warning")
def test_addressor_unresolved_offset_raises():
    """Test that an error is raised when offset cannot be determined."""
    from faebryk.core.solver.defaultsolver import DefaultSolver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()
        # Use MakeChild to get proper address_lines population
        addressor = Addressor.MakeChild(address_bits=2)

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Get address lines from PointerSequence and connect to power
    for line_node in addressor.address_lines.get().as_list():
        line = F.ElectricLogic.bind_instance(line_node.instance)
        line.reference.get()._is_interface.get().connect_to(app.power.get())

    # Don't constrain offset, base, or address - solver won't be able to deduce offset
    # Note: MakeChild adds address = base + offset constraint, but if neither
    # base, offset, nor address are constrained, offset can't be deduced.

    solver = DefaultSolver()
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # Should raise because offset is neither directly constrained nor deducible
    with pytest.raises(UserDesignCheckException, match="offset must be constrained"):
        check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)


class ConfigurableI2CClient(fabll.Node):
    # Use MakeChild for proper address_lines population
    addressor = Addressor.MakeChild(address_bits=3)
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

        # Get address lines from PointerSequence
        address_lines = self.addressor.get().address_lines.get().as_list()

        for line_node, config_field in zip(address_lines, self.config):
            line = F.ElectricLogic.bind_instance(line_node.instance)
            line._is_interface.get().connect_to(config_field.get())

        # Connect address line references to power
        for line_node in address_lines:
            line = F.ElectricLogic.bind_instance(line_node.instance)
            line.reference.get()._is_interface.get().connect_to(self.ref.get())

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


def test_addressor_expression_propagation():
    """
    Test that the solver can deduce offset from address and base.

    Given: address = base + offset
    When: base=24 (0x18), address=25 (0x19)
    Then: offset should be deduced as 1
    """
    from faebryk.core.solver.defaultsolver import DefaultSolver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        addressor = Addressor.MakeChild(address_bits=1)

    app = App.bind_typegraph(tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Set base = 24 (0x18) and address = 25 (0x19)
    # The Is constraint `address is Add(base, offset)` should allow solver to deduce offset=1 # noqa: E501
    addressor.base.get().alias_to_literal(g, 24.0)
    addressor.address.get().alias_to_literal(g, 25.0)

    # Debug: Check what expressions exist before solving
    print("\n=== Before solver ===")
    offset_po = addressor.offset.get().is_parameter_operatable.get()
    base_po = addressor.base.get().is_parameter_operatable.get()
    address_po = addressor.address.get().is_parameter_operatable.get()
    print(f"offset operations: {offset_po.get_operations()}")
    print(f"base operations: {base_po.get_operations()}")
    print(f"address operations: {address_po.get_operations()}")

    # Check the Is expression that links address to Add
    is_exprs = [op for op in address_po.get_operations() if "Is" in str(op)]
    print(f"address Is expressions: {is_exprs}")
    for is_expr in is_exprs:
        is_e = F.Expressions.Is.bind_instance(is_expr.instance)
        print(f"  {is_expr}: operands={is_e.is_expression.get().get_operands()}")

    # Run the solver using the same pattern as test_literal_folding.py
    solver = DefaultSolver()
    offset_op = addressor.offset.get().is_parameter_operatable.get()
    offset_param = addressor.offset.get().is_parameter.get()

    # This runs the solver and caches supersets
    solver.update_superset_cache(offset_op)

    # Get the result - this is in the solver's transient graph
    solver_result = solver.inspect_get_known_supersets(offset_param)
    print(f"\nsolver_result for offset: {solver_result}")

    # The solver CAN compute the result
    assert solver_result is not None, "solver should return a result for offset"

    solver_result_num = (
        fabll.Traits(solver_result).get_obj_raw().try_cast(F.Literals.Numbers)
    )
    assert solver_result_num is not None, "solver result should be Numbers"

    print(f"solver_result_num: {solver_result_num.pretty_str()}")

    # Verify the computed value is correct
    assert solver_result_num.is_singleton(), "offset should be a singleton"
    assert solver_result_num.get_single() == 1.0, (
        f"offset should be 1, got {solver_result_num.get_single()}"
    )
