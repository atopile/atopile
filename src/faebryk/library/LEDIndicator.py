# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module  # noqa: F401
from faebryk.libs.library import L  # noqa: F401


class LEDIndicator(Module):
    # interfaces

    logic_in: F.ElectricLogic
    power_in: F.ElectricPower

    # components

    led: F.PoweredLED

    def __init__(self, use_mosfet: bool = False, active_low: bool = False):
        super().__init__()
        self._use_mosfet = use_mosfet
        self._active_low = active_low

    def __preinit__(self):
        if self._use_mosfet:
            power_switch = self.add(
                F.PowerSwitchMOSFET(lowside=True, normally_closed=self._active_low)
            )
        else:
            power_switch = self.add(
                F.PowerSwitchStatic(normally_closed=self._active_low)
            )

        self.power_in.connect_via(power_switch, self.led.power)
        power_switch.logic_in.connect(self.logic_in)

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import LEDIndicator, ElectricPower, ElectricLogic

        module UsageExample:
            # Basic LED indicator (active high)
            status_led = new LEDIndicator

            # Connect power supply
            power_5v = new ElectricPower
            assert power_5v.voltage within 5V +/- 5%
            status_led.power_in ~ power_5v

            # Connect control signal
            status_signal = new ElectricLogic
            status_signal.reference ~ power_5v
            status_led.logic_in ~ status_signal

            # Connect to external signal lines
            external_gpio = new ElectricLogic
            external_gpio ~ status_signal

            # Configure LED properties
            status_led.led.led.color = "GREEN"
            status_led.led.led.current = 20mA +/- 5%
            status_led.led.led.forward_voltage = 2.1V +/- 10%

            # High-power LED with MOSFET driver
            power_led = new LEDIndicator
            power_control_signal = new ElectricLogic
            power_control_signal.reference ~ power_5v
            power_led.power_in ~ power_5v
            power_led.logic_in ~ power_control_signal
            power_led.led.led.current = 100mA +/- 10%  # Higher current

            # Active-low indicator (ON when signal is LOW)
            error_led = new LEDIndicator
            error_signal = new ElectricLogic
            error_signal.reference ~ power_5v
            error_led.power_in ~ power_5v
            error_led.logic_in ~ error_signal
            error_led.led.led.color = "RED"

            # Common applications: status indication, debugging, user feedback
        """,
        language=F.has_usage_example.Language.ato,
    )
