# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class PowerSwitch(Module):
    """
    A generic module that switches power based on a logic signal, needs specialization

    The logic signal is active high. When left floating, the state is determined by the
    normally_closed parameter.
    """

    def __init__(self, normally_closed: bool) -> None:
        super().__init__()

        self._normally_closed = normally_closed

    logic_in: F.ElectricLogic
    power_in: F.ElectricPower
    switched_power_out: F.ElectricPower

    @L.rt_field
    def switch_power(self):
        return F.can_switch_power_defined(
            self.power_in, self.switched_power_out, self.logic_in
        )

    def __preinit__(self):
        self.switched_power_out.voltage.alias_is(self.power_in.voltage)

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import ElectricPower, ElectricLogic

        module UsageExample:
            # PowerSwitch is a generic interface that needs specialization
            # It requires a constructor parameter: PowerSwitch(normally_closed=bool)
            # Here we show the connections that would be made:

            # Input power supply
            input_power = new ElectricPower
            assert input_power.voltage within 5V +/- 5%

            # Control signal
            enable_signal = new ElectricLogic
            enable_signal.reference ~ input_power

            # Output power when switch is closed
            switched_output = new ElectricPower
        """,
        language=F.has_usage_example.Language.ato,
    )
