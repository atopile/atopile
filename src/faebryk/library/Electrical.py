# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.units import Quantity


class Electrical(ModuleInterface):
    potential: F.TBD[Quantity]
