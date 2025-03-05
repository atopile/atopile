# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class XL_3528RGBW_WS2812B(Module):
    class _ws2812b_esphome_config(F.has_esphome_config.impl()):
        update_interval = L.p_field(units=P.s, tolerance_guess=0)

        def get_config(self) -> dict:
            obj = self.get_obj(XL_3528RGBW_WS2812B)

            data_pin = F.is_esphome_bus.find_connected_bus(obj.di.line)

            return {
                "light": [
                    {
                        "platform": "esp32_rmt_led_strip",
                        "update_interval": self.update_interval,
                        "num_leds": 1,  # TODO: make dynamic
                        "rmt_channel": 0,  # TODO: make dynamic
                        "chipset": "WS2812",
                        "rgb_order": "RGB",
                        "is_rgbw": "true",
                        "pin": data_pin.get_trait(F.is_esphome_bus).get_bus_id(),
                    }
                ]
            }

    # interfaces

    power: F.ElectricPower
    do: F.ElectricLogic
    di: F.ElectricLogic

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.LED
    )

    # Add bridge trait
    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.di, self.do)

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power.lv,
                "2": self.di.line,
                "3": self.power.hv,
                "4": self.do.line,
            }
        )

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2402181504_XINGLIGHT-XL-3528RGBW-WS2812B_C2890364.pdf"
    )

    esphome_config: _ws2812b_esphome_config

    def __preinit__(self):
        # ------------------------------
        #          parameters
        # ------------------------------

        # ------------------------------
        #          connections
        # ------------------------------
        # FIXME
        # self.power.decoupled.decouple()
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        F.ElectricLogic.connect_all_module_references(self, exclude=[self.power])
