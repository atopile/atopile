# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


# TODO remove generic stuff into EEPROM/i2c device etc
class M24C08_FMN6TP(Module):
    power: F.ElectricPower
    data: F.I2C
    nwc: F.ElectricLogic
    e = L.list_field(3, F.ElectricLogic)

    @L.rt_field
    def attach_to_footprint(self):
        x = self
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": x.e[0].signal,
                "2": x.e[1].signal,
                "3": x.e[2].signal,
                "4": x.power.lv,
                "5": x.data.sda.signal,
                "6": x.data.scl.signal,
                "7": x.nwc.signal,
                "8": x.power.hv,
            }
        )

    def __preinit__(self):
        self.attach_to_footprint.attach(
            F.SOIC(8, size_xy=(3.9 * P.mm, 4.9 * P.mm), pitch=1.27 * P.mm)
        )

        self.data.terminate()
        self.power.decoupled.decouple()

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")

    def set_address(self, addr: int):
        assert addr < (1 << len(self.e))

        for i, e in enumerate(self.e):
            e.set(addr & (1 << i) != 0)
