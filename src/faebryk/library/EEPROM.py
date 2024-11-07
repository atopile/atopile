# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


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

    memory_size: F.TBD

    power: F.ElectricPower
    i2c: F.I2C
    write_protect: F.ElectricLogic
    address = L.list_field(3, F.ElectricLogic)

    # ----------------------------------------
    #                traits
    # ----------------------------------------

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __preinit__(self):
        # ----------------------------------------
        #                connections
        # ----------------------------------------
        self.power.decoupled.decouple()
        self.i2c.terminate()
