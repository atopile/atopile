# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Pin multiplexer selector module.

Many microcontrollers allow a peripheral (I2C, UART, SPI) to be routed to
different sets of GPIO pins. The PinMuxSelector models this as an N-way
selector with W wires per configuration.

Architecture follows SinglePinAddressor / Addressor:
  1. `selection` parameter (0 to N-1) — solver resolves this
  2. N configs × W wires stored as `config_pins` (flattened)
  3. W `peripheral_pins` (external-facing interface)
  4. Post-solve check reads resolved `selection` and connects
     peripheral_pins[i] → config_pins[selection * W + i]

Example: I2C1 on STM32 can be routed to (PB6/PB7) or (PB8/PB9):

    i2c1_mux = new PinMuxSelector<configs=2, width=2>

    # Config 0: PB6 (SCL), PB7 (SDA)
    i2c1_mux.config_pins[0] ~ gpio_b[6]
    i2c1_mux.config_pins[1] ~ gpio_b[7]

    # Config 1: PB8 (SCL), PB9 (SDA)
    i2c1_mux.config_pins[2] ~ gpio_b[8]
    i2c1_mux.config_pins[3] ~ gpio_b[9]

    # Connect I2C interface to mux output
    i2c1.scl.line ~ i2c1_mux.peripheral_pins[0]
    i2c1.sda.line ~ i2c1_mux.peripheral_pins[1]

    # User selects config (or leave for auto-assignment later):
    assert i2c1_mux.selection within 0 to 0
"""

import logging
from typing import Self

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.util import once

logger = logging.getLogger(__name__)


class PinMuxSelector(fabll.Node):
    """
    Selects one of N pin configurations for a peripheral interface.

    Each configuration has W wires (e.g., 2 for I2C: SCL+SDA, 4 for SPI).
    After the solver resolves `selection` to config K, the post-solve check
    connects peripheral_pins[i] to config_pins[K*W + i] for each wire i.

    Template parameters:
        configs: Number of alternate pin configurations (N)
        width:   Number of wires per configuration (W)
    """

    is_abstract = fabll.Traits.MakeEdge(fabll.is_abstract.MakeChild()).put_on_type()

    # ----------------------------------------
    #     parameters
    # ----------------------------------------
    selection = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless,
        domain=F.NumberDomain.Args(negative=False, integer=True),
    )

    # ----------------------------------------
    #     interfaces
    # ----------------------------------------
    # External-facing pins (what the user connects their peripheral to)
    peripheral_pins = F.Collections.PointerSequence.MakeChild()

    # All config pins, flattened: config_pins[K*W + i] = config K, wire i
    config_pins = F.Collections.PointerSequence.MakeChild()

    # ----------------------------------------
    #     traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # Design check trait for post-solve pin mux activation
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    # ----------------------------------------
    #     errors
    # ----------------------------------------
    class SelectionNotResolvedError(
        F.implements_design_check.UnfulfilledCheckException
    ):
        """Raised when the selection parameter cannot be resolved."""

        def __init__(self, selector: "PinMuxSelector", num_configs: int):
            super().__init__(
                f"PinMuxSelector selection must be constrained to a single "
                f"value (0-{num_configs - 1}). "
                f"Use: assert <mux>.selection within <N> to <N>",
                nodes=[selector],
            )

    class NotConfiguredError(F.implements_design_check.UnfulfilledCheckException):
        """Raised when PinMuxSelector is used without module templating."""

        def __init__(self, selector: "PinMuxSelector"):
            super().__init__(
                "PinMuxSelector requires module templating. "
                "Use: new PinMuxSelector<configs=N, width=W>",
                nodes=[selector],
            )

    # ----------------------------------------
    #     post-solve check
    # ----------------------------------------
    @F.implements_design_check.register_post_instantiation_setup_check
    def __check_post_instantiation_setup__(self):
        """
        Connect peripheral pins to the selected config's pins.

        After the solver resolves `selection` to K, connects:
            peripheral_pins[i] → config_pins[K * width + i]
        for each wire i in [0, width).
        """
        peripheral_list = self.peripheral_pins.get().as_list()
        config_list = self.config_pins.get().as_list()

        if len(peripheral_list) == 0 or len(config_list) == 0:
            raise self.NotConfiguredError(self)

        width = len(peripheral_list)
        num_configs = len(config_list) // width

        # Get solver and resolve selection
        solver = self.design_check.get().get_solver()
        sel_p = self.selection.get().is_parameter.get()

        lit = solver.extract_superset(sel_p)
        if lit is None or not lit.op_setic_is_singleton():
            lit = solver.simplify_and_extract_superset(sel_p)

        # Fallback to direct extraction
        if lit is None or not lit.op_setic_is_singleton():
            direct_lit = self.selection.get().try_extract_superset()
            if direct_lit is not None and direct_lit.is_singleton():
                lit = direct_lit.is_literal.get()

        if lit is None or not lit.op_setic_is_singleton():
            # Check if this concrete type has a default_config set via MakeChild
            default_config = getattr(type(self), "_default_config", None)
            if default_config is not None and default_config >= 0:
                logger.info(
                    f"PinMuxSelector: selection not constrained, "
                    f"using default config {default_config}"
                )
                sel = default_config
                # Skip the solver extraction below and jump to connection logic
                if not 0 <= sel < num_configs:
                    raise ValueError(
                        f"PinMuxSelector default_config {sel} out of range "
                        f"[0, {num_configs - 1}]"
                    )

                for i in range(width):
                    p_pin = F.Electrical.bind_instance(peripheral_list[i].instance)
                    c_pin = F.Electrical.bind_instance(
                        config_list[sel * width + i].instance
                    )
                    p_pin._is_interface.get().connect_to(c_pin)

                logger.info(
                    f"PinMuxSelector: Activated default config {sel} "
                    f"({width} wires, {num_configs} configs available)"
                )
                return

            logger.warning(
                "PinMuxSelector selection not resolved — pin connections skipped. "
                "Constrain selection or use default_config to enable pin mux."
            )
            return

        # Extract the resolved selection value
        lit_node = fabll.Traits(lit).get_obj_raw()
        sel = int(lit_node.cast(F.Literals.Numbers).get_single())

        if not 0 <= sel < num_configs:
            raise ValueError(
                f"PinMuxSelector selection {sel} out of range [0, {num_configs - 1}]"
            )

        # Connect peripheral_pins[i] to config_pins[sel * width + i]
        for i in range(width):
            p_pin = F.Electrical.bind_instance(peripheral_list[i].instance)
            c_pin = F.Electrical.bind_instance(
                config_list[sel * width + i].instance
            )
            p_pin._is_interface.get().connect_to(c_pin)

        logger.info(
            f"PinMuxSelector: Activated config {sel} "
            f"({width} wires, {num_configs} configs available)"
        )

    # ----------------------------------------
    #     factory + MakeChild
    # ----------------------------------------
    @classmethod
    @once
    def factory(cls, configs: int, width: int, default_config: int = -1) -> type[Self]:
        """
        Create a concrete PinMuxSelector type with fixed configs and width.

        Creates:
        1. Electrical children `peripheral_pins[0..W-1]` for the external interface
        2. Electrical children `config_pins[0..N*W-1]` for all pin configurations
        3. MakeLink edges for PointerSequence iteration in ato

        Args:
            configs: Number of alternate pin configurations
            width: Number of wires per configuration
            default_config: Default config index (-1 = no default, require explicit)
        """
        if configs <= 0:
            raise ValueError("At least one config is required")
        if width <= 0:
            raise ValueError("Width must be at least 1")

        name = f"PinMuxSelector<configs={configs}, width={width}"
        if default_config >= 0:
            name += f", default_config={default_config}"
        name += ">"

        ConcretePinMuxSelector = fabll.Node._copy_type(cls, name=name)

        # Store default_config as class attribute for post-solve check
        ConcretePinMuxSelector._default_config = default_config

        # Create peripheral_pins[0..width-1]
        for i in range(width):
            pin = F.Electrical.MakeChild()
            ConcretePinMuxSelector._handle_cls_attr(f"peripheral_pins[{i}]", pin)

            edge = F.Collections.PointerSequence.MakeEdge(
                seq_ref=[cls.peripheral_pins],
                elem_ref=[pin],
                index=i,
            )
            ConcretePinMuxSelector._handle_cls_attr(
                f"_peripheral_pin_link_{i}", edge
            )

        # Create config_pins[0..configs*width-1]
        for i in range(configs * width):
            pin = F.Electrical.MakeChild()
            ConcretePinMuxSelector._handle_cls_attr(f"config_pins[{i}]", pin)

            edge = F.Collections.PointerSequence.MakeEdge(
                seq_ref=[cls.config_pins],
                elem_ref=[pin],
                index=i,
            )
            ConcretePinMuxSelector._handle_cls_attr(f"_config_pin_link_{i}", edge)

        return ConcretePinMuxSelector

    @classmethod
    def MakeChild(
        cls, configs: int, width: int, default_config: int = -1
    ) -> fabll._ChildField[Self]:
        """
        Create a PinMuxSelector child field with the specified configs and width.

        Uses factory() to create a concrete type, then adds solver constraints:
        - selection ∈ [0, configs - 1]

        Args:
            configs: Number of alternate pin configurations
            width: Number of wires per configuration
            default_config: Default config index (-1 = no default).
                When set, the mux auto-selects this config if the user
                doesn't explicitly constrain selection.
        """
        logger.debug(
            f"PinMuxSelector.MakeChild called: configs={configs}, width={width}, "
            f"default_config={default_config}"
        )

        ConcretePinMuxSelector = cls.factory(configs, width, default_config)
        out = fabll._ChildField(ConcretePinMuxSelector)

        # Constrain selection to valid range [0, configs - 1]
        max_sel = configs - 1
        F.Expressions.IsSubset.MakeChild(
            [out, ConcretePinMuxSelector.selection],
            [
                F.Literals.Numbers.MakeChild(
                    min=0,
                    max=max_sel,
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
        import PinMuxSelector
        import I2C
        import Electrical

        # I2C1 can be on (PB6/PB7) or (PB8/PB9), defaults to config 0
        i2c1_mux = new PinMuxSelector<configs=2, width=2, default_config=0>

        # Config 0: PB6 (SCL), PB7 (SDA)
        i2c1_mux.config_pins[0] ~ gpio_b_6
        i2c1_mux.config_pins[1] ~ gpio_b_7

        # Config 1: PB8 (SCL), PB9 (SDA)
        i2c1_mux.config_pins[2] ~ gpio_b_8
        i2c1_mux.config_pins[3] ~ gpio_b_9

        # Connect I2C to mux output
        i2c1 = new I2C
        i2c1.scl.line ~ i2c1_mux.peripheral_pins[0]
        i2c1.sda.line ~ i2c1_mux.peripheral_pins[1]

        # No assertion needed! Defaults to config 0.
        # To override: assert i2c1_mux.selection within 1 to 1
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )


# =============================================================================
#                                  Tests
# =============================================================================


@pytest.mark.parametrize(
    "configs,width",
    [(2, 2), (3, 2), (2, 4), (4, 1)],
)
def test_pin_mux_selector_factory(configs: int, width: int):
    """Test PinMuxSelector factory creates correct number of pins."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    AppType = fabll.Node._copy_type(
        fabll.Node, name=f"_App_factory_{configs}_{width}"
    )
    AppType._handle_cls_attr(
        "mux", PinMuxSelector.MakeChild(configs=configs, width=width)
    )

    app = AppType.bind_typegraph(tg=tg).create_instance(g=g)
    mux = app.mux.get()

    peripheral_list = mux.peripheral_pins.get().as_list()
    config_list = mux.config_pins.get().as_list()

    assert len(peripheral_list) == width
    assert len(config_list) == configs * width

    for pin in peripheral_list:
        assert pin.try_cast(F.Electrical) is not None
    for pin in config_list:
        assert pin.try_cast(F.Electrical) is not None


def test_pin_mux_selector_basic_instantiation():
    """Test basic PinMuxSelector creation via MakeChild."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        mux = PinMuxSelector.MakeChild(configs=2, width=2)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    assert app.mux.get() is not None
    assert app.mux.get().selection.get() is not None

    peripheral_list = app.mux.get().peripheral_pins.get().as_list()
    config_list = app.mux.get().config_pins.get().as_list()
    assert len(peripheral_list) == 2
    assert len(config_list) == 4


def test_pin_mux_selector_parameters():
    """Test setting PinMuxSelector parameters."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        mux = PinMuxSelector.MakeChild(configs=3, width=2)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Set selection to 1
    app.mux.get().selection.get().set_superset(g, 1.0)

    assert (
        int(app.mux.get().selection.get().force_extract_superset().get_single()) == 1
    )


@pytest.mark.parametrize(
    "selection,configs,width",
    [
        (0, 2, 2),  # I2C: 2 configs, 2 wires, select first
        (1, 2, 2),  # I2C: 2 configs, 2 wires, select second
        (0, 3, 4),  # SPI: 3 configs, 4 wires, select first
        (2, 3, 4),  # SPI: 3 configs, 4 wires, select third
        (0, 2, 1),  # Single-wire: 2 configs, 1 wire
    ],
)
def test_pin_mux_selector_connects_correct_config(
    selection: int, configs: int, width: int
):
    """Test that post-solve check connects the right config pins."""
    from faebryk.core.solver.solver import Solver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    AppType = fabll.Node._copy_type(
        fabll.Node, name=f"_App_connect_{selection}_{configs}_{width}"
    )
    AppType._handle_cls_attr(
        "_is_module", fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    )
    AppType._handle_cls_attr(
        "mux", PinMuxSelector.MakeChild(configs=configs, width=width)
    )

    app = AppType.bind_typegraph(tg=tg).create_instance(g=g)
    mux = app.mux.get()

    # Set selection
    mux.selection.get().set_superset(g, float(selection))

    # Run solver
    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    # Run post-instantiation-setup checks
    from faebryk.libs.app.checks import check_design

    check_design(
        app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
    )

    # Verify connections
    peripheral_list = mux.peripheral_pins.get().as_list()
    config_list = mux.config_pins.get().as_list()

    for i in range(width):
        p_pin = F.Electrical.bind_instance(peripheral_list[i].instance)
        expected_c_pin = F.Electrical.bind_instance(
            config_list[selection * width + i].instance
        )

        assert p_pin._is_interface.get().is_connected_to(expected_c_pin), (
            f"peripheral_pins[{i}] should be connected to "
            f"config_pins[{selection * width + i}] for selection={selection}"
        )

        # Verify NOT connected to other configs' pins
        for k in range(configs):
            if k == selection:
                continue
            wrong_pin = F.Electrical.bind_instance(
                config_list[k * width + i].instance
            )
            assert not p_pin._is_interface.get().is_connected_to(wrong_pin), (
                f"peripheral_pins[{i}] should NOT be connected to "
                f"config_pins[{k * width + i}] (config {k})"
            )


def test_pin_mux_selector_i2c_scenario():
    """
    End-to-end test: I2C peripheral with 2 alternate pin configs on a mini MCU.

    MCU has GPIO pins B6, B7, B8, B9.
    I2C1 config 0: SCL=B6, SDA=B7
    I2C1 config 1: SCL=B8, SDA=B9
    User selects config 1 → verify B8/B9 are connected to I2C.
    """
    from faebryk.core.solver.solver import Solver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _MiniMCU(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        # GPIO pins
        gpio_b6 = F.Electrical.MakeChild()
        gpio_b7 = F.Electrical.MakeChild()
        gpio_b8 = F.Electrical.MakeChild()
        gpio_b9 = F.Electrical.MakeChild()

        # I2C1 mux: 2 configs, 2 wires (SCL, SDA)
        i2c1_mux = PinMuxSelector.MakeChild(configs=2, width=2)

        # I2C interface
        i2c1 = F.I2C.MakeChild()

    app = _MiniMCU.bind_typegraph(tg=tg).create_instance(g=g)
    mux = app.i2c1_mux.get()

    # Wire config 0: B6 (SCL), B7 (SDA)
    config_list = mux.config_pins.get().as_list()
    F.Electrical.bind_instance(
        config_list[0].instance
    )._is_interface.get().connect_to(app.gpio_b6.get())
    F.Electrical.bind_instance(
        config_list[1].instance
    )._is_interface.get().connect_to(app.gpio_b7.get())

    # Wire config 1: B8 (SCL), B9 (SDA)
    F.Electrical.bind_instance(
        config_list[2].instance
    )._is_interface.get().connect_to(app.gpio_b8.get())
    F.Electrical.bind_instance(
        config_list[3].instance
    )._is_interface.get().connect_to(app.gpio_b9.get())

    # Connect I2C to mux peripheral pins
    peripheral_list = mux.peripheral_pins.get().as_list()
    app.i2c1.get().scl.get().line.get()._is_interface.get().connect_to(
        F.Electrical.bind_instance(peripheral_list[0].instance)
    )
    app.i2c1.get().sda.get().line.get()._is_interface.get().connect_to(
        F.Electrical.bind_instance(peripheral_list[1].instance)
    )

    # User selects config 1 (B8/B9)
    mux.selection.get().set_superset(g, 1.0)

    # Run solver + design checks
    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    from faebryk.libs.app.checks import check_design

    check_design(
        app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
    )

    # Verify: I2C SCL should be connected through to GPIO B8
    scl_line = app.i2c1.get().scl.get().line.get()
    assert scl_line._is_interface.get().is_connected_to(app.gpio_b8.get()), (
        "I2C1 SCL should be connected to GPIO B8 via mux config 1"
    )

    # Verify: I2C SDA should be connected through to GPIO B9
    sda_line = app.i2c1.get().sda.get().line.get()
    assert sda_line._is_interface.get().is_connected_to(app.gpio_b9.get()), (
        "I2C1 SDA should be connected to GPIO B9 via mux config 1"
    )

    # Verify: NOT connected to config 0 pins (B6, B7)
    assert not scl_line._is_interface.get().is_connected_to(app.gpio_b6.get()), (
        "I2C1 SCL should NOT be connected to GPIO B6 (config 0)"
    )
    assert not sda_line._is_interface.get().is_connected_to(app.gpio_b7.get()), (
        "I2C1 SDA should NOT be connected to GPIO B7 (config 0)"
    )


def test_pin_mux_selector_solver_deduction():
    """
    Test that the solver can deduce selection from external constraints.

    If selection is constrained via set_superset, the solver should
    extract it as a singleton.
    """
    from faebryk.core.solver.solver import Solver

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        mux = PinMuxSelector.MakeChild(configs=3, width=2)

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Constrain selection to 2
    app.mux.get().selection.get().set_superset(g, 2.0)

    # Run solver and extract
    solver = Solver()
    sel_param = app.mux.get().selection.get().is_parameter.get()
    result = solver.simplify_and_extract_superset(sel_param)

    assert result is not None, "Solver should return a result for selection"
    assert result.op_setic_is_singleton(), "Selection should be a singleton"

    result_node = fabll.Traits(result).get_obj_raw().cast(F.Literals.Numbers)
    assert int(result_node.get_single()) == 2, (
        f"Selection should be 2, got {result_node.get_single()}"
    )


# =============================================================================
#                     Compiler-level (ato syntax) tests
# =============================================================================


def _get_child(node: graph.BoundNode, name: str) -> graph.BoundNode:
    """Navigate to a child node by identifier (for compiler-level tests)."""
    from faebryk.libs.util import not_none

    return not_none(
        fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=node, child_identifier=name
        )
    )


def _check_connected(
    node: graph.BoundNode | fabll.Node, other: graph.BoundNode | fabll.Node
) -> bool:
    """Check if two nodes are connected (for compiler-level tests)."""
    source = node.instance if isinstance(node, fabll.Node) else node
    target = other.instance if isinstance(other, fabll.Node) else other
    # Handle BoundNodeReference (from PointerSequence) → get the actual BoundNode
    if hasattr(source, "node"):
        source_node = source.node()
    else:
        source_node = source
    if hasattr(target, "node"):
        target_node = target.node()
    else:
        target_node = target
    path = fbrk.EdgeInterfaceConnection.is_connected_to(
        source=source, target=target
    )
    return path.get_end_node().node().is_same(other=target_node)


def test_pin_mux_selector_ato_basic():
    """Test PinMuxSelector can be instantiated from ato syntax."""
    from test.compiler.conftest import build_instance

    g, tg, stdlib, result, app_root = build_instance(
        """
        #pragma experiment("MODULE_TEMPLATING")
        import PinMuxSelector
        import Electrical

        module App:
            mux = new PinMuxSelector<configs=2, width=2>
            gpio0 = new Electrical
            gpio1 = new Electrical
            gpio2 = new Electrical
            gpio3 = new Electrical

            # Config 0
            mux.config_pins[0] ~ gpio0
            mux.config_pins[1] ~ gpio1
            # Config 1
            mux.config_pins[2] ~ gpio2
            mux.config_pins[3] ~ gpio3
        """,
        "App",
        stdlib_extra=[PinMuxSelector],
    )

    # Navigate the instance graph
    mux_node = _get_child(app_root, "mux")
    assert mux_node is not None

    # Bind to typed wrapper to check PointerSequences
    mux = PinMuxSelector.bind_instance(mux_node)
    peripheral_list = mux.peripheral_pins.get().as_list()
    config_list = mux.config_pins.get().as_list()
    assert len(peripheral_list) == 2
    assert len(config_list) == 4


def test_pin_mux_selector_ato_with_selection():
    """Test PinMuxSelector with explicit selection constraint from ato."""
    from faebryk.core.solver.solver import Solver
    from faebryk.libs.app.checks import check_design
    from test.compiler.conftest import build_instance

    g, tg, stdlib, result, app_root = build_instance(
        """
        #pragma experiment("MODULE_TEMPLATING")
        import PinMuxSelector
        import Electrical

        module App:
            mux = new PinMuxSelector<configs=2, width=2>
            gpio0 = new Electrical
            gpio1 = new Electrical
            gpio2 = new Electrical
            gpio3 = new Electrical

            # Config 0: gpio0, gpio1
            mux.config_pins[0] ~ gpio0
            mux.config_pins[1] ~ gpio1
            # Config 1: gpio2, gpio3
            mux.config_pins[2] ~ gpio2
            mux.config_pins[3] ~ gpio3

            # Select config 1
            assert mux.selection within 1 to 1
        """,
        "App",
        stdlib_extra=[PinMuxSelector],
    )

    app = fabll.Node.bind_instance(app_root)

    # Run solver + design checks
    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    check_design(
        app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
    )

    # Navigate to mux and verify connections
    mux_node = _get_child(app_root, "mux")
    mux = PinMuxSelector.bind_instance(mux_node)
    peripheral_list = mux.peripheral_pins.get().as_list()
    config_list = mux.config_pins.get().as_list()

    # peripheral_pins[0] should connect to config_pins[2] (config 1, wire 0)
    p0 = F.Electrical.bind_instance(peripheral_list[0].instance)
    c2 = F.Electrical.bind_instance(config_list[2].instance)
    assert p0._is_interface.get().is_connected_to(c2), (
        "peripheral_pins[0] should be connected to config_pins[2] (config 1)"
    )

    # peripheral_pins[1] should connect to config_pins[3] (config 1, wire 1)
    p1 = F.Electrical.bind_instance(peripheral_list[1].instance)
    c3 = F.Electrical.bind_instance(config_list[3].instance)
    assert p1._is_interface.get().is_connected_to(c3), (
        "peripheral_pins[1] should be connected to config_pins[3] (config 1)"
    )

    # Verify NOT connected to config 0
    c0 = F.Electrical.bind_instance(config_list[0].instance)
    c1 = F.Electrical.bind_instance(config_list[1].instance)
    assert not p0._is_interface.get().is_connected_to(c0), (
        "peripheral_pins[0] should NOT be connected to config_pins[0] (config 0)"
    )
    assert not p1._is_interface.get().is_connected_to(c1), (
        "peripheral_pins[1] should NOT be connected to config_pins[1] (config 0)"
    )


def test_pin_mux_selector_ato_requires_templating():
    """Test that PinMuxSelector raises error without template args."""
    from atopile.compiler import DslRichException
    from test.compiler.conftest import build_instance

    with pytest.raises(DslRichException, match="requires module templating"):
        build_instance(
            """
            import PinMuxSelector
            import Electrical

            module App:
                mux = new PinMuxSelector
                e = new Electrical
                mux.peripheral_pins[0] ~ e
            """,
            "App",
            stdlib_extra=[PinMuxSelector],
        )


def test_pin_mux_selector_ato_i2c_end_to_end():
    """
    Full ato-level test: MCU with I2C mux, user selects config via assertion.

    Models a simplified MCU with:
    - 4 GPIO pins
    - I2C1 with 2 alternate pin configs
    - User connects a sensor I2C and selects config 0
    """
    from faebryk.core.solver.solver import Solver
    from faebryk.libs.app.checks import check_design
    from test.compiler.conftest import build_instance

    g, tg, stdlib, result, app_root = build_instance(
        """
        #pragma experiment("MODULE_TEMPLATING")
        import PinMuxSelector
        import Electrical
        import I2C
        import ElectricPower

        module MiniMCU:
            # GPIO pins
            gpio_b6 = new Electrical
            gpio_b7 = new Electrical
            gpio_b8 = new Electrical
            gpio_b9 = new Electrical

            # I2C1 mux: 2 configs, 2 wires
            i2c1_mux = new PinMuxSelector<configs=2, width=2>

            # Config 0: B6 (SCL), B7 (SDA)
            i2c1_mux.config_pins[0] ~ gpio_b6
            i2c1_mux.config_pins[1] ~ gpio_b7

            # Config 1: B8 (SCL), B9 (SDA)
            i2c1_mux.config_pins[2] ~ gpio_b8
            i2c1_mux.config_pins[3] ~ gpio_b9

            # External I2C interface
            i2c1 = new I2C
            i2c1.scl.line ~ i2c1_mux.peripheral_pins[0]
            i2c1.sda.line ~ i2c1_mux.peripheral_pins[1]

        module App:
            power = new ElectricPower
            mcu = new MiniMCU
            sensor_i2c = new I2C

            # Connect sensor to MCU's I2C
            sensor_i2c ~ mcu.i2c1

            # Select config 0 (B6/B7)
            assert mcu.i2c1_mux.selection within 0 to 0
        """,
        "App",
        stdlib_extra=[PinMuxSelector],
    )

    app = fabll.Node.bind_instance(app_root)

    # Run solver + design checks
    solver = Solver()
    solver.simplify(g, tg)
    fabll.Traits.create_and_add_instance_to(app, F.has_solver).setup(solver)

    check_design(
        app, stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP
    )

    # Navigate: App → mcu → i2c1_mux, and verify connections through to GPIOs
    mcu_node = _get_child(app_root, "mcu")
    mux_node = _get_child(mcu_node, "i2c1_mux")
    mux = PinMuxSelector.bind_instance(mux_node)

    peripheral_list = mux.peripheral_pins.get().as_list()
    config_list = mux.config_pins.get().as_list()

    # Config 0 was selected. peripheral_pins[0] → config_pins[0] → gpio_b6
    p0 = F.Electrical.bind_instance(peripheral_list[0].instance)
    c0 = F.Electrical.bind_instance(config_list[0].instance)
    assert p0._is_interface.get().is_connected_to(c0), (
        "peripheral_pins[0] should be connected to config_pins[0] (config 0, SCL)"
    )

    p1 = F.Electrical.bind_instance(peripheral_list[1].instance)
    c1 = F.Electrical.bind_instance(config_list[1].instance)
    assert p1._is_interface.get().is_connected_to(c1), (
        "peripheral_pins[1] should be connected to config_pins[1] (config 0, SDA)"
    )

    # Verify NOT connected to config 1 pins
    c2 = F.Electrical.bind_instance(config_list[2].instance)
    c3 = F.Electrical.bind_instance(config_list[3].instance)
    assert not p0._is_interface.get().is_connected_to(c2), (
        "peripheral_pins[0] should NOT be connected to config_pins[2] (config 1)"
    )
    assert not p1._is_interface.get().is_connected_to(c3), (
        "peripheral_pins[1] should NOT be connected to config_pins[3] (config 1)"
    )

    # Verify the GPIO connections are transitive:
    # config_pins[0] was connected to gpio_b6 by the ato code,
    # and peripheral_pins[0] was connected to config_pins[0] by the post-solve check.
    # So peripheral_pins[0] should be transitively connected to gpio_b6.
    gpio_b6_node = _get_child(mcu_node, "gpio_b6")
    gpio_b7_node = _get_child(mcu_node, "gpio_b7")

    assert _check_connected(peripheral_list[0], gpio_b6_node), (
        "peripheral_pins[0] (SCL) should be transitively connected to gpio_b6"
    )
    assert _check_connected(peripheral_list[1], gpio_b7_node), (
        "peripheral_pins[1] (SDA) should be transitively connected to gpio_b7"
    )
