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

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.util import once

logger = logging.getLogger(__name__)

# Module-level registry of active mux configs for post-solve conflict detection.
# List of (mux, config_index, [config_pin_instances]).
# Each entry records which config_pins are active for a resolved mux.
# Call PinMuxSelector.clear_claim_registry() between independent builds/tests.
_active_mux_configs: list[tuple["PinMuxSelector", int, list]] = []


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

    class PinConflictError(F.implements_design_check.UnfulfilledCheckException):
        """Two PinMuxSelectors resolved to configs that share a GPIO pin."""

        def __init__(
            self,
            current_mux: "PinMuxSelector",
            current_config: int,
            current_wire: int,
            other_mux: "PinMuxSelector",
            other_config: int,
            other_wire: int,
        ):
            current_name = type(current_mux).__name__
            other_name = type(other_mux).__name__
            super().__init__(
                f"Pin conflict: config_pin shared by two active mux configs.\n"
                f"  - {current_name} config {current_config}, wire {current_wire}\n"
                f"  - {other_name} config {other_config}, wire {other_wire}\n"
                f"Constrain one mux's selection to a different config "
                f"to resolve the conflict.",
                nodes=[current_mux, other_mux],
            )

    # ----------------------------------------
    #     conflict detection
    # ----------------------------------------
    def _register_and_check_conflicts(
        self, sel: int, width: int, config_list: list
    ) -> None:
        """
        Register this mux's active config_pins in the claim registry
        and check for conflicts with other muxes.

        Each active config_pin is checked for connectivity against other
        muxes' active config_pins. If two muxes' active config_pins are
        connected to the same GPIO (i.e., they share an Electrical connection),
        a PinConflictError is raised.
        """
        # Collect this mux's active config_pin instances
        active_pins = []
        for i in range(width):
            pin_instance = config_list[sel * width + i].instance
            active_pins.append(pin_instance)

        # Check for conflicts with previously registered muxes
        for other_mux, other_config, other_pins in _active_mux_configs:
            if other_mux is self:
                continue
            for i, my_pin in enumerate(active_pins):
                my_electrical = F.Electrical.bind_instance(my_pin)
                for j, other_pin in enumerate(other_pins):
                    other_electrical = F.Electrical.bind_instance(other_pin)
                    if my_electrical._is_interface.get().is_connected_to(
                        other_electrical
                    ):
                        raise self.PinConflictError(
                            current_mux=self,
                            current_config=sel,
                            current_wire=i,
                            other_mux=other_mux,
                            other_config=other_config,
                            other_wire=j,
                        )

        # Register this mux's active config
        _active_mux_configs.append((self, sel, active_pins))

    @staticmethod
    def clear_claim_registry() -> None:
        """Clear the global pin claim registry. Call between test runs."""
        global _active_mux_configs
        _active_mux_configs.clear()

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

        Also registers the active config in the claim registry and
        checks for conflicts with other PinMuxSelectors.
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
            try:
                lit = solver.simplify_and_extract_superset(sel_p)
            except AssertionError:
                # Solver may have already run terminally; skip re-simplify
                pass

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

                self._register_and_check_conflicts(sel, width, config_list)

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
            c_pin = F.Electrical.bind_instance(config_list[sel * width + i].instance)
            p_pin._is_interface.get().connect_to(c_pin)

        self._register_and_check_conflicts(sel, width, config_list)

        logger.info(
            f"PinMuxSelector: Activated config {sel} "
            f"({width} wires, {num_configs} configs available)"
        )

    # ----------------------------------------
    #     pre-solve conflict constraints
    # ----------------------------------------
    @staticmethod
    def declare_pin_conflict(
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        mux_a: "PinMuxSelector",
        config_a: int,
        mux_b: "PinMuxSelector",
        config_b: int,
    ) -> None:
        """
        Add a solver constraint preventing mux_a config_a and mux_b config_b
        from being simultaneously active.

        For binary muxes (2 configs), this encodes as a linear inequality:
            (1 - sel_a) + sel_b <= 1   (when config_a=0, config_b=1)
        which the solver can detect as contradictory if both are constrained
        to their conflicting configs.

        Note: The solver does NOT support backward propagation through
        arithmetic expressions, so auto-assignment (constraining one mux
        to automatically resolve the other) is not currently possible.
        The constraint will however raise a Contradiction if both muxes
        are explicitly constrained to conflicting configs.

        Args:
            g: Graph view for constraint creation
            tg: Type graph for constraint creation
            mux_a: First PinMuxSelector instance
            config_a: Config index of mux_a that conflicts
            mux_b: Second PinMuxSelector instance
            config_b: Config index of mux_b that conflicts
        """
        sel_a_op = mux_a.selection.get().can_be_operand.get()
        sel_b_op = mux_b.selection.get().can_be_operand.get()

        # Build indicator for config_a being active:
        # For config K of binary mux: indicator = sel if K=1, else (1-sel) if K=0
        # For general N-config mux: we approximate by creating inequality
        # constraints on the sum of indicators.
        one = F.Literals.make_singleton(g=g, tg=tg, value=1.0)
        one_op = one.can_be_operand.get()

        if config_a == 0:
            # indicator_a = 1 - sel_a (active when sel_a = 0)
            indicator_a = F.Expressions.Subtract.c(one_op, sel_a_op, g=g, tg=tg)
        else:
            # For config_a = K, create: sel_a - (K-1) (active when sel_a = K)
            # For binary (K=1): indicator_a = sel_a
            if config_a == 1:
                indicator_a = sel_a_op
            else:
                k_minus_1 = F.Literals.make_singleton(
                    g=g, tg=tg, value=float(config_a - 1)
                )
                indicator_a = F.Expressions.Subtract.c(
                    sel_a_op, k_minus_1.can_be_operand.get(), g=g, tg=tg
                )

        if config_b == 0:
            one2 = F.Literals.make_singleton(g=g, tg=tg, value=1.0)
            indicator_b = F.Expressions.Subtract.c(
                one2.can_be_operand.get(), sel_b_op, g=g, tg=tg
            )
        else:
            if config_b == 1:
                indicator_b = sel_b_op
            else:
                k_minus_1 = F.Literals.make_singleton(
                    g=g, tg=tg, value=float(config_b - 1)
                )
                indicator_b = F.Expressions.Subtract.c(
                    sel_b_op, k_minus_1.can_be_operand.get(), g=g, tg=tg
                )

        # sum = indicator_a + indicator_b
        conflict_sum = F.Expressions.Add.c(indicator_a, indicator_b, g=g, tg=tg)

        # Assert: sum <= 1 (prevents both being at conflict config simultaneously)
        one_rhs = F.Literals.make_singleton(g=g, tg=tg, value=1.0)
        F.Expressions.LessOrEqual.c(
            conflict_sum, one_rhs.can_be_operand.get(), g=g, tg=tg, assert_=True
        )

        logger.debug(
            f"PinMuxSelector: declared conflict between "
            f"{type(mux_a).__name__} config {config_a} and "
            f"{type(mux_b).__name__} config {config_b}"
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
            ConcretePinMuxSelector._handle_cls_attr(f"_peripheral_pin_link_{i}", edge)

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

