# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class PM1006(Module):
    """
    Infrared LED particle sensor module PM1006
    adopts the principle of optical scattering to
    detect the variation trend of particle
    (size between 0.3μm to 10μm) concentration in
    the air. There is an infrared light-emitting
    diode and an optoelectronic sensor built-in
    PM1006, and light rays from the light-emitting
    diode will be reflected when pass through
    the particle. The optoelectronic sensor can
    show the concentration of particle in the air
    by detecting the intensity of reflected light.
    Sensor can output measuring value by pulse
    or UART signal.
    """

    class _pm1006_esphome_config(F.has_esphome_config.impl()):
        update_interval = L.p_field(units=P.s, tolerance_guess=0)

        def get_config(self) -> dict:
            obj = self.obj
            assert isinstance(obj, PM1006), "This is not an PM1006!"

            uart = F.is_esphome_bus.find_connected_bus(obj.data)

            return {
                "sensor": [
                    {
                        "platform": "pm1006",
                        "update_interval": self.update_interval,
                        "uart_id": uart.get_trait(F.is_esphome_bus).get_bus_id(),
                    }
                ]
            }

    esphome_config: _pm1006_esphome_config

    power: F.ElectricPower
    data: F.UART_Base

    # components

    # ---------------------------------------------------------------------
    datasheet = L.f_field(F.has_datasheet_defined)(
        "http://www.jdscompany.co.kr/download.asp?gubun=07&filename=PM1006_LED_PARTICLE_SENSOR_MODULE_SPECIFICATIONS.pdf"
    )
    # ---------------------------------------------------------------------

    def __preinit__(self):
        self.power.voltage.constrain_subset(L.Range.from_center(5 * P.V, 0.2 * P.V))
        self.data.baud.constrain_subset(9600 * P.baud)
