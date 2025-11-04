# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TypeGuard

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import once


# TODO: Do we need this? Is this used other than rp2040 example?
class _TSwitch(fabll.Node):
    T = fabll.ModuleInterface

    def __init__(self, t: type[T]):
        super().__init__()
        self.t = t

    @staticmethod
    def is_instance(obj: fabll.Node, t: type[T]) -> bool:
        return isinstance(obj, _TSwitch) and issubclass(obj.t, t)


@once  # This means we can use a normal "isinstance" to test for them
def Switch[T: fabll.ModuleInterface](interface_type: type[T]):
    class _Switch(_TSwitch):
        def __init__(self) -> None:
            super().__init__(interface_type)

        designator_prefix = fabll.f_field(F.has_designator_prefix)(
            F.has_designator_prefix.Prefix.S
        )
        attach_to_footprint: F.can_attach_to_footprint_symmetrically

        unnamed = fabll.list_field(2, interface_type)

        @fabll.rt_field
        def can_bridge(self):
            return F.can_bridge(*self.unnamed)

        @staticmethod
        def is_instance(obj: fabll.Node) -> "TypeGuard[_Switch]":
            return _TSwitch.is_instance(obj, interface_type)

    return _Switch


# Usage example for the Switch factory
usage_example = F.has_usage_example.MakeChild(
    example="""
    import Switch, Electrical, ElectricLogic, ElectricPower

    # Create electrical switch (SPST)
    ElectricalSwitch = Switch(Electrical)
    electrical_switch = new ElectricalSwitch

    # Connect switch terminals
    input_signal ~ electrical_switch.unnamed[0]
    output_signal ~ electrical_switch.unnamed[1]

    # Create logic-level switch
    LogicSwitch = Switch(ElectricLogic)
    logic_switch = new LogicSwitch

    # Connect power reference for logic switch
    power_3v3 = new ElectricPower
    logic_switch.unnamed[0].reference ~ power_3v3
    logic_switch.unnamed[1].reference ~ power_3v3

    # Connect logic signals
    logic_input ~ logic_switch.unnamed[0].line
    logic_output ~ logic_switch.unnamed[1].line

    # Common uses: user buttons, reed switches, micro switches
    """,
    language=F.has_usage_example.Language.ato,
).put_on_type()
