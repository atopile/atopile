# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class OLED_Module(Module):
    class DisplayResolution(Enum):
        H64xV32 = auto()
        H128xV32 = auto()
        H128xV64 = auto()
        H256xV64 = auto()

    class DisplaySize(Enum):
        INCH_0_96 = auto()
        INCH_1_12 = auto()
        INCH_1_27 = auto()
        INCH_1_3 = auto()
        INCH_1_5 = auto()
        INCH_2_23 = auto()
        INCH_2_3 = auto()
        INCH_2_42 = auto()
        INCH_2_7 = auto()

    class DisplayController(Enum):
        SSD1315 = auto()
        SSD1306 = auto()
        SSD1309 = auto()

    power: F.ElectricPower
    i2c: F.I2C

    display_resolution = L.p_field(domain=L.Domains.ENUM(DisplayResolution))
    display_controller = L.p_field(domain=L.Domains.ENUM(DisplayController))
    display_size = L.p_field(domain=L.Domains.ENUM(DisplaySize))

    def __preinit__(self):
        self.power.voltage.constrain_subset(L.Range(3.0 * P.V, 5 * P.V))

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.DS
    )

    @L.rt_field
    def can_be_decoupled(self):
        class _(F.can_be_decoupled.impl()):
            def decouple(self, owner: Module):
                obj = self.get_obj(OLED_Module)
                obj.power.decoupled.decouple(owner=owner).capacitance.constrain_subset(
                    L.Range(100 * P.uF, 220 * P.uF)
                )

        return _()
