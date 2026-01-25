# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Single-pin I2C address configuration module.

Many I2C devices use a single address pin that can be connected to one of N
destinations to select the device address:
- Destination 0: offset 0
- Destination 1: offset 1
- ...
- Destination N-1: offset N-1

Final address = base + offset (where base comes from datasheet)

For TI devices (TMP117, TMP1075, etc.) with 4-state scheme:
- ADD0 connected to GND → offset 0
- ADD0 connected to VCC → offset 1
- ADD0 connected to SDA → offset 2
- ADD0 connected to SCL → offset 3
"""

import logging
from typing import Self

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.app.checks import check_design
from faebryk.libs.util import once

logger = logging.getLogger(__name__)


class SinglePinAddressor(fabll.Node):
    """
    Configures I2C device addresses via a single pin connected to one of N destinations.

    The SinglePinAddressor creates ElectricLogic `states` representing possible
    destinations for the address pin. After the solver resolves the offset value,
    the address_line is connected to the corresponding state.

    The final device address is calculated as: address = base + offset

    Example usage in ato:
        i2c = new I2C

        addressor = new SinglePinAddressor<states=4>
        addressor.base = 0x48  # Device base address from datasheet
        assert addressor.address is i2c.address
        adressor.address.default = 0x48
        addressor.states[0] ~ power.lv        # GND → offset 0
        addressor.states[1] ~ power.hv        # VCC → offset 1
        addressor.states[2] ~ i2c.sda.line    # SDA → offset 2
        addressor.states[3] ~ i2c.scl.line    # SCL → offset 3
        addressor.address_line.line ~ device.ADD0
        addressor.address_line.reference ~ power
    """

    is_abstract = fabll.Traits.MakeEdge(fabll.is_abstract.MakeChild()).put_on_type()

    # ----------------------------------------
    #     parameters
    # ----------------------------------------
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

    # ----------------------------------------
    #     interfaces
    # ----------------------------------------
    address_line = F.ElectricLogic.MakeChild()

    # PointerSequence for states - elements are added dynamically by factory()
    states = F.Collections.PointerSequence.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # Design check trait for post-solve address line configuration
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    # ----------------------------------------
    #     post-solve check
    # ----------------------------------------
    class StatesNotConfiguredError(F.implements_design_check.UnfulfilledCheckException):
        """Raised when SinglePinAddressor is used without module templating."""

        def __init__(self, addressor: "SinglePinAddressor"):
            super().__init__(
                "SinglePinAddressor requires explicit states configuration via "
                "module templating. Use: new SinglePinAddressor<states=N> "
                "(e.g. new SinglePinAddressor<states=4>)",
                nodes=[addressor],
            )

    class OffsetNotResolvedError(F.implements_design_check.UnfulfilledCheckException):
        """Raised when the offset parameter cannot be resolved to a single value."""

        def __init__(self, addressor: "SinglePinAddressor", max_offset: int):
            super().__init__(
                f"SinglePinAddressor offset must be constrained to a single "
                f"value (0-{max_offset}).",
                nodes=[addressor],
            )

    @F.implements_design_check.register_post_instantiation_setup_check
    def __check_post_instantiation_setup__(self):
        """
        Connect address_line to the correct state based on offset.

        After the solver resolves the offset value (0 to N-1), this method connects
        the address_line.line to the corresponding state's line.
        """
        # Check that states were configured via module templating
        state_list = self.states.get().as_list()
        if len(state_list) == 0:
            raise self.StatesNotConfiguredError(self)

        # Get solver from design check
        solver = self.design_check.get().get_solver()

        offset_p = self.offset.get().is_parameter.get()
        logger.debug(f"Running solver for SinglePinAddressor: {self}")

        # Try to extract offset - first check if resolved, then simplify if needed
        lit = solver.extract_superset(offset_p)

        if lit is None or not lit.op_setic_is_singleton():
            lit = solver.simplify_and_extract_superset(offset_p)

        # Get max_offset from already-fetched state_list
        max_offset = len(state_list) - 1

        if lit is None or not lit.op_setic_is_singleton():
            # Offset not yet constrained - this is expected when the user
            # hasn't specified the I2C address. The address line connection
            # will be made later when the offset is known.
            logger.warning(
                "SinglePinAddressor offset not resolved - address line connection "
                "skipped. Constrain the I2C address or offset to enable automatic "
                "connection."
            )
            return

        # lit is an is_literal trait - get the actual node it's attached to
        lit_node = fabll.Traits(lit).get_obj_raw()
        offset = int(lit_node.cast(F.Literals.Numbers).get_single())

        # Validate offset range
        if not 0 <= offset <= max_offset:
            raise ValueError(
                f"SinglePinAddressor offset {offset} out of range [0, {max_offset}]"
            )

        # Get destination based on offset
        destination_node = state_list[offset]
        destination = F.Electrical.bind_instance(destination_node.instance)

        # Connect address line to the selected destination
        self.address_line.get().line.get()._is_interface.get().connect_to(destination)
        logger.debug(f"SinglePinAddressor: Connected address_line to state[{offset}]")

    @classmethod
    @once
    def factory(cls, states: int) -> type[Self]:
        """
        Create a concrete SinglePinAddressor type with a fixed number of states.

        This creates:
        1. A PointerSequence named `states` for for-loop iteration in ato
        2. Electrical children named `states[0]`, `states[1]`, etc.
           for direct indexed access
        3. MakeLink edges from the PointerSequence to each Electrical element
        """
        if states <= 0:
            raise ValueError("At least one state is required")

        ConcreteSinglePinAddressor = fabll.Node._copy_type(
            cls, name=f"SinglePinAddressor<states={states}>"
        )

        # Create Electrical children with indexed names and link to PointerSequence
        for i in range(states):
            state = F.Electrical.MakeChild()
            ConcreteSinglePinAddressor._handle_cls_attr(f"states[{i}]", state)

            # Create MakeLink edge from PointerSequence to element
            # This allows iteration: for state in addressor.states
            edge = F.Collections.PointerSequence.MakeEdge(
                seq_ref=[cls.states],
                elem_ref=[state],
                index=i,
            )
            ConcreteSinglePinAddressor._handle_cls_attr(f"_state_link_{i}", edge)

        return ConcreteSinglePinAddressor

    @classmethod
    def MakeChild(cls, states: int) -> fabll._ChildField[Self]:
        """
        Create a SinglePinAddressor child field with the specified number of states.

        Uses factory() to create a concrete type with states as a proper
        list of Electrical children.
        """
        logger.debug(f"SinglePinAddressor.MakeChild called: states={states}")

        # Use factory to create a concrete type with the right number of states
        ConcreteSinglePinAddressor = cls.factory(states)
        out = fabll._ChildField(ConcreteSinglePinAddressor)

        # Setup constraint: offset is! address - base
        address_minus_base = F.Expressions.Subtract.MakeChild(
            [out, ConcreteSinglePinAddressor.address],
            [out, ConcreteSinglePinAddressor.base],
        ).add_as_dependant(out)

        F.Expressions.Is.MakeChild(
            [out, ConcreteSinglePinAddressor.offset],
            [address_minus_base],
            assert_=True,
        ).add_as_dependant(out)

        # Also add the reverse constraint: address is! base + offset
        base_plus_offset = F.Expressions.Add.MakeChild(
            [out, ConcreteSinglePinAddressor.base],
            [out, ConcreteSinglePinAddressor.offset],
        ).add_as_dependant(out)

        F.Expressions.Is.MakeChild(
            [out, ConcreteSinglePinAddressor.address],
            [base_plus_offset],
            assert_=True,
        ).add_as_dependant(out)

        # Constrain offset to valid range [0, states - 1]
        max_offset_value = states - 1
        F.Expressions.IsSubset.MakeChild(
            [out, ConcreteSinglePinAddressor.offset],
            [
                F.Literals.Numbers.MakeChild(
                    min=0,
                    max=max_offset_value,
                    unit=F.Units.Dimensionless,
                ).add_as_dependant(out)
            ],
            assert_=True,
        ).add_as_dependant(out)

        return out

    # ----------------------------------------
    #     usage example
    # ----------------------------------------
    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import SinglePinAddressor
        import I2C
        import ElectricPower

        i2c = new I2C
        power = new ElectricPower
        addressor = new SinglePinAddressor<states=4>

        addressor.base = 0x48  # Device base address from datasheet
        assert addressor.address is i2c.address
        adressor.address.default = 0x48
        addressor.states[0] ~ power.lv        # GND → offset 0
        addressor.states[1] ~ power.hv        # VCC → offset 1
        addressor.states[2] ~ i2c.sda.line    # SDA → offset 2
        addressor.states[3] ~ i2c.scl.line    # SCL → offset 3
        addressor.address_line.line ~ device.ADD0
        addressor.address_line.reference ~ power
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )


# -----------------------------------------------------------------------------
#                                 Tests
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("states", [2, 3, 4, 8])
def test_single_pin_addressor_factory(states: int):
    """Test SinglePinAddressor factory creates correct number of states."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create unique App type per test run
    AppType = fabll.Node._copy_type(fabll.Node, name=f"App_factory_{states}")

    # Dynamically add the addressor with the correct count
    AppType._handle_cls_attr("addressor", SinglePinAddressor.MakeChild(states=states))

    app = AppType.bind_typegraph(tg=tg).create_instance(g=g)
    addressor = app.addressor.get()

    # states is a PointerSequence pointing to Electrical children
    state_list = addressor.states.get().as_list()
    assert len(state_list) == states
    for state in state_list:
        assert state.try_cast(F.Electrical) is not None


def test_single_pin_addressor_basic_instantiation():
    """Test basic SinglePinAddressor creation via MakeChild."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        addressor = SinglePinAddressor.MakeChild(states=4)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Verify all expected children exist
    assert app.addressor.get() is not None
    assert app.addressor.get().address.get() is not None
    assert app.addressor.get().offset.get() is not None
    assert app.addressor.get().base.get() is not None
    assert app.addressor.get().address_line.get() is not None

    # states is a PointerSequence pointing to Electrical children
    state_list = app.addressor.get().states.get().as_list()
    assert len(state_list) == 4


def test_single_pin_addressor_parameters():
    """Test setting SinglePinAddressor parameters."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        addressor = SinglePinAddressor.MakeChild(states=4)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Set base and offset
    app.addressor.get().base.get().set_superset(g, float(0x48))
    app.addressor.get().offset.get().set_superset(g, 2.0)

    # Verify they were set
    assert (
        int(app.addressor.get().base.get().force_extract_superset().get_single())
        == 0x48
    )
    assert (
        int(app.addressor.get().offset.get().force_extract_superset().get_single()) == 2
    )


@pytest.mark.parametrize(
    "offset,state_index",
    [
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 3),
    ],
)
def test_single_pin_addressor_sets_address_line(offset: int, state_index: int):
    """Test that address_line is connected to correct state based on offset."""
    from faebryk.core.solver.solver import Solver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()
        addressor = SinglePinAddressor.MakeChild(states=4)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Connect address line reference to power
    app.addressor.get().address_line.get().reference.get()._is_interface.get().connect_to(
        app.power.get()
    )

    # Set base and offset
    app.addressor.get().base.get().set_superset(g, float(0x48))
    app.addressor.get().offset.get().set_superset(g, float(offset))

    # Run solver
    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # Run post-instantiation-setup checks (this triggers address line setting)
    check_design(
        app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
    )

    # Verify connection - address_line should be connected to states[offset]
    addr_line = app.addressor.get().address_line.get().line.get()
    state_list = app.addressor.get().states.get().as_list()
    expected_state = F.Electrical.bind_instance(state_list[state_index].instance)

    assert addr_line._is_interface.get().is_connected_to(expected_state), (
        f"Expected address_line connected to states[{state_index}] for offset={offset}"
    )


def test_single_pin_addressor_expression_propagation():
    """Test that solver can deduce offset from address and base."""
    from faebryk.core.solver.solver import Solver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        addressor = SinglePinAddressor.MakeChild(states=4)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Set base=0x48, address=0x4A → offset should be deduced as 2
    app.addressor.get().base.get().set_superset(g, float(0x48))
    app.addressor.get().address.get().set_superset(g, float(0x4A))

    # Run solver and extract offset
    solver = Solver()
    offset_param = app.addressor.get().offset.get().is_parameter.get()
    result = solver.simplify_and_extract_superset(offset_param)

    assert result is not None, "Solver should deduce offset"
    assert result.op_setic_is_singleton(), "Offset should be a singleton"

    result_node = fabll.Traits(result).get_obj_raw().cast(F.Literals.Numbers)
    assert int(result_node.get_single()) == 2, (
        f"Offset should be 2, got {result_node.get_single()}"
    )


def test_single_pin_addressor_raises_without_templating():
    """
    Test that SinglePinAddressor raises a compile-time error if instantiated
    without module templating (e.g. `new SinglePinAddressor` instead of
    `new SinglePinAddressor<states=4>`).
    """
    from atopile.compiler import DslRichException
    from test.compiler.conftest import build_instance

    with pytest.raises(DslRichException, match="requires module templating"):
        build_instance(
            """
            import SinglePinAddressor
            import Electrical

            module App:
                addressor = new SinglePinAddressor
                electrical = new Electrical
                addressor.states[0] ~ electrical
            """,
            "App",
            stdlib_extra=[SinglePinAddressor],
        )
