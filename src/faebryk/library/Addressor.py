# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import Self

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserDesignCheckException
from faebryk.core import graph
from faebryk.libs.util import once

logger = logging.getLogger(__name__)


class Addressor(fabll.Node):
    """
    Configures I2C/SPI device addresses via hardware address pins.

    Supports two modes:
    1. Binary mode (default, states_per_pin=2): Each address pin is driven
       high or low based on the corresponding bit in the offset.
    2. Multi-state mode (states_per_pin>2): Each address pin can be connected
       to one of N destinations (e.g. GND, VS, SDA, SCL for 4-state devices).

    The final device address is calculated as: address = base + offset

    Binary mode example (ato):
        addressor = new Addressor<address_bits=2>
        addressor.base = 0x48
        assert addressor.address is i2c.address
        addressor.address_lines[0].line ~ device.ADDR0
        addressor.address_lines[0].reference ~ power

    Multi-state mode example (ato):
        addressor = new Addressor<address_bits=2, states_per_pin=4>
        addressor.base = 0x40
        assert addressor.address is i2c.address
        addressor.states[0] ~ power.lv       # GND
        addressor.states[1] ~ power.hv       # VS
        addressor.states[2] ~ i2c.sda.line   # SDA
        addressor.states[3] ~ i2c.scl.line   # SCL
        addressor.address_lines[0].line ~ device.A0
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
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # PointerSequence for address lines - elements are added dynamically by factory()
    address_lines = F.Collections.PointerSequence.MakeChild()

    # PointerSequence for states (multi-state mode) - elements added by factory()
    states = F.Collections.PointerSequence.MakeChild()

    # Design check trait for post-solve address line configuration
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    class OffsetNotResolvedError(F.implements_design_check.UnfulfilledCheckException):
        """Raised when the offset parameter is not constrained to a single value."""

        def __init__(self, addressor: "Addressor"):
            super().__init__(
                "Addressor offset must be constrained to a single value.",
                nodes=[addressor],
            )

    @F.implements_design_check.register_post_instantiation_setup_check
    def __check_post_instantiation_setup__(self):
        """Set address lines based on the solved offset value."""
        # If solver hasn't been run, we can't deduce the offset

        # Use solver to deduce from address = base + offset
        solver = self.design_check.get().get_solver()

        offset_p = self.offset.get().is_parameter.get()
        logger.info(f"Running solver for addressor: {self}")

        lit = solver.extract_superset(offset_p)

        if lit is None or not lit.op_setic_is_singleton():
            lit = solver.simplify_and_extract_superset(offset_p)

        # Fallback to direct extraction from graph if solver doesn't give singleton.
        # This handles the case where offset is set directly via set_superset()
        # but the Is constraint (offset = address - base) has unconstrained operands.
        if lit is None or not lit.op_setic_is_singleton():
            direct_lit = self.offset.get().try_extract_superset()
            if direct_lit is not None and direct_lit.is_singleton():
                lit = direct_lit.is_literal.get()

        if lit is None or not lit.op_setic_is_singleton():
            # raise Addressor.OffsetNotResolvedError(self)
            raise Warning(
                "Offset not resolved"
            )  # TODO: make the check only valid for external use
        else:
            # lit is an is_literal trait - get the actual node it's attached to
            lit_node = fabll.Traits(lit).get_obj_raw()
            offset = int(lit_node.cast(F.Literals.Numbers).get_single())

        # address_lines is a PointerSequence (dynamically added by factory())
        lines = self.address_lines.get().as_list()  # type: ignore[attr-defined]
        address_bits = len(lines)

        # Check if multi-state mode (states exist)
        state_list = self.states.get().as_list()

        if len(state_list) > 0:
            # Multi-state mode: connect each address line to the correct state
            states_per_pin = len(state_list)
            max_offset = states_per_pin**address_bits - 1
            if not 0 <= offset <= max_offset:
                raise ValueError(f"Offset {offset} out of range [0, {max_offset}]")

            for i, line_node in enumerate(lines):
                line = F.ElectricLogic.bind_instance(line_node.instance)
                pin_state = (offset // (states_per_pin**i)) % states_per_pin
                destination_node = state_list[pin_state]
                destination = F.Electrical.bind_instance(destination_node.instance)
                line.line.get()._is_interface.get().connect_to(destination)
        else:
            # Binary mode: set each address line high or low
            max_offset = (1 << address_bits) - 1
            if not 0 <= offset <= max_offset:
                raise ValueError(f"Offset {offset} out of range [0, {max_offset}]")

            for i, line_node in enumerate(lines):
                line = F.ElectricLogic.bind_instance(line_node.instance)
                line.set(bool((offset >> i) & 1))

    @classmethod
    def MakeChild(
        cls, address_bits: int, states_per_pin: int = 2
    ) -> fabll._ChildField[Self]:
        """
        Create an Addressor child field with the specified number of address bits.

        Uses factory() to create a concrete type with address_lines as a proper
        list of ElectricLogic children.

        Args:
            address_bits: Number of address pins.
            states_per_pin: Number of states per pin (default 2 for binary high/low,
                use >2 for multi-state pins like TI's GND/VS/SDA/SCL scheme).
        """
        logger.debug(
            f"Addressor.MakeChild called: address_bits={address_bits}, "
            f"states_per_pin={states_per_pin}"
        )

        # Use factory to create a concrete type with the right number of address lines
        ConcreteAddressor = cls.factory(address_bits, states_per_pin)
        out = fabll._ChildField(ConcreteAddressor)

        # Setup constraint: offset is! address - base
        address_minus_base = F.Expressions.Subtract.MakeChild(
            [out, ConcreteAddressor.address],
            [out, ConcreteAddressor.base],
        ).add_as_dependant(out)

        F.Expressions.Is.MakeChild(
            [out, ConcreteAddressor.offset],
            [address_minus_base],
            assert_=True,
        ).add_as_dependant(out)

        # Constrain offset to valid range [0, states_per_pin^address_bits - 1]
        max_offset_value = states_per_pin**address_bits - 1
        F.Expressions.GreaterOrEqual.MakeChild(
            [
                F.Literals.Numbers.MakeChild(
                    min=max_offset_value,
                    max=max_offset_value,
                    unit=F.Units.Dimensionless,
                ).add_as_dependant(out)
            ],
            [out, ConcreteAddressor.offset],
            assert_=True,
        ).add_as_dependant(out)

        return out

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import Addressor, I2C, ElectricPower

        # Binary mode: 2 address pins (4 possible addresses)
        addressor = new Addressor<address_bits=2>
        addressor.base = 0x48
        assert addressor.address is i2c.address
        addressor.address_lines[0].line ~ device.ADDR0
        addressor.address_lines[0].reference ~ power

        # Multi-state mode: 2 pins x 4 states (16 possible addresses)
        addressor = new Addressor<address_bits=2, states_per_pin=4>
        addressor.base = 0x40
        assert addressor.address is i2c.address
        addressor.states[0] ~ power.lv       # GND
        addressor.states[1] ~ power.hv       # VS
        addressor.states[2] ~ i2c.sda.line   # SDA
        addressor.states[3] ~ i2c.scl.line   # SCL
        addressor.address_lines[0].line ~ device.A0
        addressor.address_lines[0].reference ~ power
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )

    @classmethod
    @once
    def factory(cls, address_bits: int, states_per_pin: int = 2) -> type[Self]:
        """
        Create a concrete Addressor type with a fixed number of address bits.

        This creates:
        1. ElectricLogic children named `address_lines[0]`, `address_lines[1]`, etc.
           for direct indexed access
        2. MakeLink edges from the inherited `address_lines` PointerSequence to each
           ElectricLogic element for for-loop iteration in ato
        3. (Multi-state mode only) Electrical children named `states[0]`, etc. and
           corresponding MakeLink edges from the `states` PointerSequence

        Args:
            address_bits: Number of address pins.
            states_per_pin: Number of states per pin (default 2 for binary).
        """
        if address_bits <= 0:
            raise ValueError("At least one address bit is required")
        if states_per_pin < 2:
            raise ValueError("states_per_pin must be at least 2")

        if states_per_pin == 2:
            name = f"Addressor<address_bits={address_bits}>"
        else:
            name = (
                f"Addressor<address_bits={address_bits}, "
                f"states_per_pin={states_per_pin}>"
            )

        ConcreteAddressor = fabll.Node._copy_type(cls, name=name)

        # Create ElectricLogic children with indexed names and link to PointerSequence
        # The address_lines PointerSequence is inherited from the base Addressor class
        for i in range(address_bits):
            line = F.ElectricLogic.MakeChild()
            ConcreteAddressor._handle_cls_attr(f"address_lines[{i}]", line)

            # Create MakeLink edge from inherited PointerSequence to element
            # This allows iteration: for line in addressor.address_lines
            edge = F.Collections.PointerSequence.MakeEdge(
                seq_ref=[cls.address_lines],
                elem_ref=[line],
                index=i,
            )
            # Add edge as a class field so it gets processed
            ConcreteAddressor._handle_cls_attr(f"_address_line_link_{i}", edge)

        # Multi-state mode: create Electrical states for each possible pin destination
        if states_per_pin > 2:
            for i in range(states_per_pin):
                state = F.Electrical.MakeChild()
                ConcreteAddressor._handle_cls_attr(f"states[{i}]", state)

                edge = F.Collections.PointerSequence.MakeEdge(
                    seq_ref=[cls.states],
                    elem_ref=[state],
                    index=i,
                )
                ConcreteAddressor._handle_cls_attr(f"_state_link_{i}", edge)

        return ConcreteAddressor


@pytest.mark.parametrize("address_bits", [1, 2, 3])
def test_addressor_x_bit(address_bits: int):
    """Test Addressor with various address bit counts via MakeChild."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        addressor: fabll._ChildField[Addressor]
        pass

    # Dynamically add the addressor with the correct bit count
    _App._handle_cls_attr("addressor", Addressor.MakeChild(address_bits=address_bits))

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
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

    class _App(fabll.Node):
        addressor = Addressor.MakeChild(address_bits=3)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Set offset and base (MakeChild only sets address_bits)
    app.addressor.get().offset.get().set_superset(g, 1.0)
    app.addressor.get().base.get().set_superset(g, float(0x48))

    assert app.addressor.get().offset.get().force_extract_superset().get_single() == 1
    assert (
        int(app.addressor.get().base.get().force_extract_superset().get_single())
        == 0x48
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
    from faebryk.core.solver.solver import Solver

    """Test that address lines are set correctly based on offset bits."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()
        addressor: fabll._ChildField[Addressor]

    # Dynamically add the addressor with the correct bit count via MakeChild
    _App._handle_cls_attr("addressor", Addressor.MakeChild(address_bits=address_bits))

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Get address lines from PointerSequence
    address_lines = addressor.address_lines.get().as_list()

    # Connect address line references to power
    for line in address_lines:
        # Cast to ElectricLogic for proper typing
        el = F.ElectricLogic.bind_instance(line.instance)
        el.reference.get()._is_interface.get().connect_to(app.power.get())

    # Set base and address, let solver deduce offset from Is constraint
    # (offset = address - base)
    base_value = 0.0
    expected_address = base_value + float(offset)

    addressor.base.get().set_superset(g, base_value)
    addressor.address.get().set_superset(g, expected_address)

    # Run solver and attach has_solver trait
    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # Run post-instantiation-setup checks (this triggers address line setting)
    from faebryk.libs.app import checks as checks_mod

    checks_mod.check_design(
        app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
    )

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
    from faebryk.core.solver.solver import Solver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()
        # Use MakeChild to get proper address_lines population
        addressor = Addressor.MakeChild(address_bits=2)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Get address lines from PointerSequence and connect to power
    for line_node in addressor.address_lines.get().as_list():
        line = F.ElectricLogic.bind_instance(line_node.instance)
        line.reference.get()._is_interface.get().connect_to(app.power.get())

    # Don't constrain offset, base, or address - solver won't be able to deduce offset
    # Note: MakeChild adds address = base + offset constraint, but if neither
    # base, offset, nor address are constrained, offset can't be deduced.

    solver = Solver()
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # Should raise because offset is neither directly constrained nor deducible
    with pytest.raises(UserDesignCheckException, match="offset must be constrained"):
        from faebryk.libs.app import checks as checks_mod

        checks_mod.check_design(
            app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
        )


def test_addressor():
    from faebryk.core.solver.solver import Solver

    ConfigurableI2CClient = _make_configurable_i2c_client()

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = ConfigurableI2CClient.bind_typegraph(tg).create_instance(g=g).setup(g, tg)
    app.setup(g, tg)

    app.addressor.get().offset.get().set_superset(g, 3.0)
    app.i2c.get().address.get().set_superset(
        g,
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g)
        .setup_from_singleton(
            value=16 + 3,
            unit=None,  # I2C.address is unitless (F.Units.Bit is commented out)
        ),
    )

    solver = Solver()
    solver.simplify(g, tg)

    # Attach solver and run post-instantiation-setup checks (which sets address lines)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)
    from faebryk.libs.app import checks as checks_mod

    checks_mod.check_design(
        app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
    )

    assert solver.extract_superset(
        app.i2c.get().address.get().is_parameter.get()
    ).op_setic_equals(
        F.Literals.Numbers.bind_typegraph(tg)
        .create_instance(g)
        .setup_from_singleton(
            value=16 + 3,
            unit=None,  # I2C.address is unitless
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


@once
def _make_configurable_i2c_client():
    """Factory to create ConfigurableI2CClient class inside tests."""

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
            self.addressor.get().base.get().set_superset(g, 16.0)

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

    return ConfigurableI2CClient


@once
def _make_i2c_bus_topology():
    """Factory to create I2CBusTopology class inside tests."""
    ConfigurableI2CClient = _make_configurable_i2c_client()

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

    return I2CBusTopology


def test_i2c_unique_addresses():
    from faebryk.core.solver.solver import Solver

    I2CBusTopology = _make_i2c_bus_topology()

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = I2CBusTopology.bind_typegraph(tg).create_instance(g=g).setup(g, tg)
    app.clients[0].get().addressor.get().offset.get().set_superset(g, 1.0)
    app.clients[1].get().addressor.get().offset.get().set_superset(g, 2.0)
    app.clients[2].get().addressor.get().offset.get().set_superset(g, 3.0)

    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    from faebryk.libs.app import checks as checks_mod

    checks_mod.check_design(
        app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
    )


@pytest.mark.skip(
    reason="I2C.requires_unique_addresses not yet implemented in new core"
)
def test_i2c_duplicate_addresses():
    from faebryk.core.solver.solver import Solver

    I2CBusTopology = _make_i2c_bus_topology()

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = I2CBusTopology.bind_typegraph(tg).create_instance(g=g).setup(g, tg)
    app.clients[0].get().addressor.get().offset.get().set_superset(g, 1.0)
    app.clients[1].get().addressor.get().offset.get().set_superset(g, 3.0)
    app.clients[2].get().addressor.get().offset.get().set_superset(g, 3.0)

    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # with pytest.raises(F.I2C.requires_unique_addresses.DuplicateAddressException):
    with pytest.raises(ExceptionGroup) as e:
        from faebryk.libs.app import checks as checks_mod

        checks_mod.check_design(
            app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
        )
    assert e.group_contains(
        UserDesignCheckException, match="Duplicate I2C addresses found on the bus:"
    )


@pytest.mark.skip(
    reason="I2C.requires_unique_addresses not yet implemented in new core"
)
def test_i2c_duplicate_addresses_isolated():
    from faebryk.core.solver.solver import Solver

    I2CBusTopology = _make_i2c_bus_topology()

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = (
        I2CBusTopology.bind_typegraph(tg)
        .create_instance(g=g)
        .setup(g, tg, isolated=True)
    )
    app.clients[0].get().addressor.get().offset.get().set_superset(g, 1.0)
    app.clients[1].get().addressor.get().offset.get().set_superset(g, 3.0)
    app.clients[2].get().addressor.get().offset.get().set_superset(g, 3.0)

    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # with pytest.raises(F.I2C.requires_unique_addresses.DuplicateAddressException):
    with pytest.raises(ExceptionGroup) as e:
        from faebryk.libs.app import checks as checks_mod

        checks_mod.check_design(
            app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
        )
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
    from faebryk.core.solver.solver import Solver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        addressor = Addressor.MakeChild(address_bits=1)

    app = _App.bind_typegraph(tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Set base = 24 (0x18) and address = 25 (0x19)
    # The Is constraint `address is Add(base, offset)` should allow solver to deduce offset=1 # noqa: E501
    addressor.base.get().set_superset(g, 24.0)
    addressor.address.get().set_superset(g, 25.0)

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
    solver = Solver()
    offset_p = addressor.offset.get().is_parameter.get()

    # This runs the solver and caches supersets
    solver_result = solver.simplify_and_extract_superset(offset_p)

    # Get the result - this is in the solver's transient graph
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


# ---------------------------------------------------------------------------
#                     Multi-state mode tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "address_bits,states_per_pin",
    [(1, 4), (2, 4), (2, 3), (3, 4)],
)
def test_addressor_multi_state_factory(address_bits: int, states_per_pin: int):
    """Test that multi-state factory creates correct states and address lines."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    AppType = fabll.Node._copy_type(
        fabll.Node,
        name=f"_App_ms_factory_{address_bits}_{states_per_pin}",
    )
    AppType._handle_cls_attr(
        "addressor",
        Addressor.MakeChild(address_bits=address_bits, states_per_pin=states_per_pin),
    )

    app = AppType.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Verify address lines
    lines = addressor.address_lines.get().as_list()
    assert len(lines) == address_bits
    for line in lines:
        assert line.try_cast(F.ElectricLogic) is not None

    # Verify states
    state_list = addressor.states.get().as_list()
    assert len(state_list) == states_per_pin
    for state in state_list:
        assert state.try_cast(F.Electrical) is not None


def test_addressor_binary_mode_has_no_states():
    """Test that binary mode (states_per_pin=2) creates no states."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        addressor = Addressor.MakeChild(address_bits=2)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    state_list = app.addressor.get().states.get().as_list()
    assert len(state_list) == 0


@pytest.mark.parametrize(
    "offset,expected_pin_states",
    [
        # 2 pins, 4 states: pin_state(i) = (offset // 4^i) % 4
        (0, [0, 0]),  # A0=GND, A1=GND
        (1, [1, 0]),  # A0=VS,  A1=GND
        (2, [2, 0]),  # A0=SDA, A1=GND
        (3, [3, 0]),  # A0=SCL, A1=GND
        (4, [0, 1]),  # A0=GND, A1=VS
        (5, [1, 1]),  # A0=VS,  A1=VS
        (10, [2, 2]),  # A0=SDA, A1=SDA
        (15, [3, 3]),  # A0=SCL, A1=SCL
    ],
)
def test_addressor_multi_state_sets_address_lines(
    offset: int, expected_pin_states: list[int]
):
    """Test that multi-state address lines connect to correct states."""
    from faebryk.core.solver.solver import Solver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()
        addressor = Addressor.MakeChild(address_bits=2, states_per_pin=4)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # Connect address line references to power
    for line_node in addressor.address_lines.get().as_list():
        el = F.ElectricLogic.bind_instance(line_node.instance)
        el.reference.get()._is_interface.get().connect_to(app.power.get())

    # Set base and address to derive offset
    base_value = 0.0
    addressor.base.get().set_superset(g, base_value)
    addressor.address.get().set_superset(g, base_value + float(offset))

    # Run solver
    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # Run design checks
    from faebryk.libs.app import checks as checks_mod

    checks_mod.check_design(
        app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
    )

    # Verify each address line is connected to the expected state
    address_lines = addressor.address_lines.get().as_list()
    state_list = addressor.states.get().as_list()

    for i, (line_node, expected_state_idx) in enumerate(
        zip(address_lines, expected_pin_states)
    ):
        line = F.ElectricLogic.bind_instance(line_node.instance)
        expected_state = F.Electrical.bind_instance(
            state_list[expected_state_idx].instance
        )
        assert line.line.get()._is_interface.get().is_connected_to(expected_state), (
            f"Address line {i} should be connected to states[{expected_state_idx}] "
            f"for offset={offset}"
        )
