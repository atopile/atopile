# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.core.util import connect_all_interfaces
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Capacitor import Capacitor
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_defined_type_description import has_defined_type_description
from faebryk.library.I2C import I2C
from faebryk.library.Resistor import Resistor
from faebryk.library.SOIC import SOIC
from faebryk.library.TBD import TBD
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


# TODO remove generic stuff into EEPROM/i2c device etc
class M24C08_FMN6TP(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            i2c_termination_resistors = [Resistor(TBD()) for _ in range(2)]
            decoupling_cap = Capacitor(TBD())

        self.NODEs = _NODEs(self)

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
                    "1": x.e[0].NODEs.signal,
                    "2": x.e[1].NODEs.signal,
                    "3": x.e[2].NODEs.signal,
                    "4": x.power.NODEs.lv,
                    "5": x.data.NODEs.sda.NODEs.signal,
                    "6": x.data.NODEs.scl.NODEs.signal,
                    "7": x.nwc.NODEs.signal,
                    "8": x.power.NODEs.hv,
                }
            )
        ).attach(SOIC(8, size_xy_mm=(3.9, 4.9), pitch_mm=1.27))

        connect_all_interfaces(
            list(
                [e.NODEs.reference for e in self.IFs.e]
                + [
                    self.IFs.power,
                    self.IFs.nwc.NODEs.reference,
                    self.IFs.data.NODEs.sda.NODEs.reference,
                ]
            )
        )

        self.IFs.data.terminate(tuple(self.NODEs.i2c_termination_resistors))
        self.IFs.power.decouple(self.NODEs.decoupling_cap)

        self.add_trait(has_defined_type_description("U"))

    def set_address(self, addr: int):
        assert addr < (1 << len(self.IFs.e))

        for i, e in enumerate(self.IFs.e):
            e.set(addr & (1 << i) != 0)
