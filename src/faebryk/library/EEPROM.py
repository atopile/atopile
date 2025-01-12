# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class EEPROM(Module):
    """
    Generic EEPROM module with F.I2C interface.
    """

    def set_address(self, addr: int):
        """
        Configure the address of the EEPROM by setting the address pins.
        """
        assert addr < (1 << len(self.address))

        for i, e in enumerate(self.address):
            e.set(addr & (1 << i) != 0)

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    memory_size = L.p_field(
        units=P.bit,
        likely_constrained=True,
        domain=L.Domains.Numbers.NATURAL(),
        soft_set=L.Range(128 * P.bit, 1024 * P.kbit),
    )

    power: F.ElectricPower
    i2c: F.I2C
    write_protect: F.ElectricLogic
    address = L.list_field(3, F.ElectricLogic)

    # ----------------------------------------
    #                traits
    # ----------------------------------------

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
