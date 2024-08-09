# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import dataclass, field

from faebryk.core.core import Module, Parameter
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Constant import Constant
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_esphome_config import has_esphome_config
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.is_esphome_bus import is_esphome_bus
from faebryk.library.TBD import TBD


class XL_3528RGBW_WS2812B(Module):
    @dataclass
    class _ws2812b_esphome_config(has_esphome_config.impl()):
        update_interval_s: Parameter = field(default_factory=TBD)

        def __post_init__(self) -> None:
            super().__init__()

        def get_config(self) -> dict:
            assert isinstance(
                self.update_interval_s, Constant
            ), "No update interval set!"

            obj = self.get_obj()
            assert isinstance(obj, XL_3528RGBW_WS2812B), "This is not a WS2812B RGBW!"

            data_pin = is_esphome_bus.find_connected_bus(obj.IFs.di.IFs.signal)

            return {
                "light": [
                    {
                        "platform": "esp32_rmt_led_strip",
                        "update_interval": f"{self.update_interval_s.value}s",
                        "num_leds": 1,  # TODO: make dynamic
                        "rmt_channel": 0,  # TODO: make dynamic
                        "chipset": "WS2812",
                        "rgb_order": "RGB",
                        "is_rgbw": "true",
                        "pin": data_pin.get_trait(is_esphome_bus).get_bus_id(),
                    }
                ]
            }

    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            power = ElectricPower()
            do = ElectricLogic()
            di = ElectricLogic()

        self.IFs = _IFs(self)

        # connect all logic references
        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

        self.add_trait(has_designator_prefix_defined("LED"))

        # Add bridge trait
        self.add_trait(can_bridge_defined(self.IFs.di, self.IFs.do))

        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": self.IFs.power.IFs.lv,
                    "2": self.IFs.di.IFs.signal,
                    "3": self.IFs.power.IFs.hv,
                    "4": self.IFs.do.IFs.signal,
                }
            )
        )

        self.add_trait(
            has_datasheet_defined(
                "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2402181504_XINGLIGHT-XL-3528RGBW-WS2812B_C2890364.pdf"
            )
        )

        self.esphome = self._ws2812b_esphome_config()
        self.add_trait(self.esphome)
