# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


# TODO remove generic stuff into EEPROM/i2c device etc
class _M24C08_FMN6TP(Module):
    power: F.ElectricPower
    data: F.I2C
    write_protect: F.ElectricLogic
    address_pin = L.list_field(3, F.ElectricLogic)

    @L.rt_field
    def attach_to_footprint(self):
        x = self
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": x.address_pin[0].line,
                "2": x.address_pin[1].line,
                "3": x.address_pin[2].line,
                "4": x.power.lv,
                "5": x.data.sda.line,
                "6": x.data.scl.line,
                "7": x.write_protect.line,
                "8": x.power.hv,
            }
        )

    explicit_part = L.f_field(F.has_explicit_part.by_mfr)(
        "STMicroelectronics", "M24C08-FMN6TP"
    )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def reference_defined(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __preinit__(self):
        # self.attach_to_footprint.attach(
        #    F.SOIC(8, size_xy=(3.9 * P.mm, 4.9 * P.mm), pitch=1.27 * P.mm)
        # )

        self.power.voltage.constrain_subset(L.Range(1.7 * P.V, 5.5 * P.V))

    def enable_write_protection(self, owner: Module, protect=True):
        if protect:
            self.write_protect.get_trait(F.ElectricLogic.can_be_pulled).pull(
                up=True, owner=owner
            )
            return
        self.write_protect.get_trait(F.ElectricLogic.can_be_pulled).pull(
            up=False, owner=owner
        )

    def set_address(self, addr: int):
        assert addr < (1 << len(self.address_pin))

        for i, e in enumerate(self.address_pin):
            e.set(addr & (1 << i) != 0)


# TODO rename to ReferenceDesign
class M24C08_FMN6TP(Module):
    ic: _M24C08_FMN6TP

    def __preinit__(self):
        self.ic.data.terminate(owner=self)
        self.ic.power.decoupled.decouple(owner=self).capacitance.constrain_subset(
            L.Range(10 * P.nF * 0.9, 100 * P.nF * 1.1)
        )
