# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

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
