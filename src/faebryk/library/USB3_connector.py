# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.Range import Range
from faebryk.library.USB3 import USB3
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class USB3_connector(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            usb3 = USB3()
            shield = Electrical()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        self.IFs.usb3.IFs.usb3_if.IFs.usb_if.IFs.buspower.PARAMs.voltage.merge(
            Range(4.75 * P.V, 5.25 * P.V)
        )

        self.IFs.usb3.IFs.usb3_if.IFs.usb_if.IFs.buspower.IFs.lv.connect(
            self.IFs.usb3.IFs.usb3_if.IFs.gnd_drain
        )

        self.add_trait(has_designator_prefix_defined("J"))
