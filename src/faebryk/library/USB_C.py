# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class USB_C(ModuleInterface):
    usb3: F.USB3
    cc1: F.Electrical
    cc2: F.Electrical
    sbu1: F.Electrical
    sbu2: F.Electrical
    rx: F.DifferentialPair
    tx: F.DifferentialPair
