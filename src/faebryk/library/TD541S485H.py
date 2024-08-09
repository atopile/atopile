# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.RS485 import RS485
from faebryk.library.UART_Base import UART_Base

logger = logging.getLogger(__name__)


class TD541S485H(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            power_iso_in = ElectricPower()
            power_iso_out = ElectricPower()
            uart = UART_Base()
            rs485 = RS485()
            read_enable = Electrical()
            write_enable = Electrical()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        self.IFs.power.get_trait(can_be_decoupled).decouple()
        self.IFs.power_iso_in.get_trait(can_be_decoupled).decouple()
        self.IFs.power_iso_out.get_trait(can_be_decoupled).decouple()

        self.add_trait(has_designator_prefix_defined("U"))

        self.IFs.power_iso_in.IFs.lv.connect(self.IFs.power_iso_out.IFs.lv)

        x = self.IFs
        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": x.power.IFs.lv,
                    "2": x.power.IFs.hv,
                    "3": x.uart.IFs.rx.IFs.signal,
                    "4": x.read_enable,
                    "5": x.write_enable,
                    "6": x.uart.IFs.tx.IFs.signal,
                    "7": x.power.IFs.hv,
                    "8": x.power.IFs.lv,
                    "9": x.power_iso_out.IFs.lv,
                    "10": x.power_iso_out.IFs.hv,
                    "13": x.rs485.IFs.diff_pair.IFs.n,
                    "14": x.rs485.IFs.diff_pair.IFs.p,
                    "15": x.power_iso_in.IFs.hv,
                    "16": x.power_iso_in.IFs.lv,
                }
            )
        )
