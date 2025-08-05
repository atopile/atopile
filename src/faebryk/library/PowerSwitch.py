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
        import PowerSwitch, ElectricPower, ElectricLogic

        # Create normally-open power switch
        power_switch = new PowerSwitch(normally_closed=False)

        # Connect input power
        input_power = new ElectricPower
        assert input_power.voltage within 5V +/- 5%
        power_switch.power_in ~ input_power

        # Connect control signal
        enable_signal = new ElectricLogic
        enable_signal.reference ~ input_power
        power_switch.logic_in ~ enable_signal

        # Connect switched output to load
        switched_output = new ElectricPower
        power_switch.switched_power_out ~ switched_output
        load_circuit ~ switched_output

        # When enable_signal is HIGH, power flows to load
        # When enable_signal is LOW (or floating), power is disconnected

        # For normally-closed switch (fails safe)
        fail_safe_switch = new PowerSwitch(normally_closed=True)
        # This switch passes power when control is LOW or floating
        """,
        language=F.has_usage_example.Language.ato,
    )
