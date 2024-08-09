# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.I2C import I2C
from faebryk.library.TBD import TBD
from faebryk.libs.util import times


class EEPROM(Module):
    """
    Generic EEPROM module with I2C interface.
    """

    def set_address(self, addr: int):
        """
        Configure the address of the EEPROM by setting the address pins.
        """
        assert addr < (1 << len(self.IFs.address))

        for i, e in enumerate(self.IFs.address):
            e.set(addr & (1 << i) != 0)

    def __init__(self):
        super().__init__()

        # ----------------------------------------
        #     modules, interfaces, parameters
        # ----------------------------------------
        class _PARAMs(Module.PARAMS()):
            memory_size = TBD[int]()

        self.PARAMs = _PARAMs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            i2c = I2C()
            write_protect = ElectricLogic()
            address = times(3, ElectricLogic)

        self.IFs = _IFs(self)

        # ----------------------------------------
        #                traits
        # ----------------------------------------
        self.add_trait(has_designator_prefix_defined("U"))
        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )

        # ----------------------------------------
        #                connections
        # ----------------------------------------
        self.IFs.power.get_trait(can_be_decoupled).decouple()
        self.IFs.i2c.terminate()
