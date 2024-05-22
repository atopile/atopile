# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.can_switch_power import can_switch_power
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower


class can_switch_power_defined(can_switch_power.impl()):
    def __init__(
        self, in_power: ElectricPower, out_power: ElectricPower, in_logic: ElectricLogic
    ) -> None:
        super().__init__()

        self.in_power = in_power
        self.out_power = out_power
        self.in_logic = in_logic

        out_power.PARAMs.voltage.merge(in_power.PARAMs.voltage)

    def get_logic_in(self) -> ElectricLogic:
        return self.in_logic

    def get_in(self) -> ElectricPower:
        return self.in_power

    def get_out(self) -> ElectricPower:
        return self.out_power
