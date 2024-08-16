# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.TBD import TBD
from faebryk.libs.units import Quantity

logger = logging.getLogger(__name__)


# TODO: make generic (use Switch module, different switch models, bistable, etc.)
class Relay(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            switch_a_nc = Electrical()
            switch_a_common = Electrical()
            switch_a_no = Electrical()
            switch_b_no = Electrical()
            switch_b_common = Electrical()
            switch_b_nc = Electrical()
            coil_p = Electrical()
            coil_n = Electrical()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            coil_rated_voltage = TBD[Quantity]()
            coil_rated_current = TBD[Quantity]()
            coil_resistance = TBD[Quantity]()
            contact_max_switching_voltage = TBD[Quantity]()
            contact_rated_switching_current = TBD[Quantity]()
            contact_max_switchng_current = TBD[Quantity]()

        self.PARAMs = _PARAMs(self)

        self.add_trait(has_designator_prefix_defined("RELAY"))
