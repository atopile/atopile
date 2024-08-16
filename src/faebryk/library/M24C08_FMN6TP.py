# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.I2C import I2C
from faebryk.library.SOIC import SOIC
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


# TODO remove generic stuff into EEPROM/i2c device etc
class M24C08_FMN6TP(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = ElectricPower()
            data = I2C()
            nwc = ElectricLogic()
            e = times(3, ElectricLogic)

        self.IFs = _IFs(self)

        x = self.IFs
        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": x.e[0].IFs.signal,
                    "2": x.e[1].IFs.signal,
                    "3": x.e[2].IFs.signal,
                    "4": x.power.IFs.lv,
                    "5": x.data.IFs.sda.IFs.signal,
                    "6": x.data.IFs.scl.IFs.signal,
                    "7": x.nwc.IFs.signal,
                    "8": x.power.IFs.hv,
                }
            )
        ).attach(SOIC(8, size_xy=(3.9 * P.mm, 4.9 * P.mm), pitch=1.27 * P.mm))

        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )

        self.IFs.data.terminate()
        self.IFs.power.get_trait(can_be_decoupled).decouple()

        self.add_trait(has_designator_prefix_defined("U"))

    def set_address(self, addr: int):
        assert addr < (1 << len(self.IFs.e))

        for i, e in enumerate(self.IFs.e):
            e.set(addr & (1 << i) != 0)
