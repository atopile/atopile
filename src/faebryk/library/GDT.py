# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.TBD import TBD
from faebryk.libs.units import Quantity

logger = logging.getLogger(__name__)


class GDT(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            common = Electrical()
            tube_1 = Electrical()
            tube_2 = Electrical()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            dc_breakdown_voltage = TBD[Quantity]()
            impulse_discharge_current = TBD[Quantity]()

        self.PARAMs = _PARAMs(self)

        self.add_trait(can_bridge_defined(self.IFs.tube_1, self.IFs.tube_2))

        self.add_trait(has_designator_prefix_defined("GDT"))
