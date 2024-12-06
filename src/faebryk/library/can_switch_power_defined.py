# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class can_switch_power_defined(F.can_switch_power.impl()):
    def __init__(
        self,
        in_power: F.ElectricPower,
        out_power: F.ElectricPower,
        in_logic: F.ElectricLogic,
    ) -> None:
        super().__init__()

        self.in_power = in_power
        self.out_power = out_power
        self.in_logic = in_logic

        out_power.voltage.alias_is(in_power.voltage)

    def get_logic_in(self) -> F.ElectricLogic:
        return self.in_logic

    def get_in(self) -> F.ElectricPower:
        return self.in_power

    def get_out(self) -> F.ElectricPower:
        return self.out_power
