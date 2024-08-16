# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.Range import Range
from faebryk.library.TBD import TBD
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class USB2_0_ESD_Protection(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            usb = times(2, USB2_0)

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            vbus_esd_protection = TBD[bool]()
            data_esd_protection = TBD[bool]()

        self.PARAMs = _PARAMs(self)

        self.IFs.usb[0].IFs.usb_if.IFs.buspower.PARAMs.voltage.merge(
            Range(4.75 * P.V, 5.25 * P.V)
        )

        self.add_trait(
            can_bridge_defined(
                self.IFs.usb[0].IFs.usb_if.IFs.d, self.IFs.usb[1].IFs.usb_if.IFs.d
            )
        )
        self.IFs.usb[0].connect(self.IFs.usb[1])

        self.IFs.usb[0].IFs.usb_if.IFs.buspower.connect(
            self.IFs.usb[1].IFs.usb_if.IFs.buspower
        )

        self.IFs.usb[0].IFs.usb_if.IFs.buspower.get_trait(can_be_decoupled).decouple()

        self.add_trait(has_designator_prefix_defined("U"))
