# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class DifferentialPair(ModuleInterface):
    p: F.Electrical
    n: F.Electrical
