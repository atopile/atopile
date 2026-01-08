# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.library.can_be_pulled as can_be_pulled


class ElectricLogic(fabll.Node):
    """
    ElectricLogic is a class that represents a logic signal.
    Logic signals only have two states: high and low.
    For more states / continuous signals check ElectricSignal.
    """

    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    class PushPull(StrEnum):
        PUSH_PULL = "PUSH_PULL"
        OPEN_DRAIN = "OPEN_DRAIN"
        OPEN_SOURCE = "OPEN_SOURCE"

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    line = F.Electrical.MakeChild()
    reference = F.ElectricPower.MakeChild()

    push_pull = F.Parameters.EnumParameter.MakeChild(
        enum_t=PushPull,
    )
    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )
    _can_be_pulled = fabll.Traits.MakeEdge(
        can_be_pulled.can_be_pulled.MakeChild(line, reference)
    )
    can_bridge = fabll.Traits.MakeEdge(F.can_bridge.MakeChild(in_=[""], out_=[""]))

    # ----------------------------------------
    #                functions
    # ----------------------------------------

    def set(self, on: bool):
        """
        Set the logic signal by directly connecting to the reference.
        """
        r = self.reference
        self.line.get()._is_interface.get().connect_to(
            r.get().hv.get() if on else r.get().lv.get()
        )

    def set_weak(self, on: bool, owner: fabll.Node):
        """
        Set the logic signal by connecting to the reference via a pull resistor.
        """
        return self.get_trait(can_be_pulled.can_be_pulled).pull(up=on, owner=owner)

    @property
    def pull_resistance(self):
        """Expose effective pull resistance like ElectricSignal."""
        return self.get_trait(can_be_pulled.can_be_pulled).pull_resistance

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import ElectricLogic

        logic_signal = new ElectricLogic

        logic_signal.reference ~ example_electric_power

        logic_signal.line ~ electrical
        # OR
        logic_signal.line ~ electricLogic.line
        # OR
        logic_signal.line ~> example_resistor ~> electrical
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )


# -----------------------------------------------------------------------------
#                                 Tests
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("on", [True, False])
def test_electric_logic_set(on: bool):
    """Test that set() correctly connects line to hv (on=True) or lv (on=False)."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()
        logic = ElectricLogic.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Connect the logic reference to the power rail
    app.logic.get().reference.get()._is_interface.get().connect_to(app.power.get())

    # Call set() to connect line to hv or lv
    app.logic.get().set(on)

    # Verify the connection
    logic = app.logic.get()
    power = app.power.get()

    if on:
        # line should be connected to hv
        assert logic.line.get()._is_interface.get().is_connected_to(power.hv.get()), (
            "set(True) should connect line to hv"
        )
        assert (
            not logic.line.get()._is_interface.get().is_connected_to(power.lv.get())
        ), "set(True) should NOT connect line to lv"
    else:
        # line should be connected to lv
        assert logic.line.get()._is_interface.get().is_connected_to(power.lv.get()), (
            "set(False) should connect line to lv"
        )
        assert (
            not logic.line.get()._is_interface.get().is_connected_to(power.hv.get())
        ), "set(False) should NOT connect line to hv"


def test_electric_logic_set_via_reference_child():
    """Test that set() works when reference is connected to a power interface."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()
        logic = ElectricLogic.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Connect the logic reference to the power rail
    app.logic.get().reference.get()._is_interface.get().connect_to(app.power.get())

    # Set high, then set low to verify both work
    app.logic.get().set(True)
    assert (
        app.logic.get()
        .line.get()
        ._is_interface.get()
        .is_connected_to(app.power.get().hv.get())
    )

    # Create a second logic to test set(False)
    class _App2(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        power = F.ElectricPower.MakeChild()
        logic = ElectricLogic.MakeChild()

    app2 = _App2.bind_typegraph(tg=tg).create_instance(g=g)
    app2.logic.get().reference.get()._is_interface.get().connect_to(app2.power.get())
    app2.logic.get().set(False)
    assert (
        app2.logic.get()
        .line.get()
        ._is_interface.get()
        .is_connected_to(app2.power.get().lv.get())
    )
