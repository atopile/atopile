# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class SPI(ModuleInterface):
    sclk: F.Electrical
    miso: F.Electrical
    mosi: F.Electrical
    gnd: F.Electrical
