# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class USB3_IF(ModuleInterface):
    usb_if: F.USB2_0_IF
    rx: F.DifferentialPair
    tx: F.DifferentialPair
    gnd_drain: F.Electrical
