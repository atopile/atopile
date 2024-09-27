# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


# TODO remove generic stuff into EEPROM/i2c device etc
class M24C08_FMN6TP(Module):
    power: F.ElectricPower
    data: F.I2C
    write_protect: F.ElectricLogic
    address_pin = L.list_field(3, F.ElectricLogic)

    @L.rt_field
    def attach_to_footprint(self):
        x = self
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": x.address_pin[0].signal,
                "2": x.address_pin[1].signal,
                "3": x.address_pin[2].signal,
                "4": x.power.lv,
                "5": x.data.sda.signal,
                "6": x.data.scl.signal,
                "7": x.write_protect.signal,
                "8": x.power.hv,
            }
        )

    def __preinit__(self):
        F.ElectricLogic.connect_all_module_references(self)

        self.attach_to_footprint.attach(
            F.SOIC(8, size_xy=(3.9 * P.mm, 4.9 * P.mm), pitch=1.27 * P.mm)
        )

        self.data.terminate()
        self.power.decoupled.decouple().capacitance.merge(
            F.Range(10 * P.nF, 100 * P.nF)
        )

        self.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.manufacturer: "STMicroelectronics",
                    DescriptiveProperties.partno: "M24C08-FMN6TP",
                },
            )
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )

    def enable_write_protection(self, protect=True):
        if protect:
            self.write_protect.get_trait(F.ElectricLogic.can_be_pulled).pull(up=True)
            return
        self.write_protect.get_trait(F.ElectricLogic.can_be_pulled).pull(up=False)

    def set_address(self, addr: int):
        assert addr < (1 << len(self.address_pin))

        for i, e in enumerate(self.address_pin):
            e.set(addr & (1 << i) != 0)

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://eu.mouser.com/datasheet/2/389/m24c08_r-1849629.pdf"
    )
