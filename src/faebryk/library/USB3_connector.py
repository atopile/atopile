# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class USB3_connector(Module):
    usb3: F.USB3
    shield: F.Electrical

    def __preinit__(self):
        self.usb3.usb3_if.usb_if.buspower.voltage.merge(F.Range(4.75 * P.V, 5.25 * P.V))

        self.usb3.usb3_if.usb_if.buspower.lv.connect(self.usb3.usb3_if.gnd_drain)

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("J")