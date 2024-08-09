# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import dataclass, field

from faebryk.core.core import Module, Parameter
from faebryk.library.Constant import Constant
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_esphome_config import has_esphome_config
from faebryk.library.is_esphome_bus import is_esphome_bus
from faebryk.library.Range import Range
from faebryk.library.TBD import TBD
from faebryk.library.UART_Base import UART_Base


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

    @dataclass
    class _pm1006_esphome_config(has_esphome_config.impl()):
        update_interval_s: Parameter = field(default_factory=TBD)

        def __post_init__(self) -> None:
            super().__init__()

        def get_config(self) -> dict:
            assert isinstance(
                self.update_interval_s, Constant
            ), "No update interval set!"

            obj = self.get_obj()
            assert isinstance(obj, PM1006), "This is not an PM1006!"

            uart = is_esphome_bus.find_connected_bus(obj.IFs.data)

            return {
                "sensor": [
                    {
                        "platform": "pm1006",
                        "update_interval": f"{self.update_interval_s.value}s",
                        "uart_id": uart.get_trait(is_esphome_bus).get_bus_id(),
                    }
                ]
            }

    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = ElectricPower()
            data = UART_Base()

        self.IFs = _IFs(self)

        # components
        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)
        # ---------------------------------------------------------------------

        self.add_trait(
            has_datasheet_defined(
                "http://www.jdscompany.co.kr/download.asp?gubun=07&filename=PM1006_F.LED_PARTICLE_SENSOR_MODULE_SPECIFICATIONS.pdf"
            )
        )

        self.esphome = self._pm1006_esphome_config()
        self.add_trait(self.esphome)
        # ---------------------------------------------------------------------

        self.IFs.power.PARAMs.voltage.merge(Range.from_center(5, 0.2))

        self.IFs.data.PARAMs.baud.merge(Constant(9600))
